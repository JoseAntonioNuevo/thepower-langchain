"""Controlador de terminal compartido por los ejemplos de S5 y S6.

main interpreta argumentos, carga configuración y prepara modelo y observabilidad.
Cada pregunta pasa a run_turn; su resultado se imprime como JSON y, opcionalmente,
se guarda en disco. El modo interactivo permite varios turnos hasta escribir
«salir» o «q». Los lanzadores eligen si se habilitan herramientas y memoria.
El bloque finally cierra la observabilidad incluso si la ejecución falla.
Los clientes se crean al ejecutar main, no al importar el archivo.
"""

import argparse
import json
from pathlib import Path
import uuid
from .config import ROOT, settings, make_model


# Punto de entrada: las opciones de la etapa se combinan con argumentos de terminal.
def main(
    default_mode="off", default_scenario="normal", *, chatbot_only=False, memory=True
):
    # 1. Argumentos: pregunta, conversación, DB, observabilidad y salida.
    parser = argparse.ArgumentParser(description="S5/S6 · Agente de soporte thePower")
    parser.add_argument(
        "--pregunta", default="Consulta T-100 y el artículo de ayuda asociado."
    )
    parser.add_argument("--hilo", default="aula-" + uuid.uuid4().hex[:8])
    parser.add_argument("--db", type=Path, default=ROOT / "data/soporte.sqlite")
    parser.add_argument(
        "--observabilidad",
        choices=["off", "langsmith", "langfuse", "both"],
        default=default_mode,
    )
    parser.add_argument(
        "--escenario", choices=["normal", "fallo", "retraso"], default=default_scenario
    )
    parser.add_argument("--version", choices=["v1", "v2"], default="v2")
    parser.add_argument("--prompts", choices=["local", "remote"], default="local")
    parser.add_argument("--salida", type=Path)
    parser.add_argument("--interactivo", action="store_true")
    args = parser.parse_args()
    # 2. Cargar entorno y crear los clientes solo después de interpretar argumentos.
    cfg = settings()
    from .telemetry import Telemetry
    from .runner import run_turn

    telemetry = Telemetry.open(args.observabilidad)
    try:
        model = make_model(cfg)
        # 3. Un turno por consulta; en modo interactivo repetimos hasta salir.
        while True:
            question = (
                input("Tú (salir para terminar): ")
                if args.interactivo
                else args.pregunta
            )
            if question.strip().lower() in {"salir", "q"}:
                break
            # Los booleanos de la etapa deciden si se usa SQLite y si hay tools.
            record = run_turn(
                model=model,
                cfg=cfg,
                telemetry=telemetry,
                question=question,
                thread_id=args.hilo,
                db=args.db if memory else None,
                version=args.version,
                source=args.prompts,
                scenario=args.escenario,
                use_tools=not chatbot_only,
            )
            # 4. Mostrar la evidencia del turno y guardar una copia si se pide.
            print(json.dumps(record, ensure_ascii=False, indent=2))
            if args.salida:
                args.salida.parent.mkdir(parents=True, exist_ok=True)
                args.salida.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n"
                )
            # En modo no interactivo se termina tras una consulta; código 2 si falla el modelo.
            if not args.interactivo:
                if record["status"] == "model_error":
                    raise SystemExit(2)
                break
    # 5. Enviar/cerrar las trazas tanto al terminar bien como ante una excepción.
    finally:
        telemetry.close()


if __name__ == "__main__":
    main()