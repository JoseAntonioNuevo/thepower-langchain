"""Dos prompts congelados, diez consultas reservadas y conversaciones limpias."""

import csv
import json
import uuid
from datetime import datetime, timezone
from .config import ROOT, settings, make_model
from .telemetry import Telemetry
from .runner import run_turn
from .prompts import MANIFEST


def comparison_rows(cases, versions=("v1", "v2")):
    batch = uuid.uuid4().hex[:12]
    for version in versions:
        for case in cases:
            yield version, case, f"eval-{batch}-{version}-{case['id']}"


def export_results(rows, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "resultados.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    )
    fields = [
        "case_id",
        "prompt_version",
        "question",
        "answer",
        "expected",
        "quality",
        "duration_s",
        "tool_count",
        "errors",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cost_usd",
        "cost_method",
        "langsmith_run_id",
        "langfuse_trace_id",
    ]
    with (directory / "resultados.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Comparación de prompts",
        "",
        "La valoración manual usa la rúbrica previa. `null` significa pendiente/no disponible, no cero.",
        "",
        "| Caso | Prompt | Segundos | Tools | Tokens | Coste USD | Calidad |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['case_id']} | {r['prompt_version']} | {r['duration_s']} | {r['tool_count']} | {r['total_tokens']} | {r['cost_usd']} | {r['quality']} |"
        )
    (directory / "comparacion.md").write_text("\n".join(lines) + "\n")


def main():
    cfg = settings()
    cases = json.loads((ROOT / "datos/soporte/evaluacion.json").read_text())
    if len(cases) != 10 or len({c["id"] for c in cases}) != 10:
        raise ValueError("Se requieren diez casos únicos")
    if not MANIFEST.exists():
        raise ValueError("Primero registra los prompts remotos")
    destination = (
        ROOT
        / "resultados"
        / ("comparacion-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    )
    t = Telemetry.open("both")
    rows = []
    try:
        model = make_model(cfg)
        for version, case, thread in comparison_rows(cases):
            r = run_turn(
                model=model,
                cfg=cfg,
                telemetry=t,
                question=case["pregunta"],
                thread_id=thread,
                db=destination / "memoria.sqlite",
                version=version,
                source="remote",
            )
            r.update(
                case_id=case["id"],
                expected=case["esperado"],
                expected_tools=case["tools"],
            )
            rows.append(r)
            export_results(rows, destination)
            print(
                f"{case['id']} {version}: {r['status']} · tools={r['tool_count']} · {r['duration_s']}s",
                flush=True,
            )
            if r["status"] == "model_error":
                raise RuntimeError(
                    "Fallo de proveedor; lote detenido y resultados parciales conservados"
                )
    finally:
        t.close()
    print("Resultados:", destination)


if __name__ == "__main__":
    main()
