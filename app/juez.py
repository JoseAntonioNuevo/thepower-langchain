"""Nodo juez: decide si hace falta Tavily. No busca; solo parsea un veredicto."""

from __future__ import annotations

# dataclass: VeredictoJuez es inmutable (frozen) y genera __init__ solo.
from dataclasses import dataclass
# date.today() ancla la consigna al calendario real (Gemma no sabe el año).
from datetime import date
# Any: el modelo a veces devuelve str, a veces bloques. Literal: destinos de ruta.
from typing import Any, Literal

# Misma fecha en español que usa buscar_web y la consigna del chatbot.
from app.fecha_hoy import _texto_fecha


# Resultado del juez: tres campos que el grafo guarda en el State.
@dataclass(frozen=True)
class VeredictoJuez:
    # True → el chatbot DEBE pedir buscar_web (Tavily).
    usar_web: bool
    # Query concreta y fechada que el juez propone (ciudad, año, magnitud).
    query: str
    # Por qué decidió sí o no: la TUI y el validador lo pueden mostrar.
    motivo: str


# Gemma no siempre escribe "si": aceptamos variantes para no fallar el parseo.
_SI = {"si", "sí", "yes", "true", "1"}
_NO = {"no", "false", "0"}


def _texto_plano(texto: Any) -> str:
    """Saca texto de un content de LangChain (str, lista de bloques o None)."""
    if texto is None:
        return ""
    if isinstance(texto, str):
        return texto
    # Algunos proveedores mandan content como [{type, text}, …].
    if isinstance(texto, list):
        partes: list[str] = []
        for block in texto:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if t:
                    partes.append(str(t))
        return "\n".join(partes)
    return str(texto)


def _campos_etiquetados(texto: Any) -> dict[str, str]:
    """Convierte 'clave: valor' por línea en un dict. Ignora el resto."""
    campos: dict[str, str] = {}
    for linea in _texto_plano(texto).splitlines():
        if ":" not in linea:
            continue
        # split(":", 1): el valor puede llevar más dos puntos (URLs, horas).
        clave, valor = linea.split(":", 1)
        campos[clave.strip().lower()] = valor.strip()
    return campos


def consigna_juez(hoy: date | None = None) -> str:
    """Instrucciones del nodo juez: un veredicto etiquetado, sin buscar."""
    # Si el test pasa una fecha fija, no usamos date.today().
    dia = _texto_fecha(hoy or date.today())
    return (
        f"Hoy es {dia}. Eres el juez de un grafo. NO buscas; solo decides.\n"
        "Si la pregunta pide un hecho actual (tiempo, temperatura, resultados, "
        "noticias, precios, personas, cómo se hace algo hoy), usa web.\n"
        "Saludos, opiniones y charla no necesitan web.\n"
        "La query debe ir fechada y ser concreta (ciudad, año, magnitud).\n"
        "Responde SOLO con este formato:\n"
        "usar_web: si|no\n"
        "query: ...\n"
        "motivo: ..."
    )


def parsear_veredicto(texto: Any) -> VeredictoJuez:
    """Lee el bloque etiquetado del modelo. Si no se entiende, no obliga web."""
    campos = _campos_etiquetados(texto)
    crudo = campos.get("usar_web", "").lower()
    if crudo in _SI:
        usar_web = True
    elif crudo in _NO:
        usar_web = False
    else:
        # Ilegible → no forzamos Tavily (un saludo no debe gastar la API).
        usar_web = False
    motivo = campos.get("motivo", "")
    if not campos:
        motivo = "veredicto ilegible"
    return VeredictoJuez(
        usar_web=usar_web,
        query=campos.get("query", ""),
        motivo=motivo,
    )


def ruta_tras_chatbot(ultimo: Any) -> Literal["tools", "validador"]:
    """Tras el LLM: si hay tool_calls → tools; si no → validador."""
    # tools_condition de LangGraph iría a END; aquí el ciclo sigue al validador.
    if getattr(ultimo, "tool_calls", None):
        return "tools"
    return "validador"


def es_turno_nuevo(ultimo: Any) -> bool:
    """True si el último mensaje es del usuario: arranque de turno, no un reintento."""
    # En un reintento el último mensaje es del bot (la respuesta rechazada).
    return getattr(ultimo, "type", None) == "human"
