"""Langfuse v4 tracing for the 04 TUI. One trace per turn; session = thread_id."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

# Same classroom placeholder as observability/_comun.py. Never a real email.
_USER_PLACEHOLDER = "alumno-demo-thepower"


def langfuse_enabled() -> bool:
    return bool(
        os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        and os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    )


def user_id_hash() -> str:
    return hashlib.sha256(_USER_PLACEHOLDER.encode()).hexdigest()[:16]


def _prepare_env() -> None:
    os.environ.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    os.environ.setdefault("LANGFUSE_HOST", os.environ["LANGFUSE_BASE_URL"])
    os.environ.setdefault("OTEL_SERVICE_NAME", "thepower-chatbot")


def _last_ai_text(values: dict[str, Any]) -> str:
    draft = str(values.get("draft") or "").strip()
    if draft:
        return draft
    for mensaje in reversed(values.get("messages") or []):
        if getattr(mensaje, "type", None) != "ai":
            continue
        if getattr(mensaje, "tool_calls", None):
            continue
        content = getattr(mensaje, "content", "")
        if isinstance(content, str) and content.strip():
            return content
    return ""


def respuesta_del_grafo(graph: Any, config: dict[str, Any]) -> str:
    """Final assistant text from the checkpointer after a turn."""
    try:
        snap = graph.get_state(config)
    except Exception:
        return ""
    values = getattr(snap, "values", None) or {}
    if not isinstance(values, dict):
        return ""
    return _last_ai_text(values)


@contextmanager
def trace_chat_turn(
    texto: str,
    *,
    thread_id: str,
    modelo: str,
    config: dict[str, Any],
) -> Iterator[tuple[dict[str, Any], Callable[[str], None]]]:
    """Yield invoke config + output setter. No-op if Langfuse keys are missing."""
    def _noop(_output: str) -> None:
        return None

    if not langfuse_enabled():
        yield config, _noop
        return

    _prepare_env()
    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    langfuse = get_client()
    handler = CallbackHandler()
    merged: dict[str, Any] = {
        **config,
        "callbacks": [*(config.get("callbacks") or []), handler],
        "run_name": "handle-chat-turn",
        "tags": list({*(config.get("tags") or []), "chatbot", "tui"}),
        "metadata": {
            **(config.get("metadata") or {}),
            "model": modelo,
            "provider": "openrouter",
        },
    }
    output = ""

    def set_output(text: str) -> None:
        nonlocal output
        output = text

    try:
        with langfuse.start_as_current_observation(
            as_type="agent",
            name="handle-chat-turn",
            input=texto,
        ) as span:
            with propagate_attributes(
                trace_name="handle-chat-turn",
                user_id=user_id_hash(),
                session_id=thread_id,
                tags=["chatbot", "tui"],
                environment="development",
                metadata={"model": modelo, "provider": "openrouter"},
            ):
                yield merged, set_output
            if output:
                span.update(output=output)
    finally:
        # Long-lived TUI: flush each turn; shutdown happens when the TUI exits.
        langfuse.flush()


def shutdown_langfuse() -> None:
    if not langfuse_enabled():
        return
    _prepare_env()
    from langfuse import get_client

    get_client().shutdown()
