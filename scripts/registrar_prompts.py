"""Registra prompts propios. --nuevo archiva el manifiesto local anterior."""
import argparse
import json
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.config import settings
from app.soporte.telemetry import Telemetry
from app.soporte.prompts import register_prompts, prepare_prompt_manifest

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Registro privado de prompts S6")
    p.add_argument("--nuevo", action="store_true", help="Crear un lote propio nuevo, conservando el anterior")
    a = p.parse_args()
    settings()
    t = Telemetry.open("both")
    try:
        manifest = prepare_prompt_manifest()
        if a.nuevo and manifest.exists():
            manifest.rename(manifest.with_name(
                "prompts-remotos-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
            ))
        print(json.dumps(register_prompts(t, migrate=not a.nuevo), indent=2))
    finally:
        t.close()
