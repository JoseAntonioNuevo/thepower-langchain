"""Ejecuta un turno del agente y prepara el resultado que enseñamos en clase.

run_turn resuelve el prompt, abre SQLite si corresponde, construye el grafo y
lo ejecuta con un HumanMessage y un thread_id. La observabilidad rodea ese turno
sin construir otro agente. Después reúne respuesta, ruta, herramientas, errores,
tokens y coste informado por el proveedor. Las métricas ausentes quedan en None.
Al devolver el resultado aplica el filtrado de datos para su salida; esto no
filtra automáticamente el historial SQLite ni lo enviado al proveedor.
La TUI puede aportar memoria en RAM y un callback on_update: el grafo se ejecuta
una sola vez en modo stream para mostrar sus pasos y obtener el resultado final.
"""

from contextlib import nullcontext
import time
import uuid
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from .graph import build_graph
from .persistence import sqlite_memory
from .tools import make_tools
from .prompts import resolve_prompt
from .privacy import redact


# Ejecuta un turno: el grafo conserva el historial y reinicia las métricas del turno.
def run_turn(
    *,
    model,
    cfg,
    telemetry,
    question,
    thread_id,
    db,
    version="v2",
    source="local",
    scenario="normal",
    use_tools=True,
    query_id=None,
    memory_saver=None,
    on_update=None,
):
    # 1. Aplicar el prompt y asignar un ID único a esta consulta.
    prompt, meta = resolve_prompt(version, source, telemetry)
    query_id = query_id or str(uuid.uuid4())
    started = time.perf_counter()
    # 2. Mantener SQLite abierta durante la invocación; sin DB, el saver es None.
    with sqlite_memory(db) if db is not None else nullcontext(memory_saver) as saver:
        # El escenario cambia las tools de prueba, no la estructura del agente.
        graph = build_graph(
            model,
            prompt=prompt,
            checkpointer=saver,
            tools=make_tools(scenario=scenario),
            use_tools=use_tools,
        )
        # 3. Preparar hilo y callbacks; off conserva el hilo sin exportar trazas.
        with telemetry.turn(
            thread_id=thread_id,
            model_id=cfg.model_id,
            prompt_meta=meta,
            scenario=scenario,
            query_id=query_id,
        ) as config:
            # Solo aportamos el mensaje nuevo; el checkpointer recupera los anteriores.
            if on_update is None:
                result = graph.invoke(
                    {"messages": [HumanMessage(content=question)]}, config
                )
            else:
                # Una sola ejecución: updates alimenta la TUI y values entrega
                # el estado final, también cuando no hay un checkpointer SQLite.
                for mode, payload in graph.stream(
                    {"messages": [HumanMessage(content=question)]},
                    config,
                    stream_mode=["updates", "values"],
                ):
                    if mode == "updates":
                        on_update(payload)
                    elif mode == "values":
                        result = payload
    # 4. Medir duración y sumar métricas solo si todas las llamadas las informan.
    duration = time.perf_counter() - started
    last = result["messages"][-1]
    usage = result["usage"]
    token_keys = ["input_tokens", "output_tokens", "total_tokens"]
    totals = {
        k: sum(u["tokens"][k] for u in usage)
        if usage and all(u["tokens"] and k in u["tokens"] for u in usage)
        else None
        for k in token_keys
    }
    costs = [u["cost_usd"] for u in usage]
    # 5. Evidencia de este turno para la consola; no exportamos aquí todo el historial.
    record = {
        "query_id": query_id,
        "thread_id": thread_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": str(last.content),
        "model": cfg.model_id,
        "scenario": scenario,
        **meta,
        "duration_s": round(duration, 3),
        "tool_count": result["tool_count"],
        "calls": result["calls"],
        "errors": result["errors"],
        "status": result["status"],
        "route": result["route"],
        "model_calls": len(usage),
        **totals,
        "cost_usd": sum(costs) if costs and all(c is not None for c in costs) else None,
        "cost_method": "provider_reported"
        if costs and all(c is not None for c in costs)
        else "unavailable",
        "langsmith_run_id": query_id if telemetry.ls else None,
        "langfuse_trace_id": getattr(telemetry.handler, "last_trace_id", None)
        if telemetry.handler
        else None,
        "answer_present": bool(str(last.content).strip()),
        "quality": None,
    }
    # answer_present mide existencia de texto, no calidad de la respuesta.
    if telemetry.lf and record["langfuse_trace_id"]:
        telemetry.lf.create_score(
            name="answer_present",
            value=float(record["answer_present"]),
            trace_id=record["langfuse_trace_id"],
        )
        telemetry.lf.flush()
    # Exportar coste informado por el proveedor solo cuando se conoce.
    if record["cost_usd"] is not None:
        if telemetry.lf and record["langfuse_trace_id"]:
            telemetry.lf.create_score(
                name="provider_cost_usd",
                value=record["cost_usd"],
                trace_id=record["langfuse_trace_id"],
                comment="USD informados por OpenRouter; no tarifa inferida de la plataforma",
            )
        if telemetry.ls:
            telemetry.ls.create_feedback(
                record["langsmith_run_id"],
                key="provider_cost_usd",
                score=record["cost_usd"],
                comment="USD informados por OpenRouter; no tarifa inferida de la plataforma",
            )
        telemetry.flush()
    # 6. Filtrar la copia devuelta; no modifica el estado interno ni lo enviado al modelo.
    return redact(record)
