"""03 — Memoria = checkpointer + thread_id, no el State. ~15 min."""

# Pausa entre invokes: Cerebras limita ráfagas y 03 hace 3 llamadas seguidas.
import sys
import time
from pathlib import Path

# Ejecutar ``python lessons/03_memoria.py`` debe encontrar utilities desde la raíz.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Annotated une el tipo de la lista con el reducer add_messages.
from typing import Annotated, TypedDict

# load_dotenv mete OPENROUTER_API_KEY (y el resto) desde .env al entorno.
from dotenv import load_dotenv

# AnyMessage: cualquier mensaje del historial; HumanMessage: lo que escribe el usuario.
from langchain_core.messages import AnyMessage, HumanMessage

# RunnableConfig tipa el dict de invoke(..., config) donde va thread_id.
from langchain_core.runnables import RunnableConfig

# Cliente LangChain para llamar el modelo a través de OpenRouter.
from langchain_openrouter import ChatOpenRouter

# InMemorySaver guarda el estado de cada hilo en RAM (se pierde al cerrar el proceso).
from langgraph.checkpoint.memory import InMemorySaver

# START/END: entrada y salida. add_messages: al devolver messages, se AÑADEN.
from langgraph.graph import END, START, StateGraph, add_messages


load_dotenv()


# OpenRouter; Cerebras primero, otro proveedor si hay 429.
MODELO = "google/gemma-4-31b-it"
model = ChatOpenRouter(
    model=MODELO,
    temperature=0,
    openrouter_provider={"order": ["Cerebras"]},
)


# El State solo describe la forma de un turno. NO es la memoria a largo plazo:
# si compilas sin checkpointer, cada invoke() empieza de cero.
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# Nodo único: el modelo ve los mensajes que el checkpointer haya recargado.
def chatbot(state: State) -> dict:
    response = model.invoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# En producción el checkpointer sería Postgres.
# compile(checkpointer=...) hace que LangGraph:
# 1) cargue el estado previo del thread_id
# 2) ejecute el grafo
# 3) guarde el estado nuevo bajo ese mismo thread_id
graph = builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":

    from utilities.consola import BRIGHT, DATO, THINK, banner, grafo_ascii, panel, spinner

    # config.configurable.thread_id = "carpeta" de conversación.
    # Mismo id → mismo historial. Otro id → conversación vacía e independiente.
    mismo_hilo: RunnableConfig = {"configurable": {"thread_id": "usuario_123"}}
    otro_hilo: RunnableConfig = {"configurable": {"thread_id": "otro_hilo"}}

    print(banner("03", "Memoria: checkpointer + thread_id", 15))
    print(panel("grafo", grafo_ascii(["chatbot"]), THINK))

    # Turno 1: el usuario se presenta. El checkpointer guarda "me llamo Alex".
    with spinner("el modelo responde…"):
        r1 = graph.invoke(
            {"messages": [HumanMessage("Hola, me llamo Alex")]},
            mismo_hilo,
        )
    print(
        panel(
            "turno 1 · usuario_123",
            f"pregunta · Hola, me llamo Alex\nrespuesta · {r1['messages'][-1].content}",
            BRIGHT,
        )
    )

    # Cerebras limita ráfagas; 03 hace 3 invokes seguidos.
    with spinner("pausa anti-429 · 2s"):
        time.sleep(2)

    # Turno 2: mismo thread_id. El modelo debería ver el saludo anterior y recordar Alex.
    with spinner("el modelo responde…"):
        r2 = graph.invoke(
            {"messages": [HumanMessage("¿Cómo me llamo?")]},
            mismo_hilo,
        )
    print(
        panel(
            "turno 2 · usuario_123",
            f"pregunta · ¿Cómo me llamo?\nrespuesta · {r2['messages'][-1].content}",
            DATO,
        )
    )

    with spinner("pausa anti-429 · 2s"):
        time.sleep(2)

    # Turno 3: otro thread_id. No hay historial → no debería saber el nombre.
    with spinner("el modelo responde…"):
        r3 = graph.invoke(
            {"messages": [HumanMessage("¿Cómo me llamo?")]},
            otro_hilo,
        )
    print(
        panel(
            "turno 3 · otro_hilo",
            f"pregunta · ¿Cómo me llamo?\nrespuesta · {r3['messages'][-1].content}",
            BRIGHT,
        )
    )
