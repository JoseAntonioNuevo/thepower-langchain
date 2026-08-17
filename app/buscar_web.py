"""Tool real: búsqueda web con Tavily. Sin modelo ni TUI."""

from __future__ import annotations

# os.getenv lee TAVILY_API_KEY y el interruptor de demo DEMO_FORCE_TOOL_ERROR.
import os
from datetime import date
from typing import Any

# @tool publica nombre, argumentos y docstring al LLM (bind_tools).
from langchain.tools import tool
# Cliente oficial: TavilyClient.search(...) → dict con answer + results.
from tavily import TavilyClient

# Fecha en español: "17 de agosto de 2026". Gemma no sabe en qué año estamos.
from app.fecha_hoy import _texto_fecha

# Mensaje que ve el modelo (y la TUI) si falta la clave: el grafo no se rompe.
FALTA_CLAVE = "Falta TAVILY_API_KEY en .env"
# advanced + 5 hits: bastante contexto sin saturar el historial del chat.
MAX_RESULTADOS = 5
# 400 chars: cabe una temperatura o un marcador; 160 recortaba el dato útil.
MAX_SNIPPET = 400


def _snippet(texto: Any) -> str:
    """Normaliza espacios y recorta el contenido de un resultado de Tavily."""
    limpio = " ".join(str(texto or "").split())
    if len(limpio) <= MAX_SNIPPET:
        return limpio
    return limpio[: MAX_SNIPPET - 1] + "…"


def _query_fechada(query: str, hoy: date | None = None) -> str:
    """Antepone la fecha de hoy para que Tavily no devuelva hechos viejos."""
    # "quién ganó el mundial" sin fecha → 2022; con "17 de agosto de 2026" → 2026.
    return f"{_texto_fecha(hoy or date.today())} — {query}"


def _formatear_busqueda(payload: dict[str, Any]) -> str:
    """Convierte la respuesta de Tavily en un texto corto para el chat."""
    lineas: list[str] = []
    # include_answer="advanced": Tavily resume primero; el modelo se apoya ahí.
    answer = (payload.get("answer") or "").strip()
    if answer:
        lineas.append(answer)
    for item in (payload.get("results") or [])[:MAX_RESULTADOS]:
        titulo = (item.get("title") or "sin título").strip()
        snippet = _snippet(item.get("content"))
        url = (item.get("url") or "").strip()
        if snippet:
            lineas.append(f"- {titulo} — {snippet}")
        else:
            lineas.append(f"- {titulo}")
        # La TUI oculta las URLs en el globo; el modelo sí las ve en el ToolMessage.
        if url:
            lineas.append(f"  {url}")
    if not lineas:
        return "Sin resultados."
    return "\n".join(lineas)


@tool
def buscar_web(query: str) -> str:
    """Única tool con internet real (Tavily). Hechos, noticias, temperatura real, resultados, precios. Sé concreto en la query."""
    # Mismo interruptor que los mocks: la demo de error no toca la red.
    if os.getenv("DEMO_FORCE_TOOL_ERROR") == "1":
        raise TimeoutError("timeout simulado")
    clave = os.getenv("TAVILY_API_KEY", "").strip()
    if not clave:
        return FALTA_CLAVE
    try:
        cliente = TavilyClient(api_key=clave)
        payload = cliente.search(
            # Fecha delante: Tavily prioriza resultados del año en curso.
            _query_fechada(query),
            # advanced + answer advanced: más fuentes y un resumen usable.
            search_depth="advanced",
            include_answer="advanced",
            max_results=MAX_RESULTADOS,
            # chunks_per_source solo aplica con search_depth="advanced".
            chunks_per_source=3,
            timeout=15,
        )
    except Exception as exc:
        # El grafo sigue: el validador verá el error y puede reintentar.
        return f"Error de búsqueda: {exc}"
    return _formatear_busqueda(payload if isinstance(payload, dict) else {})
