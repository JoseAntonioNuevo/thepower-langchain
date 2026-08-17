"""Nodo validador: ¿la respuesta cubre lo pedido? Heurística primero, luego parse."""

from __future__ import annotations

# re: atajos deterministas (temperatura sin número, mock "Soleado en").
import re
from dataclasses import dataclass
from typing import Any, Literal

# Reutilizamos el parseo "clave: valor" y los sí/no del juez (mismo formato).
from utilities.juez import _campos_etiquetados, _SI, _NO

# Un rechazo (intentos=1) reintenta; el segundo (intentos=2) cierra el ciclo.
MAX_REINTENTOS = 1

# La pregunta pide un dato numérico: temperatura, grados o "exacto/exacta".
_PIDE_NUMERO = re.compile(
    r"temperatura|grados|\b°c\b|\bcelsius\b|exact[oa]",
    re.IGNORECASE,
)
# Cualquier dígito cuenta: "24 °C", "2-1", "2026".
_HAY_NUMERO = re.compile(r"\d")
# El mock de buscar_clima siempre devuelve "Soleado en {ciudad}".
_MOCK_CLIMA = re.compile(r"soleado en\b", re.IGNORECASE)


# Resultado del validador: ok + motivo para la TUI y para el juez en el reintento.
@dataclass(frozen=True)
class VeredictoValidador:
    ok: bool
    motivo: str


def consigna_validador() -> str:
    """Instrucciones del nodo validador: un veredicto etiquetado."""
    return (
        "Eres el validador. ¿La respuesta cubre lo que pidió el usuario "
        "con datos de las tools, sin inventar?\n"
        "La evidencia de las tools es la fuente de verdad actual. "
        "No uses tu conocimiento previo para contradecirla ni para afirmar "
        "que un hecho todavía no ocurrió.\n"
        "Evalúa si la respuesta contesta la pregunta y está respaldada por "
        "la evidencia recibida. Rechaza solo una contradicción u omisión "
        "demostrable en esa evidencia.\n"
        "Si pidió un número (temperatura, marcador) y no está, no está ok.\n"
        "Si el juez pidió web y no hay resultado de buscar_web, no está ok.\n"
        "Responde SOLO:\n"
        "ok: si|no\n"
        "motivo: ..."
    )


def parsear_veredicto(texto: Any) -> VeredictoValidador:
    """Lee ok/motivo. Si no se entiende, rechaza para que el ciclo se vea."""
    campos = _campos_etiquetados(texto)
    crudo = campos.get("ok", "").lower()
    if crudo in _SI:
        ok = True
    elif crudo in _NO:
        ok = False
    else:
        # Ilegible → rechazamos: la TUI muestra "reintenta" al menos una vez.
        ok = False
    motivo = campos.get("motivo", "")
    if not campos:
        motivo = "veredicto ilegible"
    return VeredictoValidador(ok=ok, motivo=motivo)


def rechazo_heuristico(
    *,
    pregunta: str,
    respuesta: str,
    usar_web: bool,
    hubo_buscar_web: bool,
) -> str | None:
    """Rechazo determinista. None = pasar al LLM (o aceptar si no hace falta)."""
    # El juez dijo web y el modelo contestó de memoria / con el mock.
    if usar_web and not hubo_buscar_web:
        return "el juez pidió buscar_web y no se usó"
    # El mock de clase se coló en la respuesta final.
    if _MOCK_CLIMA.search(respuesta or ""):
        return "respuesta de mock (Soleado en …)"
    # Pidieron temperatura/exacto y no hay ningún dígito.
    if _PIDE_NUMERO.search(pregunta or "") and not _HAY_NUMERO.search(respuesta or ""):
        return "falta el número"
    # Nada obvio: el nodo validador pregunta al LLM.
    return None


def debe_reintentar(ok: bool, intentos: int) -> bool:
    """Un rechazo (intentos=1) reintenta; el segundo cierra el ciclo."""
    # intentos ya viene incrementado por el nodo cuando ok es False.
    return (not ok) and intentos <= MAX_REINTENTOS


def ruta_tras_validador(ok: bool, intentos: int) -> Literal["juez", "__end__"]:
    """Destino del grafo: otra vuelta al juez o END (LangGraph usa __end__)."""
    if debe_reintentar(ok, intentos):
        return "juez"
    return "__end__"
