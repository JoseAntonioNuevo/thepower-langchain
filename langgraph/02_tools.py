"""02 — Tools: bind_tools + ToolNode + tools_condition. ~18 min."""

import os
import sys
from pathlib import Path

# Ejecutar ``python langgraph/02_tools.py`` debe encontrar ui desde la raíz.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

# Annotated añade metadatos a un tipo; aquí une la lista de mensajes con un reducer.
from typing import Annotated, TypedDict

# load_dotenv lee .env y mete las variables en el entorno (p. ej. OPENROUTER_API_KEY).
from dotenv import load_dotenv

# @tool convierte una función Python en una herramienta que el LLM puede pedir.
from langchain.tools import tool

# AnyMessage: tipo genérico de mensaje; HumanMessage: mensaje del usuario.
from langchain_core.messages import AnyMessage, HumanMessage

# Cliente LangChain para llamar modelos a través de OpenRouter.
from langchain_openrouter import ChatOpenRouter

# add_messages es el reducer: al devolver mensajes nuevos, se AÑADEN a la lista
# (no sustituyen el historial entero).
from langgraph.graph import START, StateGraph, add_messages

# ToolNode ejecuta las tools que el modelo haya pedido.
# tools_condition decide: ¿hay tool_calls? → nodo "tools"; si no → END.
from langgraph.prebuilt import ToolNode, tools_condition


# Carga la API key y el resto de variables del archivo .env.
load_dotenv()


# GPT-6 Luna. Chat Completions solo admite tools con reasoning.effort "none".
# service_tier "priority" es el modo rápido. El alias "fast" vuelve como default.
MODELO = "openai/gpt-6-luna"

# temperature=0: respuestas más deterministas (útil para demos de clase).
model = ChatOpenRouter(
    model=MODELO,
    temperature=0,
    reasoning={"effort": "none"},
    model_kwargs={"service_tier": "priority"},
)


# El docstring es lo que el modelo lee para saber CUÁNDO usar la tool.
@tool
def buscar_clima(ciudad: str) -> str:
    """Devuelve el tiempo actual en una ciudad (mock para la clase)."""

    # Interruptor de demo: simula un fallo de red sin tocar APIs reales.
    if os.getenv("DEMO_FORCE_TOOL_ERROR") == "1":
        raise TimeoutError("timeout simulado")

    # Mock fijo: no llama a un servicio meteorológico de verdad.
    return f"Soleado en {ciudad}"


# Lista de tools que el grafo y el modelo van a compartir.
tools = [buscar_clima]

# bind_tools adjunta el esquema de las tools al modelo:
# el LLM puede responder con texto O con una petición de tool (tool_calls).
model_with_tools = model.bind_tools(tools)


# Estado del grafo: solo el historial de mensajes.
# Annotated[..., add_messages] = "cuando un nodo devuelve messages, concaténalos".
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# Nodo del asistente: llama al LLM con todo el historial actual.
def chatbot(state: State) -> dict:
    response = model_with_tools.invoke(state["messages"])

    # Devolvemos la respuesta en una lista; add_messages la añade al estado.
    return {"messages": [response]}


# Montaje del grafo: START → chatbot ⇄ tools → (fin cuando no hay tools).
builder = StateGraph(State)
builder.add_node("chatbot", chatbot)

# ToolNode recibe las mismas tools: ejecuta la función pedida y crea un ToolMessage.
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "chatbot")

# Tras el chatbot, ruta condicional:
# - si el AIMessage trae tool_calls → "tools"
# - si no → END (tools_condition usa el nombre de nodo "tools" por convenio)
builder.add_conditional_edges("chatbot", tools_condition)

# Tras ejecutar tools, volvemos al chatbot para que redacte la respuesta final
# (o pida otra tool).
builder.add_edge("tools", "chatbot")
graph = builder.compile()


if __name__ == "__main__":

    from ui.consola import BRIGHT, DATO, THINK, TOOL, banner, grafo_ascii, panel, spinner

    pregunta = "¿Qué tiempo hace en Madrid?"
    print(banner("02", "Tools: bind_tools + ToolNode", 18))
    print(panel("grafo", grafo_ascii(["chatbot", "tools", "chatbot"]), THINK))

    # Una sola pregunta: el modelo debería pedir buscar_clima("Madrid").
    with spinner("el modelo decide…"):
        resultado = graph.invoke({"messages": [HumanMessage(pregunta)]})

    peticiones: list[str] = []
    datos: list[str] = []
    for mensaje in resultado["messages"]:
        if getattr(mensaje, "type", None) == "ai":
            for llamada in getattr(mensaje, "tool_calls", None) or []:
                nombre = llamada.get("name", "?")
                args = llamada.get("args", {})
                argumentos = ", ".join(f"{clave}={valor!r}" for clave, valor in args.items())
                peticiones.append(f"{nombre}({argumentos})")
        elif getattr(mensaje, "type", None) == "tool":
            nombre = getattr(mensaje, "name", None) or "tool"
            datos.append(f"{nombre}: {mensaje.content}")

    print(panel("pregunta", pregunta, BRIGHT))
    print(panel("tool solicitada", "\n".join(peticiones) or "(ninguna)", TOOL))
    print(panel("dato devuelto", "\n".join(datos) or "(sin resultado)", DATO))
    # El último mensaje suele ser la respuesta en lenguaje natural del bot.
    print(panel("respuesta", str(resultado["messages"][-1].content), BRIGHT))
