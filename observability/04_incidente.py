"""04 — Timeout forzado: el mismo fallo en LangSmith y Langfuse. ~20 min."""

import os
import time

from _comun import (
    PREGUNTA,
    activar_langsmith,
    asegurar_langfuse,
    asegurar_openrouter,
    config_base,
    esperando,
    imprimir_resumen,
    preparar_entorno,
    puntuaciones,
    resumen,
    user_id_hash,
)

preparar_entorno()
# El interruptor ya vive en buscar_web / buscar_clima de Clase 1. Solo lo encendemos.
os.environ["DEMO_FORCE_TOOL_ERROR"] = "1"

from langchain_core.messages import HumanMessage
from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from app.graph import MODELO, graph, thread_id
from ui.consola import BRIGHT, DATO, THINK, banner, grafo_ascii, panel

if __name__ == "__main__":
    asegurar_openrouter()
    activar_langsmith()
    asegurar_langfuse()
    print(banner("C2-04", "Incidente: timeout de tool", 20))
    print(panel("grafo", grafo_ascii(["juez", "chatbot", "tools", "validador"]), THINK))
    print(panel("modelo", MODELO, BRIGHT))
    hashed = user_id_hash()
    print(
        panel(
            "demo",
            "DEMO_FORCE_TOOL_ERROR=1\n"
            "buscar_web (y buscar_clima) levantan TimeoutError.\n"
            "Tavily no se llama. El fallo es la tool, no el juez.",
            THINK,
        )
    )

    langfuse = get_client()
    handler = CallbackHandler()
    config = config_base(
        thread_id,
        leccion="04",
        tags=["clase-2", "incidente", "thepower"],
        callbacks=[handler],
    )
    session_id = config["configurable"]["thread_id"]
    t0 = time.perf_counter()
    try:
        with langfuse.start_as_current_observation(
            as_type="span", name="observability-incidente"
        ) as span:
            with propagate_attributes(
                user_id=hashed,
                session_id=session_id,
                tags=["clase-2", "incidente"],
            ):
                esperando("invoke con timeout simulado (juez + tools + validador; ~30s)…")
                resultado = graph.invoke(
                    {"messages": [HumanMessage(PREGUNTA)]},
                    config,
                )
            latencia = time.perf_counter() - t0
            info = resumen(resultado)
            scores = puntuaciones(info, latencia)
            for nombre, valor in scores.items():
                span.score_trace(name=nombre, value=valor, data_type="NUMERIC")
    finally:
        langfuse.shutdown()

    imprimir_resumen(PREGUNTA, info, latencia_s=latencia)
    print(
        panel(
            "scores",
            "\n".join(f"{nombre}={valor:.0f}" for nombre, valor in scores.items()),
            DATO,
        )
    )
    print(
        panel(
            "preguntas",
            "En LangSmith y en Langfuse, abre el run de la tool que falló.\n"
            "1. ¿Falló el juez/router o la tool?\n"
            "2. ¿El validador reintenta (intentos=1) o cierra?\n"
            "3. ¿El fallback le dice al usuario que hubo timeout?",
            THINK,
        )
    )
