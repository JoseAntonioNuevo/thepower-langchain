"""Grafo de clase 1 (04): mismo ciclo que lessons/04_chatbot.py."""

# importlib: el fichero se llama 04_chatbot.py (empieza por número).
import importlib
import sys
from pathlib import Path

# 04 vive en lessons/; este módulo se importa desde la raíz del repo.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Un solo sitio define juez → chatbot ⇄ tools → validador.
# La clase de observabilidad (7 oct) importa `graph` de aquí y solo lo instrumenta.
_04 = importlib.import_module("lessons.04_chatbot")
MODELO = _04.MODELO
graph = _04.graph
thread_id = _04.thread_id
