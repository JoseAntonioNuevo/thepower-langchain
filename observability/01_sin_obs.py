"""01 — El agente de Clase 1, sin observabilidad. ~10 min."""

import os

from _comun import (
    PREGUNTA,
    asegurar_openrouter,
    config_base,
    desactivar_langsmith,
    esperando,
    imprimir_resumen,
    preparar_entorno,
    resumen,
    user_id_hash,
)

# Carga .env y apaga LangSmith antes de invoke. Si el grafo falla, el bug es el del 5 oct.
preparar_entorno()
desactivar_langsmith()

from langchain_core.messages import HumanMessage

from app.graph import MODELO, graph, thread_id
from ui.consola import BRIGHT, THINK, banner, grafo_ascii, panel

if __name__ == "__main__":
    asegurar_openrouter()
    print(banner("C2-01", "Sin observabilidad", 10))
    print(panel("grafo", grafo_ascii(["juez", "chatbot", "tools", "validador"]), THINK))
    print(panel("modelo", MODELO, BRIGHT))
    print(
        panel(
            "higiene",
            f"LANGSMITH_TRACING={os.environ.get('LANGSMITH_TRACING')}\n"
            f"user_id hash (no se envía: no hay tracer)={user_id_hash()}",
            THINK,
        )
    )

    esperando("el grafo de Clase 1 corre (juez + tools + validador; ~30s)…")
    resultado = graph.invoke(
        {"messages": [HumanMessage(PREGUNTA)]},
        config_base(thread_id, leccion="01", tags=["clase-2", "sin-obs", "thepower"]),
    )

    imprimir_resumen(PREGUNTA, resumen(resultado))
    print(
        panel(
            "qué falta",
            "Hay respuesta (o un fallback). No hay árbol que inspeccionar:\n"
            "ni spans de juez/tools, ni tags, ni user_id.\n"
            "Si este script falla, el bug es el grafo del lunes, no LangSmith.",
            THINK,
        )
    )
