"""03 — El mismo invoke a través de Langfuse v4 (OTel). ~20 min."""

import time

from _comun import (
    PREGUNTA,
    asegurar_langfuse,
    asegurar_openrouter,
    config_base,
    desactivar_langsmith,
    esperando,
    imprimir_resumen,
    preparar_entorno,
    puntuaciones,
    resumen,
    user_id_hash,
)

# Este árbol es Langfuse: apagamos LangSmith aunque .env lo tenga encendido.
preparar_entorno()
desactivar_langsmith()

from langchain_core.messages import HumanMessage
from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from app.graph import MODELO, graph, thread_id
from ui.consola import BRIGHT, DATO, THINK, banner, grafo_ascii, panel

if __name__ == "__main__":
    import os

    asegurar_openrouter()
    asegurar_langfuse()
    print(banner("C2-03", "Langfuse", 20))
    print(panel("grafo", grafo_ascii(["juez", "chatbot", "tools", "validador"]), THINK))
    print(panel("modelo", MODELO, BRIGHT))
    hashed = user_id_hash()
    print(
        panel(
            "env",
            f"LANGFUSE_BASE_URL={os.environ.get('LANGFUSE_BASE_URL')}\n"
            f"user_id={hashed}  (sha256, 16 hex)\n"
            "session_id = thread_id de esta lección",
            DATO,
        )
    )

    langfuse = get_client()
    handler = CallbackHandler()
    config = config_base(
        thread_id,
        leccion="03",
        tags=["clase-2", "langfuse", "thepower"],
        callbacks=[handler],
    )
    session_id = config["configurable"]["thread_id"]
    t0 = time.perf_counter()
    try:
        with langfuse.start_as_current_observation(
            as_type="span", name="observability-langfuse"
        ) as span:
            with propagate_attributes(
                user_id=hashed,
                session_id=session_id,
                tags=["clase-2", "langfuse"],
            ):
                esperando("invoke + traza Langfuse (juez + tools + validador; ~30s)…")
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
        # CLI corto: sin shutdown() se pierde el batch al salir.
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
            "en la UI",
            f"session_id={session_id}\n"
            "user_id y session_id van first-class (propagate_attributes),\n"
            "no solo en metadata de LangChain.",
            THINK,
        )
    )
