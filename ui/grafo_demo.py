"""Presentación docente de la transformación de texto del ejemplo 01.

render_demo recibe la entrada y el resultado real de graph.invoke: no ejecuta
otra transformación ni llama a un modelo. Ordena la salida en resultado,
recorrido y explicación, con paneles alineados y texto adaptado a la terminal.
El estilo reutiliza los colores de consola.py y respeta NO_COLOR.
"""

import shutil
import textwrap
from ui.consola import BRIGHT, DATO, THINK, banner, panel


def render_demo(entrada: str, resultado: dict, *, width: int | None = None) -> str:
    """Devuelve la explicación visual usando el resultado real del grafo."""
    ancho = max(36, min(width or shutil.get_terminal_size().columns, 76))
    return "\n\n".join([
        banner("01", "De minúsculas a mayúsculas"),
        panel("Transformación del texto",
              f"Entrada    → {entrada}\nResultado  → {resultado['texto']}",
              DATO, width=ancho),
        panel("Recorrido del grafo",
              "START → mayusculas → END\nInicio  → función Python → fin",
              THINK, width=ancho),
        panel("Qué ha hecho y cómo",
              "1. Estado: recibe un diccionario con la clave texto.\n"
              "2. Nodo: mayusculas aplica .upper() al texto recibido.\n"
              "3. Aristas: conectan START con el nodo y el nodo con END.\n"
              "4. invoke(): ejecuta el recorrido y devuelve el estado final.\n"
              f"Estado final del grafo: {resultado!r}",
              BRIGHT, width=ancho),
        textwrap.fill("Python transforma; LangGraph organiza. Sin modelo de IA ni API.", width=ancho),
    ])
