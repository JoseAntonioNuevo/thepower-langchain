from contextlib import contextmanager
from pathlib import Path


@contextmanager
def sqlite_memory(path):
    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(path).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(db)) as saver:
        yield saver
