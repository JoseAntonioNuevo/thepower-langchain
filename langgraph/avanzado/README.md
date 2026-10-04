# Ejemplos originales y ampliación

El recorrido principal de la clase está un nivel arriba, numerado del 01 al 05. Estos tres ejemplos conservan el material original y se ejecutan desde la raíz del repositorio:

| Archivo | Contenido | Comando |
|---|---|---|
| `02_tools.py` | Herramienta ficticia de clima con ToolNode | `python langgraph/avanzado/02_tools.py` |
| `03_memoria.py` | Memoria en RAM y separación de hilos | `python langgraph/avanzado/03_memoria.py` |
| `04_chatbot.py` | TUI del agente con juez, herramientas y validador | `python langgraph/avanzado/04_chatbot.py` |

La memoria de `03_memoria.py` se pierde al cerrar el proceso. La práctica principal demuestra persistencia en SQLite con `langgraph/04_memoria.py`. El agente avanzado utiliza `app/graph.py`; el principal utiliza `app/soporte/graph.py`.
