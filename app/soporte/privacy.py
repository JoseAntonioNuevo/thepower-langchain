"""Filtrado didáctico antes de exportar. No es un detector universal de PII."""

import re
from copy import deepcopy
from typing import Any

EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
MARKER = re.compile(r"SECRET_DEMO_[A-Za-z0-9_-]+")
SENSITIVE = re.compile(r"api[_-]?key|password|authorization|secret|token", re.I)


def redact(data: Any) -> Any:
    # LangSmith recibe mensajes Pydantic antes de serializarlos al wire format.
    # Una copia del objeto sin recorrer sus campos dejaría el contenido intacto.
    if hasattr(data, "model_dump"):
        return redact(data.model_dump(mode="json"))
    if isinstance(data, str):
        return MARKER.sub("[SECRETO_OCULTO]", EMAIL.sub("[EMAIL_OCULTO]", data))
    if isinstance(data, dict):
        return {
            k: "[VALOR_OCULTO]"
            if SENSITIVE.search(str(k)) and not str(k).endswith("_tokens")
            else redact(v)
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [redact(x) for x in data]
    return deepcopy(data)


def mask_spans(*, params):
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    patches = {}
    for identifier, span in params.spans.items():
        changed = {k: redact(v) for k, v in span.attributes.items() if redact(v) != v}
        if changed:
            patches[identifier] = OtelSpanPatch(set_attributes=changed)
    return MaskOtelSpansResult(span_patches=patches)
