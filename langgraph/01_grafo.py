"""01 — Un grafo es funciones + aristas. ~12 min. Sin LLM, sin API key."""

import sys
from pathlib import Path

# Ejecutar ``python langgraph/01_grafo.py`` debe encontrar ui desde la raíz.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

# TypedDict describe un diccionario con claves fijas y tipos conocidos.
from typing import TypedDict

# Piezas de LangGraph:
# - StateGraph: constructor del grafo (nodos + aristas).
# - START: punto de entrada oficial (de dónde arranca la ejecución).
# - END: punto de salida oficial (dónde termina).
from langgraph.graph import END, START, StateGraph


# Estado compartido: lo que viaja de nodo a nodo.
# Cada nodo lee este diccionario y puede devolver solo las claves que cambia.
class State(TypedDict):
    texto: str  # único dato del ejemplo: una cadena que iremos transformando


# Un nodo es una función: recibe el estado y devuelve un parche (dict).
# LangGraph mezcla ese parche con el estado anterior.
def mayusculas(state: State) -> dict:

    # .upper() convierte el texto a mayúsculas; devolvemos solo "texto".
    return {"texto": state["texto"].upper()}


# Creamos el grafo indicando qué forma tiene el estado.
builder = StateGraph(State)

# Registramos la función como nodo con el nombre "mayusculas".
builder.add_node("mayusculas", mayusculas)

# Arista fija: al empezar, ir siempre al nodo mayusculas.
builder.add_edge(START, "mayusculas")

# Arista fija: después de mayusculas, terminar.
builder.add_edge("mayusculas", END)

# compile() congela el diseño y produce un grafo ejecutable.
graph = builder.compile()


# Solo corre si ejecutas este archivo (no si lo importas desde otro módulo).
if __name__ == "__main__":

    from ui.consola import BRIGHT, DATO, THINK, banner, grafo_ascii, panel

    # invoke() recorre el grafo una vez con el estado inicial.
    entrada = "hola thepower"
    print(banner("01", "Un grafo es funciones + aristas", 12))
    print(panel("grafo", grafo_ascii(["mayusculas"]), THINK))
    resultado = graph.invoke({"texto": entrada})

    print(
        panel(
            "estado",
            f"antes   · {entrada}\ndespués · {resultado['texto']}",
            DATO,
        )
    )
    print(panel("salida Python", str(resultado), BRIGHT))
