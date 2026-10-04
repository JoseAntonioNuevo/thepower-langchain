"""Apertura y cierre de la memoria persistente en SQLite.

sqlite_memory prepara la ruta, abre un SqliteSaver y lo entrega al bloque with
del llamador. Al salir del bloque se cierra la conexión, también si hay un error.
El checkpointer guarda el estado por thread_id: usar la misma DB y el mismo hilo
permite continuar desde otro proceso; otro hilo mantiene un estado independiente.
Este módulo no abre bases de datos simplemente por importarlo.
"""

from contextlib import contextmanager
from pathlib import Path


# El decorador permite escribir «with sqlite_memory(ruta) as saver».
@contextmanager
def sqlite_memory(path):
    # Importación diferida: la dependencia se necesita al abrir la memoria.
    from langgraph.checkpoint.sqlite import SqliteSaver

    # Normalizar la ruta y crear la carpeta evita fallos en el primer uso.
    db = Path(path).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    # El with interno administra la conexión; yield la presta al llamador.
    with SqliteSaver.from_conn_string(str(db)) as saver:
        yield saver
