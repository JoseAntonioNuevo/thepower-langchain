"""Tercera etapa de S5: chatbot con herramientas, sin memoria persistente.

La ruta del proyecto se añade para importar app al ejecutar este archivo desde
la terminal. El bloque __main__ llama al controlador cli.main con las opciones
de esta etapa: memory=False evita SQLite; las herramientas quedan habilitadas por defecto.
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
    main(memory=False)