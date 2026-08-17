"""Fecha de hoy del sistema. Gemma no sabe en qué año estamos."""

from __future__ import annotations

from datetime import date

from langchain.tools import tool

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def _texto_fecha(hoy: date) -> str:
    return f"{hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}"


def consigna_sistema(
    hoy: date | None = None,
    *,
    # None = el juez aún no ha hablado (tests / lección 02 no pasan veredicto).
    usar_web: bool | None = None,
    query_web: str = "",
    motivo_juez: str = "",
    motivo_validador: str = "",
) -> str:
    """Consigna del chatbot: tools + veredicto del juez (si lo hay)."""
    dia = _texto_fecha(hoy or date.today())
    # Reglas fijas: Tavily es la única tool real; clima/ropa son mocks de clase.
    lineas = [
        f"Eres un asistente útil. Contexto: hoy es {dia}.",
        "Ante cualquier pregunta:",
        "1. Entiende qué pide. Si es ambiguo, asume lo más probable y dilo, "
        "o pregunta una cosa concreta.",
        "2. Si el dato puede ser falso o no lo sabes, usa una tool. No inventes.",
        "3. Elige la tool que encaje (puedes encadenar varias):",
        "   - buscar_web: ÚNICA tool con internet real (Tavily). Hechos, noticias, "
        "temperatura real, resultados, precios, instrucciones actuales.",
        "   - buscar_clima: MOCK de clase. Nunca para temperatura real ni datos actuales.",
        "   - tendencia_ropa: MOCK de clase. Nunca para moda o hechos reales.",
        "   - fecha_hoy: solo si el calendario forma parte de la respuesta.",
        "4. Con el resultado, responde claro y solo con datos de las tools. "
        "Si pidieron un número, inclúyelo. Saludos y charla no necesitan tools.",
    ]
    # El juez ya decidió: el chatbot no elige a ciegas entre mock y Tavily.
    if usar_web:
        query = query_web.strip() or "la pregunta del usuario"
        lineas.append(
            f"5. El juez obliga a buscar_web (query: {query}). "
            "No uses buscar_clima ni tendencia_ropa para esto."
        )
        if motivo_juez.strip():
            lineas.append(f"   Motivo del juez: {motivo_juez.strip()}")
    elif usar_web is False:
        lineas.append("5. El juez no pide internet. No llames a buscar_web.")
    # Solo en un reintento: el validador explica qué falló la vuelta anterior.
    if motivo_validador.strip():
        lineas.append(
            f"6. El validador rechazó la respuesta anterior: "
            f"{motivo_validador.strip()}. Corrige."
        )
    return "\n".join(lineas)


@tool
def fecha_hoy() -> str:
    """Devuelve la fecha de hoy. Úsala solo si el calendario es parte de la respuesta."""
    return _texto_fecha(date.today())
