"""Etapa de aula sobre el núcleo compartido de soporte."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.cli import main

if __name__ == "__main__":
    main(chatbot_only=True, memory=False)
