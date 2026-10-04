"""Ejecución observable y resultados de aula sin credenciales."""

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
):
    prompt, meta = resolve_prompt(version, source, telemetry)
    query_id = query_id or str(uuid.uuid4())
    started = time.perf_counter()
    with sqlite_memory(db) if db is not None else nullcontext(None) as saver:
        graph = build_graph(
            model,
            prompt=prompt,
            checkpointer=saver,
            tools=make_tools(scenario=scenario),
            use_tools=use_tools,
        )
        with telemetry.turn(
            thread_id=thread_id,
            model_id=cfg.model_id,
            prompt_meta=meta,
            scenario=scenario,
            query_id=query_id,
        ) as config:
            result = graph.invoke(
                {"messages": [HumanMessage(content=question)]}, config
            )
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
    if telemetry.lf and record["langfuse_trace_id"]:
        telemetry.lf.create_score(
            name="answer_present",
            value=float(record["answer_present"]),
            trace_id=record["langfuse_trace_id"],
        )
        telemetry.lf.flush()
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
    return redact(record)
