"""Núcleo del asistente de soporte que usamos en las clases S5 y S6.

Este archivo define qué datos guarda el agente y qué camino sigue cada turno.
No ejecuta una demo al importarlo: build_graph construye un grafo con el modelo,
el prompt, las herramientas y el checkpointer que le entreguemos.

Partes del archivo:
1. State describe mensajes, presupuesto, errores y resultados del turno.
2. local_prompt y prompt_template preparan las instrucciones y el historial.
3. build_graph conecta tres nodos: inicio, chatbot y ejecutar_tools.
4. Las aristas permiten responder directamente o repetir modelo → herramientas.
5. El checkpointer opcional conserva el estado de cada hilo de conversación.

La observabilidad se configura fuera de este núcleo; las métricas de cada
llamada se devuelven en el estado para que runner.py prepare el resultado.
"""

from typing import Annotated, Required, TypedDict, TypeVar
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END, add_messages
from .config import ROOT
from .tools import make_tools


# TypedDict documenta la forma del estado; no valida sus valores en ejecución.
# total=False permite aportar solo los campos que cambian en cada actualización.
class State(TypedDict, total=False):
    # add_messages combina mensajes nuevos con el historial en lugar de sustituirlo.
    # Required: cada turno llega con mensajes, aunque el resto del estado sea parcial.
    messages: Required[Annotated[list[AnyMessage], add_messages]]
    # Los demás campos se reemplazan con la actualización del nodo.
    # Número de intentos ejecutados en este turno, también cuando fallan.
    tool_count: int
    # Etiquetas de fallos controlados; no contienen cuerpos HTTP ni credenciales.
    errors: list[str]
    # Registro de herramientas solicitadas: nombre, executed y ok.
    calls: list[dict]
    # Recorrido legible del turno para mostrarlo en la consola.
    route: list[str]
    # Señala si seguimos, necesitamos tools, terminamos o encontramos un fallo.
    status: str
    # Una entrada de tokens/coste por llamada al modelo, si el proveedor los informa.
    usage: list[dict]


_T = TypeVar("_T")


# Copia una lista opcional. Si la clave no está en el estado, devuelve [].
def _list(value: list[_T] | None) -> list[_T]:
    return [] if value is None else list(value)


# Lee una versión local permitida. La selección remota se realiza en prompts.py.
def local_prompt(version="v2"):
    if version not in {"v1", "v2"}:
        raise ValueError("Versión local debe ser v1 o v2")
    return (ROOT / "prompts/soporte" / f"{version}.txt").read_text().strip()


# Combina un SystemMessage literal con el historial recibido en «messages».
# Los metadatos acompañan la ejecución, pero no son instrucciones para el modelo.
def prompt_template(text, metadata=None):
    # Tupla system literal: no interpretar llaves del texto como variables.
    from langchain_core.messages import SystemMessage

    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=text),
            MessagesPlaceholder("messages"),
        ]
    ).with_config(metadata=metadata or {})


# Construye el grafo sin lanzar consultas. Las dependencias inyectables permiten
# usar el modelo real en clase y un modelo simulado en las pruebas sin red.
def build_graph(model, *, prompt=None, checkpointer=None, tools=None, use_tools=True):
    """Inyectar model/prompt/checkpointer permite tests sin credenciales ni red."""
    tool_list = make_tools() if tools is None else tools
    # Solo se pueden ejecutar herramientas del catálogo: no código del modelo.
    by_name = {t.name: t for t in tool_list}
    template = prompt if prompt is not None else prompt_template(local_prompt())
    # bind_tools ofrece nombres, descripciones y argumentos; no ejecuta funciones.
    with_tools = model.bind_tools(tool_list) if use_tools else model
    # «|» compone la plantilla con el modelo. La segunda cadena no ofrece tools.
    chain = template | with_tools
    final_chain = template | model

    # Primer nodo de cada turno: reinicia métricas y presupuesto, no los mensajes.
    # El historial recuperado del checkpointer sigue disponible para chatbot.
    def inicio(state: State):
        return {
            "tool_count": 0,
            "errors": [],
            "calls": [],
            "usage": [],
            "route": ["inicio"],
            "status": "running",
        }

    # Llama al modelo con el historial y decide, por su respuesta, si hay tools.
    # config transporta el hilo y callbacks de trazas hasta la llamada al modelo.
    def chatbot(state: State, config: RunnableConfig):
        # Tras dos intentos, solo permitimos una llamada final sin ofrecer tools.
        # «respuesta_final» es una etiqueta de route, no otro nodo del grafo.
        final = not use_tools or state.get("tool_count", 0) >= 2
        route = [*_list(state.get("route")), "respuesta_final" if final else "chatbot"]
        try:
            msg = (final_chain if final else chain).invoke(
                {"messages": state["messages"]}, config
            )
        except Exception as exc:
            # No incluir respuesta HTTP/cuerpo del proveedor: puede contener datos sensibles.
            return {
                "messages": [
                    AIMessage(
                        content="No puedo completar la consulta ahora. Inténtalo más tarde."
                    )
                ],
                "errors": [*_list(state.get("errors")), f"modelo:{type(exc).__name__}"],
                "status": "model_error",
                "route": route,
            }
        # Recogemos tokens y coste cuando el proveedor los informa. None significa
        # dato desconocido; no equivale a consumo cero ni a una estimación.
        usage = getattr(msg, "usage_metadata", None)
        response_metadata = getattr(msg, "response_metadata", {}) or {}
        record = {"tokens": usage, "cost_usd": None, "cost_method": None}
        for container in [
            response_metadata.get("usage", {}),
            response_metadata.get("token_usage", {}),
            response_metadata,
        ]:
            if isinstance(container, dict) and isinstance(
                container.get("cost"), (int, float)
            ):
                record.update(
                    cost_usd=container["cost"], cost_method="provider_reported"
                )
                break
        tool_calls = getattr(msg, "tool_calls", [])
        if final and tool_calls:
            # No ejecutar una tercera herramienta ni dejar IDs de tools sin respuesta.
            denied = [
                ToolMessage(
                    content="Error: límite de herramientas agotado",
                    tool_call_id=c["id"],
                    name=c["name"],
                )
                for c in tool_calls
            ]
            return {
                "messages": [
                    msg,
                    *denied,
                    AIMessage(
                        content="He alcanzado el límite de dos herramientas. Acota la consulta en otro turno."
                    ),
                ],
                "errors": [*_list(state.get("errors")), "limite_final"],
                "status": "limit",
                "usage": [*_list(state.get("usage")), record],
                "route": route,
            }
        # Si no hay respuesta ni solicitud de herramientas, terminamos con un
        # mensaje controlado en lugar de entregar una respuesta vacía.
        if not tool_calls and not str(msg.content).strip():
            msg = AIMessage(
                content="No he obtenido una respuesta utilizable. Reformula la consulta."
            )
        return {
            "messages": [msg],
            "route": route,
            "usage": [*_list(state.get("usage")), record],
            "status": "tools" if tool_calls else "done",
        }

    # Ejecuta las solicitudes del último mensaje respetando un máximo de dos
    # intentos por turno, aunque vengan varias solicitudes en una misma respuesta.
    def ejecutar_tools(state: State, config: RunnableConfig):
        # Copias locales: preparamos una actualización sin modificar las listas
        # del estado que ha recibido el nodo.
        count = state.get("tool_count", 0)
        errors = _list(state.get("errors"))
        calls = _list(state.get("calls"))
        results = []
        # tool_calls solo existe en AIMessage; AnyMessage incluye el resto del historial.
        last = state["messages"][-1]
        if not isinstance(last, AIMessage):
            return {
                "errors": [*errors, "mensaje_sin_tools"],
                "tool_count": count,
                "calls": calls,
                "route": [*_list(state.get("route")), "tools"],
            }
        for call in last.tool_calls:
            if count >= 2:
                body = "Error: límite de dos herramientas agotado"
                errors.append("limite_herramientas")
                calls.append({"name": call["name"], "executed": False, "ok": False})
            else:
                # Consumir antes de ejecutar hace que argumentos inválidos,
                # recursos inexistentes y excepciones también cuenten como intento.
                count += 1
                try:
                    target = by_name.get(call["name"])
                    if target is None:
                        raise ValueError("herramienta_desconocida")
                    # La herramienta valida sus argumentos con el esquema Pydantic.
                    body = target.invoke(call["args"], config=config)
                    import json

                    success = json.loads(body).get("ok", True)
                    if not success:
                        errors.append("no_encontrado")
                    calls.append(
                        {"name": call["name"], "executed": True, "ok": success}
                    )
                except Exception as exc:
                    label = type(exc).__name__
                    body = f"Error controlado: {label}. No se obtuvo información."
                    errors.append(label)
                    calls.append({"name": call["name"], "executed": True, "ok": False})
            # Cada solicitud recibe un ToolMessage, incluso si fue rechazada.
            # El ID permite al modelo relacionar cada resultado con su petición.
            results.append(
                ToolMessage(content=body, tool_call_id=call["id"], name=call["name"])
            )
        return {
            "messages": results,
            "tool_count": count,
            "errors": errors,
            "calls": calls,
            "route": [*_list(state.get("route")), "tools"],
        }

    # Montaje del recorrido: START → inicio → chatbot. Si hay solicitudes,
    # chatbot → tools → chatbot; si no, chatbot → END.
    builder = StateGraph(State)
    builder.add_node("inicio", inicio)
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ejecutar_tools)
    builder.add_edge(START, "inicio")
    builder.add_edge("inicio", "chatbot")
    builder.add_conditional_edges(
        "chatbot",
        lambda s: "tools" if s["status"] == "tools" else END,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "chatbot")
    # El checkpointer guarda/recupera por thread_id. Sin él no hay persistencia
    # entre ejecuciones. Compilar prepara el grafo; invoke lo ejecutará después.
    return builder.compile(checkpointer=checkpointer)
