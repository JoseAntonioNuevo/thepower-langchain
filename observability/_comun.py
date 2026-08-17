"""Helpers de Clase 2: path, PII, config de invoke y resumen del State de 04.

No es una lección. Los scripts 01–04 lo importan para no copiar el hash
ni el parseo del estado del grafo de Clase 1.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# observability/ → raíz del repo (app/, ui/, .env).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from dotenv import load_dotenv

# Misma pregunta que la lección 02. En el grafo de 04 el juez manda a buscar_web.
PREGUNTA = "¿Qué tiempo hace en Madrid?"
# Placeholder de aula. Nunca un email, DNI o teléfono real.
_USER_PLACEHOLDER = "alumno-demo-thepower"
# Tope de clase para el score latency_sla (segundos de reloj).
LATENCY_SLA_S = 30.0


def preparar_entorno() -> None:
    """Carga el .env de la raíz aunque el cwd no sea el repo."""
    load_dotenv(_ROOT / ".env")


def asegurar_var(nombre: str) -> str:
    """Exige una variable de entorno. No imprime el valor (puede ser un secreto)."""
    valor = os.getenv(nombre, "").strip()
    if not valor:
        raise SystemExit(f"Falta {nombre} en .env")
    return valor


def asegurar_openrouter() -> None:
    """02–04 y también 01: el grafo de Clase 1 llama al modelo."""
    asegurar_var("OPENROUTER_API_KEY")


def desactivar_langsmith() -> None:
    """Corta el auto-tracer aunque .env traiga LANGSMITH_TRACING=true."""
    os.environ["LANGSMITH_TRACING"] = "false"


def activar_langsmith() -> None:
    """LangGraph emite el árbol completo con estas vars. Sin callbacks extra."""
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "thepower-clase-2")
    asegurar_var("LANGSMITH_API_KEY")


def asegurar_langfuse() -> None:
    """Claves v4. El host es LANGFUSE_BASE_URL, no LANGFUSE_HOST."""
    asegurar_var("LANGFUSE_PUBLIC_KEY")
    asegurar_var("LANGFUSE_SECRET_KEY")
    os.environ.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")


def user_id_hash() -> str:
    """16 hex del SHA-256. Eso es lo que viaja en metadata / user_id."""
    return hashlib.sha256(_USER_PLACEHOLDER.encode()).hexdigest()[:16]


def config_base(
    thread_id: str,
    *,
    leccion: str,
    tags: list[str],
    callbacks: list[Any] | None = None,
) -> dict[str, Any]:
    """RunnableConfig: mismo hilo de Clase 1 + sufijo para no mezclar trazas."""
    hashed = user_id_hash()
    config: dict[str, Any] = {
        "configurable": {"thread_id": f"{thread_id}-c2-{leccion}"},
        "tags": tags,
        "metadata": {"user_id": hashed, "lesson": leccion},
    }
    if callbacks:
        config["callbacks"] = callbacks
    return config


def _texto(content: Any) -> str:
    """Saca texto plano del content de un mensaje (str, bloques o None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes: list[str] = []
        for block in content:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if t:
                    partes.append(str(t))
        return "\n".join(partes)
    return str(content)


def _es_error_tool(contenido: str) -> bool:
    """ToolNode envuelve TimeoutError; el interruptor de demo dice timeout simulado."""
    bajo = contenido.lower()
    return "timeout simulado" in bajo or "timeouterror" in bajo or bajo.startswith("error:")


@dataclass(frozen=True)
class ResumenTurno:
    peticiones: list[str]
    datos: list[str]
    respuesta: str
    ok: bool | None
    motivo_validador: str
    usar_web: bool | None
    intentos: int
    hubo_error_tool: bool


def resumen(resultado: dict[str, Any]) -> ResumenTurno:
    """Lee el State de 04: tools, draft/AI, veredicto. El validador puede no publicar."""
    peticiones: list[str] = []
    datos: list[str] = []
    hubo_error = False
    ultima_ai = ""
    for mensaje in resultado.get("messages") or []:
        tipo = getattr(mensaje, "type", None)
        if tipo == "ai":
            for llamada in getattr(mensaje, "tool_calls", None) or []:
                nombre = llamada.get("name", "?")
                args = llamada.get("args", {})
                argumentos = ", ".join(f"{clave}={valor!r}" for clave, valor in args.items())
                peticiones.append(f"{nombre}({argumentos})")
            if not getattr(mensaje, "tool_calls", None):
                texto = _texto(getattr(mensaje, "content", ""))
                if texto:
                    ultima_ai = texto
        elif tipo == "tool":
            nombre = getattr(mensaje, "name", None) or "tool"
            contenido = _texto(getattr(mensaje, "content", ""))
            datos.append(f"{nombre}: {contenido}")
            if _es_error_tool(contenido):
                hubo_error = True
    draft = str(resultado.get("draft") or "").strip()
    respuesta = draft or ultima_ai
    ok = resultado.get("ok")
    return ResumenTurno(
        peticiones=peticiones,
        datos=datos,
        respuesta=respuesta,
        ok=None if ok is None else bool(ok),
        motivo_validador=str(resultado.get("motivo_validador") or ""),
        usar_web=None if "usar_web" not in resultado else bool(resultado.get("usar_web")),
        intentos=int(resultado.get("intentos") or 0),
        hubo_error_tool=hubo_error,
    )


def puntuaciones(info: ResumenTurno, latencia_s: float) -> dict[str, float]:
    """Scores de aula, no un segundo juez: 1.0 o 0.0."""
    tool_ok = bool(info.datos) and not info.hubo_error_tool
    return {
        "tool_success": 1.0 if tool_ok else 0.0,
        "answer_quality": 1.0 if info.respuesta.strip() else 0.0,
        "latency_sla": 1.0 if latencia_s < LATENCY_SLA_S else 0.0,
    }


def _ancho_panel() -> int:
    """Cabe en la terminal. panel() se ensancha a la línea más larga (Tavily)."""
    columnas = shutil.get_terminal_size((80, 24)).columns
    return max(40, min(72, columnas - 4))


def _envolver(texto: str) -> str:
    """Parte párrafos y URLs para que el recuadro no se rompa al envolver el TTY."""
    ancho = _ancho_panel()
    lineas: list[str] = []
    for cruda in texto.splitlines() or [""]:
        trozos = textwrap.wrap(
            cruda,
            width=ancho,
            break_long_words=True,
            break_on_hyphens=False,
        )
        lineas.extend(trozos or [""])
    return "\n".join(lineas)


def esperando(texto: str) -> None:
    """Una línea fija. El spinner de Clase 1 (\r + color 12 Hz) apaga el TTY de VS Code."""
    from ui.consola import THINK, panel

    print(panel("espera", texto, THINK), flush=True)


def imprimir_resumen(pregunta: str, info: ResumenTurno, *, latencia_s: float | None = None) -> None:
    """Paneles al estilo de langgraph/02_tools.py."""
    from ui.consola import BRIGHT, DATO, THINK, TOOL, panel

    print(panel("pregunta", pregunta, BRIGHT))
    if info.usar_web is not None:
        print(panel("juez usar_web", "si" if info.usar_web else "no", THINK))
    print(panel("tool solicitada", _envolver("\n".join(info.peticiones) or "(ninguna)"), TOOL))
    print(panel("dato devuelto", _envolver("\n".join(info.datos) or "(sin resultado)"), DATO))
    print(
        panel(
            "respuesta",
            _envolver(info.respuesta or "(vacía: el validador no publicó)"),
            BRIGHT,
        )
    )
    if info.ok is not None or info.motivo_validador:
        veredicto = "ok" if info.ok else "reintenta/cierra"
        motivo = info.motivo_validador or "(sin motivo)"
        print(panel("validador", _envolver(f"{veredicto} · intentos={info.intentos}\n{motivo}"), THINK))
    if latencia_s is not None:
        print(panel("latencia", f"{latencia_s:.1f}s (sla {LATENCY_SLA_S:.0f}s)", DATO))
