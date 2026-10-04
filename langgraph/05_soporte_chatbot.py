"""Segunda etapa de S5: chatbot sin herramientas ni memoria persistente.

La ruta del proyecto se añade para importar app al ejecutar este archivo desde
la terminal. El bloque __main__ llama al controlador cli.main con las opciones
de esta etapa: chatbot_only=True deshabilita herramientas; memory=False evita SQLite.
El grafo no se duplica aquí: sus nodos están en app/soporte/graph.py; la consola
interpreta --pregunta, --hilo, --db y --salida. Importar el lanzador no ejecuta
la demo.
"""

import sys
from pathlib import Path

# La carpeta raíz debe estar en la ruta de importación para encontrar app.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.soporte.cli import main

# Ejecutar este archivo inicia la etapa; importarlo solo define su entrada.
if __name__ == "__main__":
    main(chatbot_only=True, memory=False)