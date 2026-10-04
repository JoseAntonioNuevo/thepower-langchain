"""04 — Chatbot: juez + tools + validador + TUI. ~20 min."""

import sys
from pathlib import Path

# python langgraph/avanzado/04_chatbot.py pone langgraph/ en sys.path, no la raíz del repo.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from app.graph import MODELO, graph, thread_id
from ui.chat_tui import run_tui

if __name__ == "__main__":
    # El ciclo vive en app/graph.py. Aquí solo se lanza la interfaz.
    run_tui(
        graph,
        {"configurable": {"thread_id": thread_id}},
        modelo=MODELO,
        thread_id=thread_id,
    )
