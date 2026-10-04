"""Lee árboles remotos y verifica privacidad/correlación. No invoca modelos."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.config import settings, ROOT
from app.soporte.telemetry import Telemetry
from app.soporte.privacy import redact


def verify_record(t, record):
    result = {"query_id": record["query_id"], "checks": {}, "nodes": {}}
    if record.get("langsmith_run_id"):
        run = t.ls.read_run(record["langsmith_run_id"], load_child_runs=True)
        payload = (
            run.model_dump(mode="json") if hasattr(run, "model_dump") else run.dict()
        )
        raw = json.dumps(payload, default=str)

        def walk(r):
            return [{"name": r.name, "type": r.run_type, "id": str(r.id)}] + [
                x for child in (r.child_runs or []) for x in walk(child)
            ]

        nodes = walk(run)
        result["nodes"]["langsmith"] = nodes
        result["checks"]["langsmith_root"] = run.parent_run_id is None
        result["checks"]["langsmith_model_nodes"] = (
            sum(n["type"] == "llm" for n in nodes) == record["model_calls"]
        )
        result["checks"]["langsmith_mask"] = all(
            s not in raw for s in ["aula@example.test", "SECRET_DEMO_123"]
        )
        result["langsmith_url"] = run.url
        result["langsmith_payload"] = redact(payload)
    if record.get("langfuse_trace_id"):
        trace = t.lf.api.trace.get(record["langfuse_trace_id"])
        payload = trace.dict()
        raw = json.dumps(payload, default=str)
        obs = payload.get("observations", [])
        result["nodes"]["langfuse"] = [
            {
                "name": o.get("name"),
                "type": o.get("type"),
                "id": o.get("id"),
                "promptVersion": o.get("prompt_version", o.get("promptVersion")),
            }
            for o in obs
        ]
        result["checks"]["langfuse_root"] = (
            sum(
                not o.get("parent_observation_id", o.get("parentObservationId"))
                for o in obs
            )
            == 1
        )
        result["checks"]["langfuse_model_nodes"] = (
            sum(o.get("type") == "GENERATION" for o in obs) == record["model_calls"]
        )
        result["checks"]["langfuse_mask"] = all(
            s not in raw for s in ["aula@example.test", "SECRET_DEMO_123"]
        )
        result["langfuse_payload"] = redact(payload)
        result["langfuse_trace_id"] = record["langfuse_trace_id"]
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument(
        "--salida", type=Path, default=ROOT / "resultados/verificacion-trazas.json"
    )
    a = p.parse_args()
    settings()
    t = Telemetry.open("both")
    rows = json.loads(a.results.read_text())
    rows = rows if isinstance(rows, list) else [rows]
    evidence = []
    try:
        for row in rows:
            for attempt in range(4):
                try:
                    r = verify_record(t, row)
                    if all(r["checks"].values()):
                        break
                except Exception as exc:
                    if attempt == 3:
                        raise RuntimeError(
                            "No se pudo leer la traza: " + type(exc).__name__
                        ) from None
                time.sleep(2)
            evidence.append(r)
            print(row["query_id"], r["checks"], flush=True)
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        a.salida.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        if not all(all(r["checks"].values()) for r in evidence):
            raise SystemExit(2)
    finally:
        t.close()


if __name__ == "__main__":
    main()
