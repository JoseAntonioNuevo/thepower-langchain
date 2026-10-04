"""Un único grafo para S5 y S6. La instrumentación queda fuera del núcleo."""

from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END, add_messages
from .config import ROOT
from .tools import make_tools


class State(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_count: int
    errors: list[str]
    calls: list[dict]
    route: list[str]
    status: str
    usage: list[dict]


def local_prompt(version="v2"):
    if version not in {"v1", "v2"}:
        raise ValueError("Versión local debe ser v1 o v2")
    return (ROOT / "prompts/soporte" / f"{version}.txt").read_text().strip()


def prompt_template(text, metadata=None):
    # Tupla system literal: no interpretar llaves del texto como variables.
    from langchain_core.messages import SystemMessage

    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=text),
            MessagesPlaceholder("messages"),
        ]
    ).with_config(metadata=metadata or {})


def build_graph(model, *, prompt=None, checkpointer=None, tools=None, use_tools=True):
    """Inyectar model/prompt/checkpointer permite tests sin credenciales ni red."""
    tool_list = make_tools() if tools is None else tools
    by_name = {t.name: t for t in tool_list}
    template = prompt if prompt is not None else prompt_template(local_prompt())
    with_tools = model.bind_tools(tool_list) if use_tools else model
    chain = template | with_tools
    final_chain = template | model

    def inicio(state: State):
        return {
            "tool_count": 0,
            "errors": [],
            "calls": [],
            "usage": [],
            "route": ["inicio"],
            "status": "running",
        }

    def chatbot(state: State, config: RunnableConfig):
        final = not use_tools or state["tool_count"] >= 2
        route = [*state["route"], "respuesta_final" if final else "chatbot"]
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
                "errors": [*state["errors"], f"modelo:{type(exc).__name__}"],
                "status": "model_error",
                "route": route,
            }
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
                "errors": [*state["errors"], "limite_final"],
                "status": "limit",
                "usage": [*state["usage"], record],
                "route": route,
            }
        if not tool_calls and not str(msg.content).strip():
            msg = AIMessage(
                content="No he obtenido una respuesta utilizable. Reformula la consulta."
            )
        return {
            "messages": [msg],
            "route": route,
            "usage": [*state["usage"], record],
            "status": "tools" if tool_calls else "done",
        }

    def ejecutar_tools(state: State, config: RunnableConfig):
        count, errors, calls = (
            state["tool_count"],
            list(state["errors"]),
            list(state["calls"]),
        )
        results = []
        for call in state["messages"][-1].tool_calls:
            if count >= 2:
                body = "Error: límite de dos herramientas agotado"
                errors.append("limite_herramientas")
                calls.append({"name": call["name"], "executed": False, "ok": False})
            else:
                count += 1
                try:
                    target = by_name.get(call["name"])
                    if target is None:
                        raise ValueError("herramienta_desconocida")
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
            results.append(
                ToolMessage(content=body, tool_call_id=call["id"], name=call["name"])
            )
        return {
            "messages": results,
            "tool_count": count,
            "errors": errors,
            "calls": calls,
            "route": [*state["route"], "tools"],
        }

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
    return builder.compile(checkpointer=checkpointer)
