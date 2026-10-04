"""Comprobación del entorno antes de comenzar las demos de S5 y S6.

main informa de Python, modelo, directorio de datos, versiones instaladas y
presencia de configuración, sin mostrar valores secretos. Por defecto no
consulta el modelo ni los servicios de trazas. La opción --online ejecuta una
consulta real con observabilidad en ambas plataformas y guarda su resultado;
requiere sus credenciales y puede consumir API. El finally cierra las trazas.
"""

import argparse
import importlib.metadata
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.config import settings, ROOT


# Lee --online y prepara el informe; la consulta real es opcional.
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--online", action="store_true")
    args = p.parse_args()
    cfg = settings()
    # Datos no secretos para comprobar el entorno antes del directo.
    info = {
        "python": sys.version.split()[0],
        "model": cfg.model_id,
        "data": str(ROOT / "data"),
        "dependencies": {},
        "configuration": {},
    }
    # Consultamos versiones instaladas; no instalamos ni actualizamos paquetes.
    for name in [
        "langgraph",
        "langgraph-checkpoint-sqlite",
        "langchain-openrouter",
        "langsmith",
        "langfuse",
    ]:
        try:
            info["dependencies"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            info["dependencies"][name] = "MISSING"
    # Solo configured/missing: nunca imprimir el valor de una credencial.
    for key in [
        "OPENROUTER_API_KEY",
        "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    ]:
        info["configuration"][key] = "configured" if os.getenv(key) else "missing"
    print(json.dumps(info, indent=2))
    # Rama con red: consulta real, SQLite propia y trazas en ambas plataformas.
    if args.online:
        from app.soporte.telemetry import Telemetry
        from app.soporte.config import make_model
        from app.soporte.runner import run_turn

        t = Telemetry.open("both")
        try:
            r = run_turn(
                model=make_model(cfg),
                cfg=cfg,
                telemetry=t,
                question="Consulta el ticket T-100.",
                thread_id="preflight",
                db=ROOT / "data/preflight.sqlite",
            )
            out = ROOT / "resultados/preflight.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(r, ensure_ascii=False))
            if r["status"] == "model_error":
                raise SystemExit(2)
        # Asegurar el cierre incluso si falla la prueba online.
        finally:
            t.close()


if __name__ == "__main__":
    main()