"""Parser de mensajes LangGraph → líneas de chat. Sin I/O."""

from __future__ import annotations

# dataclass: ChatLine es inmutable (frozen) y genera __init__ solo.
from dataclasses import dataclass, field

# count(1): ids únicos 1, 2, 3… para que OpenTUI reconcilie filas por key.
from itertools import count
from typing import Any, Literal

# Kind: los "papeles" que la TUI sabe pintar (tú, pensar, tool, dato, bot…).
Kind = Literal[
    "human", "thinking", "tool", "dato", "bot", "error", "hint", "juez", "validador"
]

# Contador de proceso: cada ChatLine nueva recibe un key distinto.
_keys = count(1)


def _key(kind: str) -> str:
    """Id estable tipo 'bot-12' para el For de OpenTUI."""
    return f"{kind}-{next(_keys)}"


@dataclass(frozen=True)
class ChatLine:
    """Una fila del chat: tipo visual, texto y key de reconciliación."""

    kind: Kind
    text: str
    # Si el caller no pasa key, inventamos uno para no chocar con otras filas.
    key: str = field(default_factory=lambda: _key("line"))


def _texto(content: Any) -> str:
    """Saca texto plano del content de un mensaje (str, lista de bloques o None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # Algunos modelos mandan content como lista de bloques {type, text}.
    if isinstance(content, list):
        partes: list[str] = []
        for block in content:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict) and block.get("type") in {None, "text"}:
                t = block.get("text") or block.get("content")
                if t:
                    partes.append(str(t))
        return "\n".join(partes)
    return str(content)


def _razonamiento(mensaje: Any) -> str | None:
    """Lee el 'pensar' del modelo si el proveedor lo expone (Gemma/OpenRouter)."""
    # Camino 1: content_blocks con type=reasoning (API nueva de LangChain).
    for block in getattr(mensaje, "content_blocks", None) or []:
        if isinstance(block, dict) and block.get("type") == "reasoning":
            razon = block.get("reasoning") or block.get("text")
            if razon:
                return str(razon)
    # Camino 2: additional_kwargs (algunos proveedores lo dejan ahí).
    extra = getattr(mensaje, "additional_kwargs", None) or {}
    for clave in ("reasoning", "reasoning_content"):
        if extra.get(clave):
            return str(extra[clave])
    return None


def _fmt_args(args: Any) -> str:
    """Pinta los argumentos de una tool: (ciudad='Madrid')."""
    if isinstance(args, dict):
        inner = ", ".join(f"{k}={v!r}" for k, v in args.items())
        return f"({inner})"
    return f"({args})"


def _tool_field(tc: Any, name: str, default: Any = "") -> Any:
    """Lee un campo de tool_call tanto si viene como dict como si es objeto."""
    if isinstance(tc, dict):
        return tc.get(name, default)
    return getattr(tc, name, default)


def _tipo_mensaje(mensaje: Any) -> str:
    """Normaliza mensajes completos y chunks al tipo lógico de LangChain."""
    tipo = str(getattr(mensaje, "type", "") or "").lower()
    if tipo in {"ai", "aimessage", "aimessagechunk"}:
        return "ai"
    if tipo in {"human", "humanmessage", "humanmessagechunk"}:
        return "human"
    if tipo in {"tool", "toolmessage", "toolmessagechunk"}:
        return "tool"
    return tipo


def lineas_de_mensajes(mensajes: list[Any]) -> list[ChatLine]:
    """Convierte mensajes (un chunk o un turno) en líneas pintables."""
    lineas: list[ChatLine] = []
    for m in mensajes:
        tipo = _tipo_mensaje(m)
        if tipo == "human":
            texto = _texto(getattr(m, "content", ""))
            if texto:
                lineas.append(ChatLine("human", texto, _key("human")))
        elif tipo == "ai":
            # Orden de clase: primero el pensar, luego las tools, luego el texto.
            razon = _razonamiento(m)
            if razon:
                lineas.append(ChatLine("thinking", razon, _key("thinking")))
            for tc in getattr(m, "tool_calls", None) or []:
                nombre = _tool_field(tc, "name", "?")
                args = _tool_field(tc, "args", {})
                lineas.append(ChatLine("tool", f"{nombre}{_fmt_args(args)}", _key("tool")))
            texto = _texto(getattr(m, "content", ""))
            if texto:
                lineas.append(ChatLine("bot", texto, _key("bot")))
        elif tipo == "tool":
            # ToolMessage: resultado que ToolNode mete en el historial.
            nombre = getattr(m, "name", None) or "tool"
            contenido = _texto(getattr(m, "content", ""))
            lineas.append(ChatLine("dato", f"{nombre}: {contenido}", _key("dato")))
    return lineas


def lineas_del_turno(mensajes: list[Any]) -> list[ChatLine]:
    """Líneas del último turno (después del último human). No incluye al humano."""
    nuevos: list[Any] = []
    # Recorremos al revés hasta el último HumanMessage: eso marca el corte del turno.
    for m in reversed(mensajes):
        if getattr(m, "type", None) == "human":
            break
        nuevos.append(m)
    # reversed(nuevos) recupera el orden cronológico (pensar → tool → dato → bot).
    return lineas_de_mensajes(list(reversed(nuevos)))


def _mensajes_de_payload(payload: Any) -> list[Any]:
    """Un chunk de stream puede ser {messages: [...]} o ya una lista."""
    if isinstance(payload, dict):
        return list(payload.get("messages") or [])
    if isinstance(payload, list):
        return list(payload)
    return []


def _nombres_tools(mensajes: list[Any]) -> list[str]:
    """Nombres de tools en un chunk: las que el LLM pidió o las que ToolNode ejecutó."""
    nombres: list[str] = []
    for m in mensajes:
        tipo = _tipo_mensaje(m)
        if tipo == "ai":
            for tc in getattr(m, "tool_calls", None) or []:
                nombre = _tool_field(tc, "name", "")
                if nombre:
                    nombres.append(str(nombre))
        elif tipo == "tool":
            nombre = getattr(m, "name", None)
            if nombre:
                nombres.append(str(nombre))
    # Deduplicamos conservando el orden (buscar_clima, tendencia_ropa).
    vistos: list[str] = []
    for n in nombres:
        if n not in vistos:
            vistos.append(n)
    return vistos


def _linea_juez(payload: dict[str, Any]) -> ChatLine:
    """Veredicto del juez: 'web · query' o 'sin web'. No es un mensaje del chat."""
    # El nodo juez no escribe messages: el update trae usar_web / query_web.
    query = str(payload.get("query_web") or "").strip()
    if payload.get("usar_web"):
        texto = f"web · {query}" if query else "web"
    else:
        texto = "sin web"
    return ChatLine("juez", texto, _key("juez"))


def _linea_validador(payload: dict[str, Any]) -> ChatLine:
    """Veredicto del validador: 'ok · …' o 'reintenta · …'."""
    motivo = str(payload.get("motivo_validador") or "").strip()
    cabeza = "ok" if payload.get("ok") else "reintenta"
    texto = f"{cabeza} · {motivo}" if motivo else cabeza
    return ChatLine("validador", texto, _key("validador"))


def lineas_de_update(update: dict[str, Any]) -> list[ChatLine]:
    """Extrae líneas de un chunk `graph.stream(..., stream_mode='updates')`."""
    # El update es {nombre_nodo: payload}. Recorremos todos los payloads.
    lineas: list[ChatLine] = []
    for clave, payload in update.items():
        # juez / validador no meten ToolMessage: pintamos su State como traza.
        if clave == "juez" and isinstance(payload, dict) and "usar_web" in payload:
            lineas.append(_linea_juez(payload))
            continue
        if clave == "validador" and isinstance(payload, dict) and "ok" in payload:
            lineas.append(_linea_validador(payload))
            continue
        lineas.extend(lineas_de_mensajes(_mensajes_de_payload(payload)))
    return lineas


def estado_de_update(update: dict[str, Any]) -> tuple[str | None, list[str]]:
    """Nodo activo y nombres de tools de un chunk de stream updates."""
    nodo: str | None = None
    nombres: list[str] = []
    for clave, payload in update.items():
        # Nodos del grafo de 04: juez, chatbot, tools, validador.
        if clave in {"juez", "chatbot", "tools", "validador"}:
            nodo = clave
        nombres.extend(_nombres_tools(_mensajes_de_payload(payload)))
    # Mismo dedup que _nombres_tools por si el chunk trae varias claves.
    vistos: list[str] = []
    for n in nombres:
        if n not in vistos:
            vistos.append(n)
    return nodo, vistos
