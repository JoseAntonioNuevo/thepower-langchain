"""Grafo de clase 1: juez → chatbot ⇄ tools → validador → publicar."""

# os.getenv lee interruptores de demo (p. ej. DEMO_FORCE_TOOL_ERROR).
import os

# Annotated une la lista de mensajes con el reducer add_messages.
# NotRequired: el checkpointer puede arrancar un turno sin esos campos.
from typing import Annotated, Any, NotRequired, TypedDict

# Carga .env → OPENROUTER_API_KEY (y TAVILY_API_KEY) disponibles en el proceso.
from dotenv import load_dotenv

# @tool publica la función al LLM: nombre, argumentos y docstring.
from langchain.tools import tool

# AnyMessage: tipo del historial (human, ai, tool, …).
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

# Cliente del modelo vía OpenRouter.
from langchain_openrouter import ChatOpenRouter

# InMemorySaver: memoria de conversación en RAM, claveada por thread_id.
from langgraph.checkpoint.memory import InMemorySaver

# START/END: entrada y salida. add_messages: los nodos AÑADEN mensajes.
from langgraph.graph import END, START, StateGraph, add_messages

# ToolNode ejecuta las tools pedidas (Tavily vive aquí, no en el juez).
from langgraph.prebuilt import ToolNode

# Búsqueda real (Tavily). Si falta la clave, la tool lo dice y el grafo sigue.
from app.buscar_web import buscar_web
# Reloj del sistema: el modelo no sabe si estamos en 2024 o 2026.
from app.fecha_hoy import consigna_sistema, fecha_hoy
# Juez: ¿hace falta internet? Validador: ¿la respuesta cubre lo pedido?
from app.juez import consigna_juez, es_turno_nuevo, parsear_veredicto, ruta_tras_chatbot
from app.validador import (
    consigna_validador,
    parsear_veredicto as parsear_validador,
    rechazo_heuristico,
    ruta_tras_validador,
)

load_dotenv()

# GPT-6 Luna. En Chat Completions las tools solo funcionan con effort "none".
# service_tier "priority" es el modo rápido. El alias "fast" vuelve como default.
MODELO = "openai/gpt-6-luna"
model = ChatOpenRouter(
    model=MODELO,
    temperature=0,
    reasoning={"effort": "none"},
    model_kwargs={"service_tier": "priority"},
)

# Un solo hilo para toda la sesión de terminal: así el bot recuerda turnos previos.
thread_id = "usuario_123"


@tool
def buscar_clima(ciudad: str) -> str:
    """MOCK de clase: no da temperatura real. Para tiempo real usa buscar_web."""
    # Interruptor de demo: simula un fallo de red sin tocar APIs reales.
    if os.getenv("DEMO_FORCE_TOOL_ERROR") == "1":
        raise TimeoutError("timeout simulado")
    # Mock fijo: no llama a un servicio meteorológico de verdad.
    return f"Soleado en {ciudad}"


@tool
def tendencia_ropa(ciudad: str) -> str:
    """MOCK de clase: no consulta internet. Para moda real usa buscar_web."""
    # Segundo mock: el modelo puede pedir las dos tools en el mismo turno.
    return f"En {ciudad} se lleva chaqueta ligera y zapatillas."


# El modelo puede elegir una, varias, o ninguna, según la pregunta.
tools = [fecha_hoy, buscar_clima, tendencia_ropa, buscar_web]
# bind_tools adjunta el esquema: el LLM responde con texto o con tool_calls.
model_with_tools = model.bind_tools(tools)


# Estado de un turno. La memoria entre turnos la guarda el checkpointer.
class State(TypedDict):
    # Historial: human / ai / tool. add_messages concatena, no pisa.
    messages: Annotated[list[AnyMessage], add_messages]
    # Veredicto del juez (nodo 1). El chatbot lo lee en la consigna.
    usar_web: NotRequired[bool]
    query_web: NotRequired[str]
    motivo_juez: NotRequired[str]
    # Veredicto del validador (nodo 4). Si ok es False, puede volver al juez.
    ok: NotRequired[bool]
    motivo_validador: NotRequired[str]
    # Contador de rechazos de este turno. El juez lo pone a 0 al empezar.
    intentos: NotRequired[int]
    # Borrador privado: solo se publica después de que el validador dé ok.
    draft: NotRequired[str]


def _texto(content: Any) -> str:
    """Saca texto plano del content de un mensaje (str, bloques o None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes: list[str] = []
        for block in content:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if t:
                    partes.append(str(t))
        return "\n".join(partes)
    return str(content)


def _ultimo_humano(mensajes: list[AnyMessage]) -> str:
    """Pregunta del usuario de este turno (el HumanMessage más reciente)."""
    for mensaje in reversed(mensajes):
        if getattr(mensaje, "type", None) == "human":
            return _texto(getattr(mensaje, "content", ""))
    return ""


def _mensajes_del_turno(mensajes: list[AnyMessage]) -> list[AnyMessage]:
    """Mensajes posteriores al último human: tools y respuestas de esta vuelta."""
    bloque: list[AnyMessage] = []
    for mensaje in reversed(mensajes):
        if getattr(mensaje, "type", None) == "human":
            break
        bloque.append(mensaje)
    return list(reversed(bloque))


def _ultima_respuesta_bot(mensajes: list[AnyMessage]) -> str:
    """Último AIMessage con texto y sin tool_calls: lo que ve el usuario."""
    for mensaje in reversed(_mensajes_del_turno(mensajes)):
        if getattr(mensaje, "type", None) != "ai":
            continue
        # Un AIMessage que solo pide tools no es la respuesta final.
        if getattr(mensaje, "tool_calls", None):
            continue
        texto = _texto(getattr(mensaje, "content", ""))
        if texto:
            return texto
    return ""


def _hubo_buscar_web(mensajes: list[AnyMessage]) -> bool:
    """True si ToolNode ejecutó buscar_web en este turno (no en turnos viejos)."""
    for mensaje in _mensajes_del_turno(mensajes):
        if getattr(mensaje, "type", None) == "tool" and getattr(mensaje, "name", None) == "buscar_web":
            return True
    return False


def _evidencia_tools(mensajes: list[AnyMessage]) -> str:
    """Resultados de tools del turno: la fuente de verdad para el validador."""
    bloques: list[str] = []
    for mensaje in _mensajes_del_turno(mensajes):
        if getattr(mensaje, "type", None) != "tool":
            continue
        nombre = getattr(mensaje, "name", None) or "tool"
        contenido = _texto(getattr(mensaje, "content", ""))
        if contenido:
            bloques.append(f"[{nombre}]\n{contenido}")
    return "\n\n".join(bloques)


def juez(state: State) -> dict:
    """Nodo 1: ¿hace falta internet? No busca; solo deja el veredicto en el estado."""
    mensajes = state.get("messages") or []
    pregunta = _ultimo_humano(mensajes)
    ultimo = mensajes[-1] if mensajes else None
    # Human al final = turno nuevo. AI al final = reintento del validador.
    turno_nuevo = es_turno_nuevo(ultimo)
    msgs: list[Any] = [SystemMessage(consigna_juez()), HumanMessage(pregunta or "(sin pregunta)")]
    # En un reintento el último mensaje es del bot; el motivo del validador sigue vivo.
    rechazo = "" if turno_nuevo else (state.get("motivo_validador") or "").strip()
    if rechazo:
        msgs.append(HumanMessage(f"El validador rechazó: {rechazo}. Decide de nuevo."))
    # invoke (no stream): el juez no pinta tokens; la TUI espera el update entero.
    respuesta = model.invoke(msgs)
    veredicto = parsear_veredicto(getattr(respuesta, "content", ""))
    salida = {
        "usar_web": veredicto.usar_web,
        "query_web": veredicto.query,
        "motivo_juez": veredicto.motivo,
        # Cada pasada por el juez invalida el ok anterior.
        "ok": False,
        # Nunca arrastramos un borrador rechazado a la siguiente pasada.
        "draft": "",
    }
    if turno_nuevo:
        # El checkpointer reutiliza el hilo: sin esto el tope de reintentos
        # del turno anterior bloquearía el siguiente.
        salida["intentos"] = 0
        salida["motivo_validador"] = ""
    return salida


def chatbot(state: State) -> dict:
    """Nodo 2: pide tools o crea un borrador privado para validar."""
    # stream() emite tokens al grafo (TUI); el resultado final es el mismo AIMessage.
    msgs = [
        SystemMessage(
            consigna_sistema(
                usar_web=state.get("usar_web"),
                query_web=state.get("query_web") or "",
                motivo_juez=state.get("motivo_juez") or "",
                motivo_validador=state.get("motivo_validador") or "",
            )
        ),
        *state["messages"],
    ]
    response = None
    for chunk in model_with_tools.stream(msgs):
        response = chunk if response is None else response + chunk
    if response is None:
        return {"draft": ""}
    tool_calls = getattr(response, "tool_calls", None) or getattr(
        response, "tool_call_chunks", None
    )
    if tool_calls:
        # ToolNode necesita el AIMessage/AIMessageChunk que contiene las llamadas.
        return {"messages": [response], "draft": ""}
    # No se añade a messages todavía: el validador debe aprobarlo primero.
    return {"draft": _texto(getattr(response, "content", ""))}


def validador(state: State) -> dict:
    """Nodo 4: ¿la respuesta cubre lo pedido? Si no, otra vuelta al juez."""
    mensajes = state.get("messages") or []
    pregunta = _ultimo_humano(mensajes)
    respuesta = str(state.get("draft") or _ultima_respuesta_bot(mensajes))
    usar_web = bool(state.get("usar_web"))
    evidencia = _evidencia_tools(mensajes)
    # Atajos sin LLM: mock, sin Tavily, temperatura sin número.
    motivo = rechazo_heuristico(
        pregunta=pregunta,
        respuesta=respuesta,
        usar_web=usar_web,
        hubo_buscar_web=_hubo_buscar_web(mensajes),
    )
    if motivo is None:
        # Nada obvio: el mismo modelo puntúa la respuesta con ok: si|no.
        chequeo = model.invoke(
            [
                SystemMessage(consigna_validador()),
                HumanMessage(
                    f"Pregunta: {pregunta}\n"
                    f"Respuesta: {respuesta}\n"
                    f"Juez usar_web: {usar_web}\n"
                    f"Hubo buscar_web: {_hubo_buscar_web(mensajes)}\n"
                    f"Evidencia de tools (fuente de verdad):\n"
                    f"{evidencia or '(ninguna)'}"
                ),
            ]
        )
        veredicto = parsear_validador(getattr(chequeo, "content", ""))
        ok, motivo = veredicto.ok, veredicto.motivo
    else:
        ok = False
    intentos = int(state.get("intentos") or 0)
    if not ok:
        # 1 = primer rechazo (reintenta); 2 = tope (END).
        intentos += 1
    return {"ok": ok, "motivo_validador": motivo, "intentos": intentos}


def publicar_respuesta(state: State) -> dict:
    """Publica el borrador únicamente después de que el validador dé ok."""
    draft = str(state.get("draft") or "").strip()
    if not draft:
        return {}
    return {"messages": [AIMessage(content=draft)], "draft": ""}


def _despues_chatbot(state: State) -> str:
    """Arista condicional: tool_calls → tools; si no → validador (nunca END)."""
    mensajes = state.get("messages") or []
    return ruta_tras_chatbot(mensajes[-1] if mensajes else None)


def _despues_validador(state: State) -> str:
    """Arista condicional: ok → publicar; rechazo → juez o END."""
    if state.get("ok"):
        return "publicar"
    destino = ruta_tras_validador(bool(state.get("ok")), int(state.get("intentos") or 0))
    return END if destino == "__end__" else destino


# START → juez → chatbot ⇄ tools → validador → END (o otra vuelta al juez).
builder = StateGraph(State)
builder.add_node("juez", juez)
builder.add_node("chatbot", chatbot)
# ToolNode recibe las mismas tools y devuelve ToolMessage con el resultado.
builder.add_node("tools", ToolNode(tools))
builder.add_node("validador", validador)
builder.add_node("publicar", publicar_respuesta)
builder.add_edge(START, "juez")
# El juez siempre pasa al chatbot: el veredicto viaja por el State, no por un if.
builder.add_edge("juez", "chatbot")
builder.add_conditional_edges(
    "chatbot",
    _despues_chatbot,
    {"tools": "tools", "validador": "validador"},
)
# Tras las tools, el chatbot redacta (o pide otra tool).
builder.add_edge("tools", "chatbot")
builder.add_conditional_edges(
    "validador",
    _despues_validador,
    {"juez": "juez", "publicar": "publicar", END: END},
)
builder.add_edge("publicar", END)
# Sin checkpointer, cada turno sería una conversación nueva.
graph = builder.compile(checkpointer=InMemorySaver())
