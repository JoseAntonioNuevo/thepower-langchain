"""Primera etapa de S5: un grafo determinista, sin modelo ni claves de API.

State define el texto compartido. mayusculas recibe ese estado y devuelve la
actualización del texto. StateGraph registra el nodo y las conexiones de inicio
y fin; compile prepara el grafo. Al ejecutar el archivo, invoke transforma
«hola thepower» y los paneles muestran la entrada y el resultado.
Sirve para entender estado, nodo y aristas antes de añadir un modelo.
"""

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

    import argparse
    from ui.grafo_demo import render_demo

    # Mantener una entrada preparada y permitir cambiarla para probar otro texto.
    parser = argparse.ArgumentParser(description="Transforma un texto mediante un grafo de un nodo")
    parser.add_argument("--texto", default="hola thepower", help="Texto que recibe el grafo")
    args = parser.parse_args()

    # invoke() recorre el grafo una vez con el estado inicial.
    entrada = args.texto
    resultado = graph.invoke({"texto": entrada})
    # La presentación queda separada de la lógica para enseñar el grafo con claridad.
    print(render_demo(entrada, resultado))
