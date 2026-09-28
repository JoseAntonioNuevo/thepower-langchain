"""TUI OpenTUI del chatbot 04. El grafo se pasa desde fuera."""

from __future__ import annotations

# queue + thread: el grafo corre en segundo plano; la UI solo se toca en el hilo principal.
import queue
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# HumanMessage: lo que metemos en graph.stream() al enviar un turno.
from langchain_core.messages import HumanMessage

# OpenTUI: Box/Text/For para pintar; Signal para estado reactivo; hooks de teclado.
from opentui import (
    Box,
    For,
    ScrollBox,
    ScrollContent,
    Signal,
    Text,
    TextareaRenderable,
    hooks,
    on_cleanup,
    render,
    use_cursor,
    use_cursor_style,
    use_renderer,
)
from opentui.animation import create_timeline, engine
from opentui.components.markdown import MarkdownRenderable
from opentui.input.keymapping import KeyBinding

# Parser puro: mensajes LangGraph → filas + (nodo, nombres de tools).
from ui.chat_lines import ChatLine, estado_de_update, lineas_de_update
from ui.chat_input import HistorialComposer, indice_cursor

# Primera fila del chat: una pregunta que recorre juez → Tavily → validador.
HINT = "Prueba: ¿Qué temperatura hace ahora en Madrid?"
# Palabras que cierran la TUI al enviarlas (además de Esc).
SALIR = {"salir", "exit", "q"}

# Paleta Tokyo Night: no cambiar los hex; la TUI los reutiliza en chat y grafo.
BG = "#16161e"
SURFACE = "#1a1b26"
BORDER = "#414868"
DIM = "#565f89"
BRIGHT = "#c0caf5"
USER = "#7aa2f7"
THINK = "#9d7cd8"
TOOL = "#e0af68"
DATO = "#9ece6a"
BOT = "#c0caf5"
ERROR = "#f7768e"
ACTIVE = "#7aa2f7"
IDLE_NODE = "#565f89"
ESPINA = "#a9b1d6"
THINK_BG = "#1f1a2e"
TOOL_BG = "#2a2416"
VALID_BG = "#1a2233"
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧"
_PREVIEW = 18

# Columnas del panel grafo (interior = 28): espina central (START→LLM→tools→END)
# y un segundo carril a su derecha para el retorno tools→LLM (el bucle).
_ANCHO_NODO = 22
_COL_NODO = 3
_COL_ESPINA = _COL_NODO + _ANCHO_NODO // 2
_COL_VUELVE = _COL_ESPINA + 5
_COL_INICIO = 11  # "○ START" centrado sobre la espina
_COL_FIN = 12  # "○ END" centrado sobre la espina

# Ids de tool → etiqueta corta en el grafo y el header (el chat sigue con el id).
_NOMBRES_TOOLS = {
    "fecha_hoy": "fecha",
    "buscar_clima": "clima",
    "tendencia_ropa": "tendencia",
    "buscar_web": "búsqueda",
}

# kind → (etiqueta en pantalla, color, estilo de layout).
# human/bot = globo de chat; meta = traza del grafo, sin caja.
_KIND = {
    "human": ("tú", USER, "human"),
    "thinking": ("pensar", THINK, "meta"),
    "tool": ("tool", TOOL, "meta"),
    "dato": ("dato", DATO, "meta"),
    "bot": ("bot", BOT, "bot"),
    "error": ("error", ERROR, "bot"),
    "hint": ("hint", DIM, "hint"),
    "juez": ("juez", THINK, "meta"),
    "validador": ("validador", ACTIVE, "meta"),
}


def _envolver_markdown(nodo: Any) -> None:
    """MarkdownTextBlock nace con wrap_mode=none; sin wrap el globo recorta."""
    if hasattr(nodo, "wrap_mode"):
        nodo.wrap_mode = "word"
    for hijo in getattr(nodo, "get_children", lambda: ())():
        _envolver_markdown(hijo)


def _vista_dato(texto: str) -> tuple[str, str]:
    """Separa 'nombre: cuerpo' y deja un resumen (sin URLs ni snippets sucios)."""
    if ": " in texto:
        nombre, resto = texto.split(": ", 1)
    else:
        nombre, resto = "tool", texto
    lineas = [ln.strip() for ln in resto.splitlines() if ln.strip()]
    resumen: list[str] = []
    fuentes: list[str] = []
    for ln in lineas:
        if ln.startswith(("http://", "https://")):
            continue
        if ln.startswith("- "):
            titulo = ln[2:].split(" — ", 1)[0].strip()
            if titulo:
                fuentes.append(titulo)
            continue
        resumen.append(ln)
    partes: list[str] = []
    if resumen:
        partes.append(_recortar(" ".join(resumen), 160))
    partes.extend(f"· {f}" for f in fuentes[:2])
    return nombre, "\n".join(partes) if partes else resto.strip()


def _cuerpo_globo(line: ChatLine, color: str, *, lado: str) -> Text | MarkdownRenderable:
    """El LLM entra como markdown; tú y error se quedan en texto plano."""
    if lado == "bot" and line.kind == "bot":
        cuerpo = MarkdownRenderable(
            content=line.text,
            conceal=True,
            fg=color,
            background_color=SURFACE,
            flex_shrink=0,
            align_self="stretch",
        )
        _envolver_markdown(cuerpo)
        return cuerpo
    return Text(line.text, fg=color, bg=SURFACE, wrap_mode="word")


def _globo(line: ChatLine, etiqueta: str, color: str, *, lado: str) -> Box:
    """Caja de diálogo (tú a la derecha, bot/error a la izquierda)."""
    dialogo = Box(
        _cuerpo_globo(line, color, lado=lado),
        title=etiqueta,
        title_alignment="right" if lado == "human" else "left",
        border=True,
        border_style="round",
        border_color=color,
        background_color=SURFACE,
        padding_left=2,
        padding_right=2,
        padding_top=1,
        padding_bottom=1,
        flex_shrink=0,
        # tú: globo estrecho a la derecha. bot: usa el ancho del chat y envuelve.
        max_width=42 if lado == "human" else None,
        align_self="stretch" if lado != "human" else None,
    )
    if lado == "human":
        return Box(
            dialogo,
            key=line.key,
            background_color=SURFACE,
            margin_left=10,
            margin_right=2,
            margin_top=1,
            flex_shrink=0,
            align_self="stretch",
            align_items="flex-end",
        )
    return Box(
        dialogo,
        key=line.key,
        background_color=SURFACE,
        margin_left=2,
        margin_right=3,
        margin_top=1,
        margin_bottom=1,
        flex_shrink=0,
        align_self="stretch",
        align_items="stretch",
    )


def _traza(line: ChatLine, etiqueta: str, color: str) -> Box:
    """pensar / tool: riel con sangría, para no confundirlo con la respuesta."""
    return Box(
        Text("│", fg=color, bg=SURFACE),
        Box(
            Text(etiqueta, fg=color, bg=SURFACE),
            Text(line.text, fg=color, bg=SURFACE, wrap_mode="word", italic=line.kind == "thinking"),
            flex_direction="column",
            flex_grow=1,
            flex_shrink=1,
            gap=0,
        ),
        key=line.key,
        background_color=SURFACE,
        padding_left=3,
        padding_right=3,
        padding_top=1 if line.kind == "thinking" else 0,
        flex_direction="row",
        gap=1,
        flex_shrink=0,
        align_self="stretch",
    )


def _tarjeta_dato(line: ChatLine, etiqueta: str, color: str) -> Box:
    """Resultado de tool: tarjeta corta, no el volcado crudo con URLs."""
    nombre, cuerpo = _vista_dato(line.text)
    return Box(
        Box(
            Text(cuerpo, fg=color, bg=SURFACE, wrap_mode="word"),
            title=f"{etiqueta} · {nombre}",
            title_alignment="left",
            border=True,
            border_style="round",
            border_color=color,
            background_color=SURFACE,
            padding_left=2,
            padding_right=2,
            padding_top=1,
            padding_bottom=1,
            flex_shrink=0,
            align_self="stretch",
        ),
        key=line.key,
        background_color=SURFACE,
        margin_left=2,
        margin_right=3,
        margin_top=1,
        flex_shrink=0,
        align_self="stretch",
    )


def _linea(line: ChatLine) -> Box:
    """Una fila del transcript: globo de chat o traza del grafo."""
    etiqueta, color, estilo = _KIND[line.kind]
    if estilo == "hint":
        return Box(
            Text(line.text, fg=color, bg=SURFACE, wrap_mode="word"),
            key=line.key,
            background_color=SURFACE,
            padding_left=3,
            padding_right=3,
            padding_top=1,
            flex_shrink=0,
            align_self="stretch",
        )
    if estilo == "human":
        return _globo(line, etiqueta, color, lado="human")
    if estilo == "meta":
        if line.kind == "dato":
            return _tarjeta_dato(line, etiqueta, color)
        return _traza(line, etiqueta, color)
    return _globo(line, etiqueta, color, lado="bot")


def _nombre_amigable(nombre: str) -> str:
    """Id de tool → etiqueta del grafo. Si no está en el mapa, se deja el id."""
    return _NOMBRES_TOOLS.get(nombre, nombre)


def _nombre_modelo(slug: str) -> str:
    """openai/gpt-6-luna → Gpt 6 Luna. Cabe en el nodo de 22 columnas."""
    cola = (slug or "").rsplit("/", 1)[-1]
    if cola.endswith("-it"):
        cola = cola[:-3]
    partes: list[str] = []
    for trozo in cola.replace("_", "-").split("-"):
        if not trozo:
            continue
        if trozo[-1] in "bBmM" and trozo[:-1].isdigit():
            partes.append(trozo[:-1] + trozo[-1].upper())
        elif trozo.isdigit():
            partes.append(trozo)
        else:
            partes.append(trozo[:1].upper() + trozo[1:])
    return " ".join(partes) or slug


def _etiquetas_tools(tools: list[str]) -> list[str]:
    return [_nombre_amigable(n) for n in tools]


def _leyenda(phase: str | None, tools: list[str] | None = None) -> str:
    """Chip de la sidebar: dónde está el turno, no el id crudo de la tool."""
    pedidos = _etiquetas_tools(tools or [])
    # Fases nuevas del ciclo 04: el chip sigue al nodo, no al id de la tool.
    if phase == "judging":
        return "el juez decide"
    if phase == "retrying":
        return "reintenta"
    if phase == "thinking":
        return "en el modelo"
    if phase == "tools":
        if len(pedidos) == 1:
            return "pide tool · " + pedidos[0]
        if pedidos:
            return f"pide tool · {len(pedidos)}"
        return "pide tool"
    if phase == "writing":
        return "el modelo responde"
    if phase == "validating":
        return "valida respuesta"
    return "reposo"


def _leyenda_con_tiempo(phase: Signal, active_tools: Signal, segundos: Signal) -> str:
    """Chip de la sidebar + cronómetro del turno cuando el grafo trabaja."""
    base = _leyenda(phase(), active_tools())
    if phase() in {None, "idle"} or segundos() <= 0:
        return base
    return f"{base} · {segundos()}s"


def _recortar(texto: str, ancho: int = _PREVIEW) -> str:
    limpio = " ".join((texto or "").split())
    if len(limpio) <= ancho:
        return limpio
    return limpio[: ancho - 1] + "…"


def _posicion_cursor_en_textarea(textarea: Any) -> tuple[int, int]:
    """Columna y fila visuales (0-based) del caret dentro del widget."""
    try:
        visual = textarea._editor_view.get_visual_cursor()
        return int(visual.visual_col), int(visual.visual_row)
    except Exception:
        texto = getattr(textarea, "plain_text", "") or ""
        offset = int(getattr(textarea, "cursor_offset", 0) or 0)
        linea, columna = indice_cursor(texto, offset)
        return max(0, columna - 1), max(0, linea - 1)


def _mostrar_cursor_textarea(textarea: Any, *, encendido: bool) -> None:
    """Pide el cursor parpadeante del terminal en el punto de inserción.

    TextareaRenderable pinta el texto pero no llama a use_cursor; sin esto
    no se ve dónde se escribe. El blink lo hace el renderer (~530 ms).
    """
    if not encendido or not getattr(textarea, "_focused", False):
        return
    x = int(getattr(textarea, "_x", 0) or 0)
    y = int(getattr(textarea, "_y", 0) or 0)
    w = int(getattr(textarea, "_layout_width", 0) or 0)
    h = int(getattr(textarea, "_layout_height", 0) or 1)
    col, row = _posicion_cursor_en_textarea(textarea)
    if w > 0:
        col = max(0, min(col, w - 1))
    if h > 0:
        row = max(0, min(row, h - 1))
    use_cursor(x + col, y + row)
    use_cursor_style("block", USER)


def _frame_spinner(t: float) -> str:
    """Glifo del spinner a partir de un tiempo o índice."""
    return _SPINNER[int(t) % len(_SPINNER)]


def _color_espina(viva: bool, pulso: float, acento: str) -> str:
    """Espina idle: gris claro. Viva: acento o SURFACE (parpadeo duro)."""
    if not viva:
        return ESPINA
    return acento if pulso > 0.5 else SURFACE


@dataclass
class GrafoEstado:
    """Estado puro del sidebar: lo actualiza aplicar_evento, no OpenTUI."""

    phase: str = "idle"
    tools: list[str] = field(default_factory=list)
    tool_detalle: list[str] = field(default_factory=list)
    llm_detalle: str = ""
    # Preview del veredicto en el nodo juez / validador (no son tokens del LLM).
    juez_detalle: str = ""
    validador_detalle: str = ""
    hubo_tools: bool = False
    # True tras la primera pasada por validador: el siguiente juez es un reintento.
    hubo_validacion: bool = False


def _texto_mensaje(mensaje: Any) -> str:
    content = getattr(mensaje, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes: list[str] = []
        for block in content:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict) and block.get("type") in {None, "text"}:
                t = block.get("text") or block.get("content")
                if t:
                    partes.append(str(t))
        return "".join(partes)
    return ""


def _unicos(items: list[str]) -> list[str]:
    """Quita duplicados conservando el orden (misma tool en calls + chunks)."""
    vistos: list[str] = []
    for item in items:
        if item not in vistos:
            vistos.append(item)
    return vistos


def _tools_de_mensaje(mensaje: Any) -> tuple[list[str], list[str]]:
    """Nombres crudos y etiquetas 'clima · Madrid' de un AIMessage / chunk."""
    # Un mensaje completo trae tool_calls y a veces los chunks: no sumar los dos.
    llamadas = list(getattr(mensaje, "tool_calls", None) or [])
    if not llamadas:
        llamadas = list(getattr(mensaje, "tool_call_chunks", None) or [])
    nombres: list[str] = []
    detalles: list[str] = []
    for tc in llamadas:
        if isinstance(tc, dict):
            nombre = tc.get("name") or ""
            args = tc.get("args") or {}
        else:
            nombre = getattr(tc, "name", "") or ""
            args = getattr(tc, "args", {}) or {}
        if not nombre or str(nombre) in nombres:
            continue
        nombres.append(str(nombre))
        extra = ""
        if isinstance(args, dict) and args:
            # 6 chars de argumento: "▸ tendencia · Madrid" cabe justo en el nodo.
            extra = " · " + _recortar(str(next(iter(args.values()))), 6)
        detalles.append(_nombre_amigable(str(nombre)) + extra)
    return nombres, detalles


def _payload_task(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    if "name" in data:
        return data
    inner = data.get("data")
    if isinstance(inner, dict) and "name" in inner:
        return inner
    return None


def aplicar_evento(estado: GrafoEstado, mode: str, data: Any) -> GrafoEstado:
    """Reducer puro: un chunk de stream → nuevo estado del grafo."""
    nuevo = GrafoEstado(
        phase=estado.phase,
        tools=list(estado.tools),
        tool_detalle=list(estado.tool_detalle),
        llm_detalle=estado.llm_detalle,
        juez_detalle=estado.juez_detalle,
        validador_detalle=estado.validador_detalle,
        hubo_tools=estado.hubo_tools,
        hubo_validacion=estado.hubo_validacion,
    )
    if mode == "tasks":
        payload = _payload_task(data)
        if not payload:
            return nuevo
        nombre = str(payload.get("name") or "")
        es_inicio = "input" in payload and "result" not in payload
        # tasks: LangGraph avisa al ENTRAR en un nodo. Iluminamos antes del update.
        if nombre == "juez" and es_inicio:
            nuevo.phase = "retrying" if nuevo.hubo_validacion else "judging"
        elif nombre == "validador" and es_inicio:
            nuevo.phase = "validating"
            nuevo.hubo_validacion = True
        elif nombre == "chatbot" and es_inicio:
            nuevo.phase = "writing" if nuevo.hubo_tools else "thinking"
            if not nuevo.hubo_tools:
                nuevo.llm_detalle = ""
        elif nombre == "tools" and (es_inicio or "result" in payload):
            nuevo.phase = "tools"
            nuevo.hubo_tools = True
        return nuevo
    if mode == "messages":
        if isinstance(data, tuple) and len(data) == 2:
            chunk, meta = data
        else:
            chunk, meta = data, {}
        nodo = ""
        if isinstance(meta, dict):
            nodo = str(meta.get("langgraph_node") or meta.get("node") or "")
        if nodo and nodo != "chatbot":
            return nuevo
        nombres, detalles = _tools_de_mensaje(chunk)
        if nombres:
            nuevo.phase = "tools"
            nuevo.tools = _unicos(nombres)
            nuevo.tool_detalle = _unicos(detalles)
            nuevo.hubo_tools = True
            return nuevo
        texto = _texto_mensaje(chunk)
        if texto:
            nuevo.llm_detalle = (nuevo.llm_detalle + texto)[-80:]
            if nuevo.hubo_tools:
                nuevo.phase = "writing"
            elif nuevo.phase in {"idle", "thinking"}:
                nuevo.phase = "thinking"
        return nuevo
    if mode == "updates" and isinstance(data, dict):
        nodo, tools = estado_de_update(data)
        # updates: el nodo acabó y el payload es el dict que devolvió (State).
        if nodo == "juez":
            payload = data.get("juez") if isinstance(data.get("juez"), dict) else {}
            nuevo.phase = "retrying" if nuevo.hubo_validacion else "judging"
            query = str(payload.get("query_web") or "").strip()
            if payload.get("usar_web"):
                nuevo.juez_detalle = f"web · {query}" if query else "web"
            elif "usar_web" in payload:
                nuevo.juez_detalle = "sin web"
        elif nodo == "validador":
            payload = data.get("validador") if isinstance(data.get("validador"), dict) else {}
            nuevo.phase = "validating"
            nuevo.hubo_validacion = True
            motivo = str(payload.get("motivo_validador") or "").strip()
            cabeza = "ok" if payload.get("ok") else "reintenta"
            nuevo.validador_detalle = f"{cabeza} · {motivo}" if motivo else cabeza
        elif nodo == "chatbot" and tools:
            nuevo.phase = "tools"
            nuevo.tools = _unicos(tools)
            nuevo.hubo_tools = True
            if not nuevo.tool_detalle:
                nuevo.tool_detalle = _etiquetas_tools(nuevo.tools)
        elif nodo == "chatbot":
            nuevo.phase = "writing" if nuevo.hubo_tools else "thinking"
        elif nodo == "tools":
            nuevo.phase = "tools"
            nuevo.hubo_tools = True
            if tools:
                nuevo.tools = _unicos(tools)
        return nuevo
    return nuevo


def _cuerpo_tools(
    tools: list[str],
    *,
    aqui: bool = False,
    detalle: list[str] | None = None,
    spinner: str = "",
) -> str:
    """Interior del nodo tools: etiquetas amigables, o 'en espera'."""
    lineas: list[str] = []
    if aqui:
        lineas.append(f"{spinner} aquí" if spinner else "● aquí")
    filas = _unicos(detalle if detalle else _etiquetas_tools(tools))
    if not filas:
        lineas.append("en espera")
        return "\n".join(lineas)
    lineas.extend(filas)
    return "\n".join(lineas)


def _cuerpo_llm(
    phase: str,
    corto: str,
    *,
    detalle: str = "",
    spinner: str = "",
) -> str:
    """Interior del nodo del modelo: nombre, generando/responde + preview."""
    extra = _recortar(detalle)
    if phase == "thinking":
        cabeza = f"{spinner} generando" if spinner else "● generando"
        return f"{cabeza}\n{extra}" if extra else cabeza
    if phase == "writing":
        cabeza = f"{spinner} responde" if spinner else "● responde"
        return f"{cabeza}\n{extra}" if extra else cabeza
    return corto


def _cuerpo_juez(
    phase: str,
    *,
    detalle: str = "",
    spinner: str = "",
) -> str:
    """Interior del nodo juez: decide / reintenta + veredicto corto."""
    extra = _recortar(detalle)
    if phase == "judging":
        cabeza = f"{spinner} decide" if spinner else "● decide"
        return f"{cabeza}\n{extra}" if extra else cabeza
    if phase == "retrying":
        cabeza = f"{spinner} reintenta" if spinner else "● reintenta"
        return f"{cabeza}\n{extra}" if extra else cabeza
    return extra or "¿buscar web?"


def _cuerpo_validador(
    phase: str,
    *,
    detalle: str = "",
    spinner: str = "",
) -> str:
    """Interior del nodo validador: chequeo + ok/reintenta."""
    extra = _recortar(detalle)
    if phase == "validating":
        cabeza = f"{spinner} valida" if spinner else "● valida"
        return f"{cabeza}\n{extra}" if extra else cabeza
    return extra or "¿respuesta ok?"


def _fase_en(phase: Signal, *valores: str) -> Signal:
    """True cuando phase está en uno de los valores."""
    return phase.map(lambda p, _v=valores: p in _v)


def _fila(*partes: tuple[int, int, Any]) -> Box:
    """Fila del grafo con piezas en columnas fijas: (columna, ancho, elemento)."""
    hijos: list[Any] = []
    col = 0
    for destino, ancho, pieza in sorted(partes, key=lambda p: p[0]):
        if destino > col:
            hijos.append(Box(width=destino - col, flex_shrink=0))
        hijos.append(pieza)
        col = destino + ancho
    return Box(*hijos, flex_direction="row", flex_shrink=0, align_self="stretch")


def _riel(glifo: str, color: Signal | str) -> Text:
    """Un glifo de carril (┃, ▲…); sin wrap para no romper la columna."""
    return Text(glifo, fg=color, bg=SURFACE, wrap_mode="none")


def _carriles(centro: Signal, der: Signal) -> Box:
    """Fila de dos carriles: bajada (pide) ┃ y subida (vuelve) ┃."""
    return _fila(
        (_COL_ESPINA, 1, _riel("┃", centro)),
        (_COL_VUELVE, 1, _riel("┃", der)),
    )


def _ancla(nombre: str) -> Text:
    """Terminales START / END, como en el mermaid de LangGraph."""
    return Text(f"○ {nombre}", fg=ESPINA, bg=SURFACE, wrap_mode="none")


def _nodo_grafo(
    titulo: str,
    encendido: Signal,
    *children: Any,
    acento: str,
    fondo: str,
) -> Box:
    """Caja redonda. Borde y fondo se tiñen si el nodo está activo."""
    return Box(
        *children,
        title=titulo,
        title_alignment="center",
        border=True,
        border_style="round",
        border_color=encendido.map(lambda v, _c=acento: _c if v else BORDER),
        background_color=encendido.map(lambda v, _f=fondo: _f if v else SURFACE),
        padding_left=1,
        padding_right=1,
        width=_ANCHO_NODO,
        flex_shrink=0,
        align_items="center",
        justify_content="center",
    )


def _color_tramo(
    phase: Signal,
    pulso: Signal,
    valor: str,
    acento: str,
) -> Signal:
    """Color de una espina o etiqueta: parpadeo duro si ese tramo está vivo."""
    return phase.map(
        lambda p, _v=valor, _c=acento, _pulso=pulso: _color_espina(p == _v, _pulso(), _c)
    )


def _panel_grafo(
    phase: Signal,
    active_tools: Signal,
    *,
    modelo: str,
    pulso: Signal,
    fade: Signal,
    llm_detalle: Signal,
    tool_detalle: Signal,
    segundos: Signal,
    juez_detalle: Signal,
    validador_detalle: Signal,
) -> Box:
    """Sidebar: START → juez → LLM ⇄ tools → validador → END (reintenta al juez).

    El rail derecho (▲ vuelve / ▲ reintenta) es el bucle que los alumnos
    deben ver: tools→LLM y validador→juez. El izquierdo baja hacia END.
    """
    corto = _nombre_modelo(modelo)
    juez_on = _fase_en(phase, "judging", "retrying")
    llm_on = _fase_en(phase, "thinking", "writing")
    tools_on = _fase_en(phase, "tools")
    valid_on = _fase_en(phase, "validating")
    ocupado = phase.map(lambda p: p not in {None, "idle"})
    arco_juez = phase.map(
        lambda p, _pulso=pulso: _color_espina(p in {"judging", "retrying"}, _pulso(), THINK)
    )
    arco_llm = _color_tramo(phase, pulso, "thinking", THINK)
    arco_pide = _color_tramo(phase, pulso, "tools", TOOL)
    arco_vuelve = _color_tramo(phase, pulso, "writing", THINK)
    arco_valida = _color_tramo(phase, pulso, "validating", ACTIVE)
    arco_ok = _color_tramo(phase, pulso, "validating", ACTIVE)
    arco_reintenta = phase.map(
        lambda p, _pulso=pulso: _color_espina(p == "retrying", _pulso(), THINK)
    )

    def _texto_juez() -> str:
        return _cuerpo_juez(
            phase(),
            detalle=juez_detalle(),
            spinner=_frame_spinner(pulso() * 8) if phase() in {"judging", "retrying"} else "",
        )

    def _texto_llm() -> str:
        return _cuerpo_llm(
            phase(),
            corto,
            detalle=llm_detalle(),
            spinner=_frame_spinner(pulso() * 8) if phase() in {"thinking", "writing"} else "",
        )

    def _texto_tools() -> str:
        return _cuerpo_tools(
            active_tools(),
            aqui=phase() == "tools",
            detalle=tool_detalle() or None,
            spinner=_frame_spinner(pulso() * 8) if phase() == "tools" else "",
        )

    def _texto_validador() -> str:
        return _cuerpo_validador(
            phase(),
            detalle=validador_detalle(),
            spinner=_frame_spinner(pulso() * 8) if phase() == "validating" else "",
        )

    nodo_juez = _nodo_grafo(
        "juez",
        juez_on,
        Text(
            _texto_juez,
            fg=juez_on.map(lambda v: THINK if v else IDLE_NODE),
            bg=juez_on.map(lambda v: THINK_BG if v else SURFACE),
            bold=juez_on,
        ),
        acento=THINK,
        fondo=THINK_BG,
    )
    nodo_llm = _nodo_grafo(
        "LLM",
        llm_on,
        Text(
            _texto_llm,
            fg=llm_on.map(lambda v: THINK if v else IDLE_NODE),
            bg=llm_on.map(lambda v: THINK_BG if v else SURFACE),
            bold=llm_on,
        ),
        acento=THINK,
        fondo=THINK_BG,
    )
    nodo_tools = _nodo_grafo(
        "tools",
        tools_on,
        Text(
            _texto_tools,
            fg=tools_on.map(lambda v: TOOL if v else IDLE_NODE),
            bg=tools_on.map(lambda v: TOOL_BG if v else SURFACE),
            bold=tools_on,
        ),
        acento=TOOL,
        fondo=TOOL_BG,
    )
    nodo_validador = _nodo_grafo(
        "validador",
        valid_on,
        Text(
            _texto_validador,
            fg=valid_on.map(lambda v: ACTIVE if v else IDLE_NODE),
            bg=valid_on.map(lambda v: VALID_BG if v else SURFACE),
            bold=valid_on,
        ),
        acento=ACTIVE,
        fondo=VALID_BG,
    )

    return Box(
        Box(
            Text(
                lambda: _leyenda_con_tiempo(phase, active_tools, segundos),
                fg=ocupado.map(lambda v: ACTIVE if v else DIM),
                bg=SURFACE,
                bold=ocupado,
                wrap_mode="none",
            ),
            align_self="stretch",
            height=1,
            padding_left=1,
        ),
        _fila((_COL_INICIO, 7, _ancla("START"))),
        _fila((_COL_ESPINA, 1, _riel("┃", arco_juez))),
        _fila((_COL_NODO, _ANCHO_NODO, nodo_juez)),
        _fila((_COL_ESPINA, 1, _riel("┃", arco_llm))),
        _fila((_COL_NODO, _ANCHO_NODO, nodo_llm)),
        _carriles(arco_pide, arco_vuelve),
        _fila(
            (_COL_ESPINA - 10, 11, Text(
                "pide tool ▼",
                fg=arco_pide,
                bg=SURFACE,
                bold=phase.map(lambda p, _pulso=pulso: p == "tools" and _pulso() > 0.5),
                wrap_mode="none",
            )),
            (_COL_VUELVE, 8, Text(
                "▲ vuelve",
                fg=arco_vuelve,
                bg=SURFACE,
                bold=phase.map(lambda p, _pulso=pulso: p == "writing" and _pulso() > 0.5),
                wrap_mode="none",
            )),
        ),
        _carriles(arco_pide, arco_vuelve),
        _fila((_COL_NODO, _ANCHO_NODO, nodo_tools)),
        _fila((_COL_ESPINA, 1, _riel("┃", arco_valida))),
        _fila((_COL_NODO, _ANCHO_NODO, nodo_validador)),
        _fila(
            (_COL_ESPINA - 4, 5, Text(
                "ok ▼",
                fg=arco_ok,
                bg=SURFACE,
                wrap_mode="none",
            )),
            (_COL_VUELVE, 11, Text(
                "▲ reintenta",
                fg=arco_reintenta,
                bg=SURFACE,
                bold=phase.map(lambda p, _pulso=pulso: p == "retrying" and _pulso() > 0.5),
                wrap_mode="none",
            )),
        ),
        _fila((_COL_FIN, 5, _ancla("END"))),
        width=32,
        flex_shrink=0,
        background_color=SURFACE,
        border=True,
        border_style="round",
        border_color=BORDER,
        title="grafo",
        title_alignment="left",
        padding_x=1,
        padding_y=0,
        gap=0,
        overflow="hidden",
        opacity=fade,
    )


def _ms(delta: float) -> float:
    """El renderer pasa segundos (~0.016); Timeline espera milisegundos."""
    return delta if delta > 5 else delta * 1000.0


def _arrancar_efectos(
    phase: Signal,
    pulso: Signal,
    fade: Signal,
    *,
    animar_fade: bool,
    segundos: Signal,
) -> None:
    """Fade-in del panel al montar + pulso de los carriles y cronómetro del turno."""
    renderer = use_renderer()
    if renderer is None:
        fade.set(1.0)
        return

    fade_obj = type("_Fade", (), {"v": 0.0})()
    if animar_fade:
        fade.set(0.0)
        fade_tl = create_timeline(duration=700, loop=False, autoplay=True)
        fade_tl.add(
            fade_obj,
            {
                "v": 1.0,
                "duration": 700,
                "ease": "outQuad",
                "on_update": lambda anim: fade.set(float(anim.targets[0].v)),
            },
        )
    else:
        fade.set(1.0)

    pulso_obj = type("_Pulso", (), {"v": 0.0})()
    pulso_tl = create_timeline(duration=400, loop=True, autoplay=False)
    pulso_tl.add(
        pulso_obj,
        {
            "v": 1.0,
            "duration": 400,
            "ease": "linear",
            "alternate": True,
            "loop": True,
            "on_update": lambda anim: pulso.set(float(anim.targets[0].v)),
        },
    )

    reloj: dict[str, Any] = {"inicio": None, "ultimo": -1}

    def _tick(delta: float) -> None:
        engine.update(_ms(delta))
        ocupado = phase() not in {None, "idle"}
        if ocupado and not pulso_tl.is_playing:
            pulso_tl.play()
        elif not ocupado and pulso_tl.is_playing:
            pulso_tl.pause()
            pulso.set(0.0)
        if ocupado:
            if reloj["inicio"] is None:
                reloj["inicio"] = time.monotonic()
            actual = int(time.monotonic() - reloj["inicio"])
            if actual != reloj["ultimo"]:
                reloj["ultimo"] = actual
                segundos.set(actual)
        elif reloj["inicio"] is not None:
            reloj["inicio"] = None
            reloj["ultimo"] = -1
            segundos.set(0)

    renderer.set_frame_callback(_tick)


def _status_turno(phase: str | None, tools: list[str]) -> str:
    """Texto del header: 'LLM…', 'tool clima' o 'listo'."""
    if phase == "judging":
        return "juez…"
    if phase == "retrying":
        return "reintenta…"
    if phase == "validating":
        return "valida…"
    if phase == "writing":
        return "responde…"
    if tools:
        return "tool " + ", ".join(_etiquetas_tools(tools))
    if phase == "tools":
        return "tool…"
    if phase == "thinking":
        return "LLM…"
    return "listo"


def build_app(
    *,
    modelo: str,
    thread_id: str,
    lines: Signal,
    busy: Signal,
    active_node: Signal,
    active_tools: Signal,
    status: Signal,
    draft: Signal,
    on_submit: Callable[[str], None],
    on_quit: Callable[[], None],
    phase: Signal | None = None,
    pulso: Signal | None = None,
    grafo_opacity: Signal | None = None,
    llm_detalle: Signal | None = None,
    tool_detalle: Signal | None = None,
    juez_detalle: Signal | None = None,
    validador_detalle: Signal | None = None,
    turnos: Signal | None = None,
) -> Box:
    """Árbol visual: header + (chat | grafo) + composer + pie."""
    pulso_sig = pulso if pulso is not None else Signal(0.0, name="pulso")
    fade_sig = grafo_opacity if grafo_opacity is not None else Signal(0.0, name="grafo_opacity")
    detalle_llm = llm_detalle if llm_detalle is not None else Signal("", name="llm_detalle")
    detalle_tool = tool_detalle if tool_detalle is not None else Signal([], name="tool_detalle")
    detalle_juez = juez_detalle if juez_detalle is not None else Signal("", name="juez_detalle")
    detalle_validador = (
        validador_detalle if validador_detalle is not None else Signal("", name="validador_detalle")
    )
    turnos_sig = turnos if turnos is not None else Signal(0, name="turnos")
    segundos = Signal(0, name="segundos")
    composer_height = Signal(3, name="composer_height")
    historial = HistorialComposer()
    textarea: TextareaRenderable | None = None

    def _on_composer_change(texto: str) -> None:
        draft.set(texto)
        composer_height.set(min(6, max(3, 3 + texto.count("\n"))))

    def _submit_composer(texto: str) -> None:
        texto = texto.strip()
        if busy() or not texto or textarea is None:
            return
        historial.push(texto)
        textarea.set_text("")
        on_submit(texto)

    def _set_composer_text(texto: str) -> None:
        if textarea is None:
            return
        textarea.set_text(texto)
        # set_text() intentionally starts at (0, 0); history should be
        # immediately editable at its end, like a shell command line.
        textarea.cursor_offset = len(texto)

    def _on_composer_key(event: Any) -> None:
        nonlocal textarea
        if textarea is None:
            return
        if getattr(event, "event_type", "press") == "release":
            # Kitty keyboard mode reports press + release. TextareaRenderable
            # dispatches both through its edit keymap, so releases must not
            # insert a second copy of the same character.
            event.prevent_default()
            return
        key = event.key.lower()
        if key in {"escape", "esc"}:
            event.prevent_default()
            on_quit()
            return
        if key == "up" and not event.shift:
            # A single-line draft has no useful vertical cursor movement, so
            # Up starts history there. Multiline drafts keep native Up/Down.
            if historial.navegando or not textarea.plain_text or textarea.line_count == 1:
                event.prevent_default()
                _set_composer_text(historial.anterior(textarea.plain_text))
            return
        if key == "down" and not event.shift and historial.navegando:
            event.prevent_default()
            _set_composer_text(historial.siguiente())

    # wrap_mode="none": la estrategia NATIVE_TEXT de opentui 0.1.2 despinta
    # Texts hermanos en una misma fila; con "none" pinta el renderer python.
    header = Box(
        Text(" LangGraph", fg=USER, bg=BG, bold=True, wrap_mode="none"),
        Text(f"  {modelo}", fg=DIM, bg=BG, wrap_mode="none"),
        Text(f"  ·  hilo {thread_id}", fg=DIM, bg=BG, wrap_mode="none"),
        Text(
            lambda: f"  ·  {status()}",
            fg=busy.map(lambda b: ACTIVE if b else DATO),
            bg=BG,
            bold=True,
            wrap_mode="none",
        ),
        flex_direction="row",
        background_color=BG,
        height=1,
    )

    # For reconcilia por key: al añadir líneas no se reconstruye todo el chat.
    transcript = Box(
        ScrollBox(
            content=ScrollContent(
                For(_linea, each=lines, key_fn=lambda e: e.key, flex_shrink=0, flex_grow=0),
                gap=0,
                padding_x=3,
                padding_top=1,
                padding_bottom=2,
                align_self="stretch",
            ),
            # sticky bottom: al llegar un chunk nuevo seguimos viendo el final.
            sticky_scroll=True,
            sticky_start="bottom",
            scroll_y=True,
            flex_grow=1,
            background_color=SURFACE,
        ),
        # El borde vive en el Box padre: el scissor del ScrollBox cubre su
        # rectángulo entero y, con scroll, el contenido pisaría el borde.
        border=True,
        border_style="round",
        border_color=BORDER,
        title="chat",
        title_alignment="left",
        background_color=SURFACE,
        flex_grow=1,
    )

    # phase manda el ciclo; active_node se acepta por compatibilidad de tests.
    fase = phase if phase is not None else active_node.map(
        lambda n: {
            "juez": "judging",
            "chatbot": "thinking",
            "tools": "tools",
            "validador": "validating",
        }.get(n, "idle")
    )
    # Tests pasan grafo_opacity=1 (ya visible). En vivo arranca en 0 y hace fade-in.
    _arrancar_efectos(fase, pulso_sig, fade_sig, animar_fade=grafo_opacity is None, segundos=segundos)
    sidebar = _panel_grafo(
        fase,
        active_tools,
        modelo=modelo,
        pulso=pulso_sig,
        fade=fade_sig,
        llm_detalle=detalle_llm,
        tool_detalle=detalle_tool,
        segundos=segundos,
        juez_detalle=detalle_juez,
        validador_detalle=detalle_validador,
    )

    cuerpo = Box(
        transcript,
        sidebar,
        flex_direction="row",
        flex_grow=1,
        flex_shrink=1,
        flex_basis=0,
        gap=1,
        overflow="hidden",
    )

    # Composer real: foco, cursor, edición multilínea, selección, undo y paste.
    # TextareaRenderable es el widget pesado de OpenTUI; Textarea (la clase
    # simple) no implementa key_bindings ni el editor nativo en opentui 0.1.2.
    textarea = TextareaRenderable(
        initial_value="",
        placeholder="Escribe un mensaje…",
        wrap_mode="word",
        text_color=BRIGHT,
        placeholder_color=DIM,
        focused_background_color=SURFACE,
        focused_text_color=BRIGHT,
        cursor_color=USER,
        flex_grow=1,
        flex_shrink=1,
        align_self="stretch",
        on_submit=_submit_composer,
        on_key_down=_on_composer_key,
        on_content_change=_on_composer_change,
        key_bindings=[
            KeyBinding(name="return", action="submit"),
            KeyBinding(name="return", action="newline", shift=True),
        ],
    )
    # El árbol se construye antes del primer frame; el foco directo evita que
    # el renderer/test_render descarte un callback de montaje prematuro.
    textarea.focus()
    # TextareaRenderable 0.1.2 expone su handler en dos canales: el renderer
    # lo reenvía desde el árbol y focus() también lo registra en hooks. La
    # terminal atraviesa ambos canales, así que dejamos solo el del renderer.
    hooks.unregister_keyboard_handler(textarea._key_handler)

    # El render nativo no pide el caret del terminal. Lo pedimos después
    # de pintar para que parpadee en el punto de inserción.
    _pintar_textarea = type(textarea).render

    def _render_con_caret(buffer: Any, delta_time: float = 0) -> None:
        _pintar_textarea(textarea, buffer, delta_time)
        _mostrar_cursor_textarea(textarea, encendido=not busy.peek())

    textarea.render = _render_con_caret

    def _sync_placeholder() -> None:
        if textarea is not None:
            textarea.placeholder = (
                f"{_frame_spinner(pulso_sig.peek() * 8)} trabajando…"
                if busy.peek()
                else "Escribe un mensaje…"
            )

    _sync_placeholder()
    unsubscribe_busy = busy.subscribe(lambda _value: _sync_placeholder())
    unsubscribe_pulso = pulso_sig.subscribe(lambda _value: _sync_placeholder())
    on_cleanup(lambda: (unsubscribe_busy(), unsubscribe_pulso()))
    composer = Box(
        textarea,
        background_color=SURFACE,
        padding_left=2,
        padding_right=2,
        height=composer_height,
        min_height=3,
        max_height=6,
        flex_shrink=0,
        flex_grow=0,
        border=True,
        border_style="round",
        border_color=busy.map(lambda b: ACTIVE if b else BORDER),
        title="mensaje",
    )

    # Pie: pistas de teclado a la izquierda, contador de turnos a la derecha.
    pie_info = Box(
        Text(
            "enter envía · shift+enter nueva línea · ↑ historial · esc sale",
            fg=DIM,
            bg=BG,
            wrap_mode="none",
        ),
        Text(lambda: f"turno {turnos_sig()}", fg=DIM, bg=BG, wrap_mode="none"),
        flex_direction="row",
        justify_content="space-between",
        padding_left=1,
        padding_right=1,
        height=1,
        flex_shrink=0,
        background_color=BG,
    )

    return Box(
        header,
        cuerpo,
        Box(composer, pie_info, flex_direction="column", gap=0, flex_shrink=0),
        flex_direction="column",
        flex_grow=1,
        background_color=BG,
        padding=1,
        gap=1,
        overflow="hidden",
    )


class ChatController:
    """Puente grafo ↔ TUI: stream en un hilo, pintado en el hilo de OpenTUI."""

    def __init__(self, graph: Any, config: dict, modelo: str, thread_id: str):
        self.graph = graph
        # Misma config (thread_id) en cada stream → el checkpointer recuerda.
        self.config = config
        self.modelo = modelo
        self.thread_id = thread_id
        self.lines = Signal(
            [ChatLine("hint", HINT, "hint-0")],
            name="lines",
        )
        self.busy = Signal(False, name="busy")
        self.active_node = Signal(None, name="active_node")
        self.active_tools = Signal([], name="active_tools")
        self.phase = Signal("idle", name="phase")
        self.llm_detalle = Signal("", name="llm_detalle")
        self.tool_detalle = Signal([], name="tool_detalle")
        self.juez_detalle = Signal("", name="juez_detalle")
        self.validador_detalle = Signal("", name="validador_detalle")
        self.status = Signal("listo", name="status")
        self.draft = Signal("", name="draft")
        self.turnos = Signal(0, name="turnos")
        self._grafo = GrafoEstado()
        # El worker no toca Signals: deja lambdas aquí y drain() las ejecuta.
        self._pending: queue.Queue[Callable[[], None]] = queue.Queue()
        self._worker: threading.Thread | None = None

    def drain(self, _buffer: Any = None) -> None:
        """OpenTUI llama a esto como post_process(fn(buffer)); vaciamos la cola."""
        while True:
            try:
                fn = self._pending.get_nowait()
            except queue.Empty:
                return
            fn()

    def _ui(self, fn: Callable[[], None]) -> None:
        """Encola un cambio de UI desde el hilo del grafo."""
        self._pending.put(fn)

    def _append(self, lineas: list[ChatLine]) -> None:
        """Añade filas al Signal (copia la lista: Signal no muta in-place)."""
        if not lineas:
            return
        actuales = list(self.lines())
        actuales.extend(lineas)
        self.lines.set(actuales)

    def quit(self) -> None:
        """Para el renderer: cierra la TUI (Esc o salir/q)."""
        renderer = use_renderer()
        if renderer is not None:
            renderer.stop()

    def submit(self, texto: str) -> None:
        """Enter: ignora vacío, cierra si es salir, o lanza un turno."""
        texto = texto.strip()
        if self.busy():
            return
        if not texto:
            return
        if texto.lower() in SALIR:
            self.quit()
            return
        self.draft.set("")
        self._append([ChatLine("human", texto)])
        # El stream emite al TERMINAR cada nodo: iluminamos LLM ya, no al primer chunk.
        self.busy.set(True)
        self.turnos.set(self.turnos() + 1)
        self.active_node.set("juez")
        self.active_tools.set([])
        self.tool_detalle.set([])
        self.llm_detalle.set("")
        self.juez_detalle.set("")
        self.validador_detalle.set("")
        self._grafo = GrafoEstado(phase="judging")
        self.phase.set("judging")
        self.status.set(_status_turno("judging", []))
        self._worker = threading.Thread(target=self._run_turn, args=(texto,), daemon=True)
        self._worker.start()

    def _pintar_grafo(self, estado: GrafoEstado, nuevas: list[ChatLine]) -> None:
        self._grafo = estado
        self.phase.set(estado.phase)
        self.active_tools.set(list(estado.tools))
        self.tool_detalle.set(list(estado.tool_detalle))
        self.llm_detalle.set(estado.llm_detalle)
        self.juez_detalle.set(estado.juez_detalle)
        self.validador_detalle.set(estado.validador_detalle)
        if estado.phase == "tools":
            self.active_node.set("tools")
        elif estado.phase in {"thinking", "writing"}:
            self.active_node.set("chatbot")
        elif estado.phase in {"judging", "retrying"}:
            self.active_node.set("juez")
        elif estado.phase == "validating":
            self.active_node.set("validador")
        self.status.set(_status_turno(estado.phase, estado.tools))
        self._append(nuevas)

    def _run_turn(self, texto: str) -> None:
        """Hilo de fondo: tasks + tokens + updates → cola de UI."""
        from app.langfuse_chat import respuesta_del_grafo, trace_chat_turn

        estado = GrafoEstado(phase="judging")
        try:
            with trace_chat_turn(
                texto,
                thread_id=self.thread_id,
                modelo=self.modelo,
                config=self.config,
            ) as (config, set_output):
                for item in self.graph.stream(
                    {"messages": [HumanMessage(texto)]},
                    config,
                    stream_mode=["tasks", "messages", "updates"],
                ):
                    if isinstance(item, tuple) and len(item) == 2:
                        mode, data = item
                    elif isinstance(item, dict):
                        mode, data = "updates", item
                    else:
                        continue
                    estado = aplicar_evento(estado, str(mode), data)
                    nuevas = (
                        lineas_de_update(data)
                        if mode == "updates" and isinstance(data, dict)
                        else []
                    )

                    def _apply(estado=estado, nuevas=nuevas) -> None:
                        self._pintar_grafo(estado, nuevas)

                    self._ui(_apply)
                set_output(respuesta_del_grafo(self.graph, config))
        except Exception as exc:
            # Timeout de demo u otro fallo: una fila roja, el grafo no se toca.
            msg = str(exc)
            self._ui(lambda: self._append([ChatLine("error", msg)]))
        finally:
            self._ui(self._idle)

    def _idle(self) -> None:
        """Fin de turno: se puede escribir otra vez y el grafo vuelve a reposo."""
        self.busy.set(False)
        self.active_node.set(None)
        self.phase.set("idle")
        self.llm_detalle.set("")
        self._grafo = GrafoEstado(tools=self._grafo.tools, tool_detalle=self._grafo.tool_detalle)
        self.status.set("listo")

    def app(self) -> Box:
        """Monta la app y engancha drain() al ciclo de pintado de OpenTUI."""
        renderer = use_renderer()
        if renderer is not None and self.drain not in renderer._post_process_fns:
            renderer.add_post_process_fn(self.drain)
        return build_app(
            modelo=self.modelo,
            thread_id=self.thread_id,
            lines=self.lines,
            busy=self.busy,
            active_node=self.active_node,
            active_tools=self.active_tools,
            phase=self.phase,
            llm_detalle=self.llm_detalle,
            tool_detalle=self.tool_detalle,
            juez_detalle=self.juez_detalle,
            validador_detalle=self.validador_detalle,
            status=self.status,
            draft=self.draft,
            turnos=self.turnos,
            on_submit=self.submit,
            on_quit=self.quit,
        )


def run_tui(graph: Any, config: dict, *, modelo: str, thread_id: str) -> None:
    """Punto de entrada desde 04_chatbot.py. Exige TTY (no pipes ni IDE run)."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Esta TUI necesita una terminal interactiva.", file=sys.stderr)
        raise SystemExit(1)

    import asyncio

    controller = ChatController(graph, config, modelo, thread_id)
    # render() es async; asyncio.run arranca el bucle hasta que quit() para el renderer.
    try:
        asyncio.run(render(controller.app))
    finally:
        from app.langfuse_chat import shutdown_langfuse

        shutdown_langfuse()
