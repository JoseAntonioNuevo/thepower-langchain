"""Ensayo acotado. Usa subprocesos para demostrar persistencia real."""

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default="grafo")
    args_cli = parser.parse_args()
    batch = "ensayo-" + uuid.uuid4().hex[:8]
    dest = ROOT / "resultados" / batch
    dest.mkdir(parents=True)
    db = str(dest / "memory.sqlite")
    jobs = [
        ("grafo", ["langgraph/01_grafo.py"]),
        (
            "chatbot",
            [
                "langgraph/05_soporte_chatbot.py",
                "--pregunta",
                "Hola, ¿qué puedes hacer?",
            ],
        ),
        ("tools", ["langgraph/06_soporte_tools.py", "--pregunta", "Consulta T-200."]),
        (
            "memoria-escribir",
            [
                "langgraph/07_soporte_memoria.py",
                "--hilo",
                batch + "-a",
                "--db",
                db,
                "--pregunta",
                "Me llamo Alex.",
            ],
        ),
        (
            "memoria-leer",
            [
                "langgraph/07_soporte_memoria.py",
                "--hilo",
                batch + "-a",
                "--db",
                db,
                "--pregunta",
                "¿Cómo me llamo?",
            ],
        ),
        (
            "memoria-aislar",
            [
                "langgraph/07_soporte_memoria.py",
                "--hilo",
                batch + "-b",
                "--db",
                db,
                "--pregunta",
                "¿Cómo me llamo?",
            ],
        ),
        (
            "completo",
            [
                "langgraph/08_soporte_completo.py",
                "--pregunta",
                "Consulta T-100 y su artículo asociado.",
            ],
        ),
        ("baseline", ["observability/01_sin_obs.py"]),
        ("langsmith", ["observability/02_langsmith.py", "--prompts", "remote"]),
        ("langfuse", ["observability/03_langfuse.py", "--prompts", "remote"]),
        ("fallo", ["observability/04_incidente.py", "--prompts", "remote"]),
        (
            "retraso",
            [
                "observability/04_incidente.py",
                "--escenario",
                "retraso",
                "--prompts",
                "remote",
            ],
        ),
    ]
    report = []
    started_jobs = False
    for name, args in jobs:
        if name == args_cli.desde:
            started_jobs = True
        if not started_jobs:
            continue
        target = dest / (name + ".json")
        if name != "grafo":
            args += ["--salida", str(target)]
        start = time.perf_counter()
        r = subprocess.run(
            [sys.executable, "-u", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        elapsed = round(time.perf_counter() - start, 2)
        report.append(
            {
                "name": name,
                "seconds": elapsed,
                "exit_code": r.returncode,
                "result": target.name if name != "grafo" else None,
            }
        )
        print(name, r.returncode, elapsed, flush=True)
        (dest / "tiempos.json").write_text(json.dumps(report, indent=2) + "\n")
        if name == "grafo":
            (dest / "grafo.txt").write_text(r.stdout)
        if r.returncode:
            raise RuntimeError(
                "Ensayo falló en " + name + "; revisar ejecución dirigida"
            )
    (dest / "tiempos.json").write_text(json.dumps(report, indent=2) + "\n")
    print(dest)


if __name__ == "__main__":
    main()
