import argparse
import json
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.config import settings
from app.soporte.telemetry import Telemetry
from app.soporte.prompts import register_prompts

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--nuevo", action="store_true")
    a = p.parse_args()
    if a.nuevo:
        from app.soporte.prompts import MANIFEST

        if MANIFEST.exists():
            MANIFEST.rename(
                MANIFEST.with_name(
                    "prompts-remotos-"
                    + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                    + ".json"
                )
            )
    settings()
    t = Telemetry.open("both")
    try:
        print(json.dumps(register_prompts(t), indent=2))
    finally:
        t.close()
