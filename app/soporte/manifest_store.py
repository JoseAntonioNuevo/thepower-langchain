"""Persistencia local de metadatos de prompts; no contiene credenciales.

Solo usa la biblioteca estándar. No abre cuentas ni crea prompts remotos.
La copia antigua se conserva y nunca reemplaza un manifiesto nuevo existente.
"""
import json
import os
import tempfile
from pathlib import Path


def write_manifest(path: Path, value: dict) -> None:
    """Escribe JSON de forma atómica para no dejar un fichero parcial."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare_manifest(path: Path, legacy: Path) -> Path:
    """Prepara el directorio y copia el manifiesto histórico solo si hace falta."""
    path, legacy = Path(path), Path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() and legacy.is_file() and path != legacy:
        try:
            value = json.loads(legacy.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("El manifiesto histórico no es JSON válido; no se ha sustituido.") from exc
        if not isinstance(value, dict) or not isinstance(value.get("versions"), dict):
            raise ValueError("El manifiesto histórico no tiene un mapa de versiones válido.")
        write_manifest(path, value)
    return path
