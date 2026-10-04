"""Primitivas de salida compartidas por las lecciones de LangGraph.

La API devuelve texto para que las lecciones puedan seguir siendo scripts
simples y los tests no necesiten una terminal real. El color se activa solo
cuando la salida es un TTY; ``NO_COLOR`` siempre lo desactiva.
"""

from __future__ import annotations

import os
import sys
import threading
import textwrap
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import TextIO

BG = "#16161e"
SURFACE = "#1a1b26"
BORDER = "#414868"
DIM = "#565f89"
BRIGHT = "#c0caf5"
USER = "#7aa2f7"
THINK = "#9d7cd8"
TOOL = "#e0af68"
DATO = "#9ece6a"
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧"


def _color_enabled(stream: TextIO | None = None) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    stream = stream or sys.stdout
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError):
        return False


def _paint(text: str, color: str, *, stream: TextIO | None = None) -> str:
    """Aplica ANSI 24-bit solo cuando la salida conectada lo soporta."""
    if not _color_enabled(stream):
        return text
    value = color.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"\033[38;2;{red};{green};{blue}m{text}\033[0m"


def banner(leccion: str, titulo: str, minutos: int | None = None) -> str:
    """Renderiza una cabecera de lección compacta y legible."""
    texto = f"{leccion} · {titulo}"
    if minutos is not None:
        texto += f" · ~{minutos} min"
    interior = f" {texto} "
    borde = "─" * len(interior)
    return "\n".join(
        (
            _paint(f"╭{borde}╮", USER),
            _paint(f"│{interior}│", BRIGHT),
            _paint(f"╰{borde}╯", USER),
        )
    )


def panel(titulo: str, cuerpo: str, color: str = BRIGHT, *, width: int | None = None) -> str:
    """Renderiza un panel redondeado para estados, resultados o explicaciones."""
    lineas = cuerpo.splitlines() or [""]
    if width is not None:
        # Ancho exterior común para alinear paneles y envolver textos largos.
        ancho = max(len(titulo) + 2, width - 4)
        lineas = [parte for linea in lineas
                  for parte in (textwrap.wrap(linea, width=ancho, replace_whitespace=False) or [""])]
    else:
        ancho = max(len(titulo) + 2, *(len(linea) for linea in lineas))
    hueco = max(1, ancho - len(titulo) - 1)
    top = f"╭─ {titulo} " + "─" * hueco + "╮"
    cuerpo_render = [f"│ {linea.ljust(ancho)} │" for linea in lineas]
    bottom = "╰" + "─" * (ancho + 2) + "╯"
    return "\n".join(
        [_paint(top, color), *(_paint(linea, color) for linea in cuerpo_render), _paint(bottom, color)]
    )


def grafo_ascii(nodos: Iterable[str]) -> str:
    """Dibuja una ruta corta del grafo en el mismo vocabulario que la TUI."""
    cajas = [f"╭─ {nombre} ─╮" for nombre in nodos]
    ruta = ["○ START", *cajas, "○ END"]
    return "  →  ".join(ruta)


@contextmanager
def spinner(
    texto: str,
    *,
    stream: TextIO | None = None,
    enabled: bool | None = None,
    interval: float = 0.08,
) -> Iterator[None]:
    """Muestra un spinner durante una llamada bloqueante y limpia su línea."""
    salida = stream or sys.stdout
    activo = _color_enabled(salida) if enabled is None else enabled
    if not activo:
        yield
        return

    detenido = threading.Event()
    ultimo_ancho = [0]

    def _pintar() -> None:
        indice = 0
        while not detenido.is_set():
            contenido = f"{_SPINNER[indice % len(_SPINNER)]} {texto}"
            salida.write("\r" + _paint(contenido, THINK, stream=salida))
            salida.flush()
            ultimo_ancho[0] = len(contenido)
            indice += 1
            if detenido.wait(interval):
                break

    hilo = threading.Thread(target=_pintar, name="langgraph-spinner", daemon=True)
    hilo.start()
    try:
        yield
    finally:
        detenido.set()
        hilo.join(timeout=max(0.2, interval * 4))
        salida.write("\r" + (" " * ultimo_ancho[0]) + "\r")
        salida.flush()
