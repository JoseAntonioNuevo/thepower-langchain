"""02 — LangSmith: LANGSMITH_* + graph.invoke() = el árbol completo. ~15 min."""

from _comun import (
    PREGUNTA,
    activar_langsmith,
    asegurar_openrouter,
    config_base,
    esperando,
    imprimir_resumen,
    preparar_entorno,
    resumen,
    user_id_hash,
)

preparar_entorno()

from langchain_core.messages import HumanMessage

from app.graph import MODELO, graph, thread_id
from ui.consola import BRIGHT, DATO, THINK, banner, grafo_ascii, panel

# Prompt versionado de Hub. Solo se enseña; no se enlaza al grafo (cambiaría el ciclo).
_PROMPT_HUB = "thepower-obs:staging"


def _mostrar_prompt_hub() -> None:
    """pull_prompt es opcional: si el Hub no tiene el tag, se salta."""
    try:
        from langsmith import Client

        prompt = Client().pull_prompt(_PROMPT_HUB)
        nombre = getattr(prompt, "name", None) or _PROMPT_HUB
        print(panel("prompt Hub", f"ok · {nombre}\nno se inyecta en el grafo", DATO))
    except Exception as exc:
        print(
            panel(
                "prompt Hub",
                f"no hay prompt en Hub ({_PROMPT_HUB})\n{type(exc).__name__}",
                THINK,
            )
        )


if __name__ == "__main__":
    import os

    asegurar_openrouter()
    activar_langsmith()
    print(banner("C2-02", "LangSmith", 15))
    print(panel("grafo", grafo_ascii(["juez", "chatbot", "tools", "validador"]), THINK))
    print(panel("modelo", MODELO, BRIGHT))
    print(
        panel(
            "env",
            f"LANGSMITH_TRACING={os.environ.get('LANGSMITH_TRACING')}\n"
            f"LANGSMITH_PROJECT={os.environ.get('LANGSMITH_PROJECT')}\n"
            f"user_id={user_id_hash()}  (sha256, 16 hex)",
            DATO,
        )
    )
    _mostrar_prompt_hub()

    config = config_base(
        thread_id,
        leccion="02",
        tags=["clase-2", "langsmith", "thepower"],
    )
    esperando("invoke + traza LangSmith (juez + tools + validador; ~30s)…")
    resultado = graph.invoke({"messages": [HumanMessage(PREGUNTA)]}, config)

    imprimir_resumen(PREGUNTA, resumen(resultado))
    print(
        panel(
            "en la UI",
            "Abre el proyecto LANGSMITH_PROJECT. Deberías ver el árbol:\n"
            f"thread_id={config['configurable']['thread_id']}\n"
            "metadata.user_id = hash · tags = clase-2, langsmith, thepower",
            THINK,
        )
    )
