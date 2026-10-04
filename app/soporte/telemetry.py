"""Clientes explícitos y filtrado de todas las trazas del grafo."""

import os
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from .privacy import redact, mask_spans


@dataclass
class Telemetry:
    mode: str
    ls: object = None
    lf: object = None
    tracer: object = None
    handler: object = None

    @classmethod
    def open(cls, mode):
        if mode not in {"off", "langsmith", "langfuse", "both"}:
            raise ValueError("Modo de observabilidad inválido")
        # Una sola vía de instrumentación: callbacks explícitos, no auto-tracing adicional.
        os.environ["LANGSMITH_TRACING"] = "false"
        obj = cls(mode)
        if mode in {"langsmith", "both"}:
            from langsmith import Client
            from langchain_core.tracers.langchain import LangChainTracer

            if not os.getenv("LANGSMITH_API_KEY"):
                raise ValueError("Falta LANGSMITH_API_KEY")
            obj.ls = Client(
                hide_inputs=redact, hide_outputs=redact, hide_metadata=redact
            )
            obj.tracer = LangChainTracer(
                client=obj.ls,
                project_name=os.getenv("LANGSMITH_PROJECT", "thepower-clase-2"),
            )
        if mode in {"langfuse", "both"}:
            from langfuse import Langfuse
            from langfuse.langchain import CallbackHandler

            if not all(
                os.getenv(k) for k in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
            ):
                raise ValueError("Faltan claves LANGFUSE_*")
            obj.lf = Langfuse(
                mask=redact_adapter,
                mask_otel_spans=mask_spans,
                environment="thepower-aula",
                timeout=20,
            )
            obj.handler = CallbackHandler(public_key=os.getenv("LANGFUSE_PUBLIC_KEY"))
        return obj

    @contextmanager
    def turn(self, *, thread_id, model_id, prompt_meta, scenario, query_id=None):
        from langsmith import tracing_context

        query_id = query_id or str(uuid.uuid4())
        callbacks = [c for c in [self.tracer, self.handler] if c is not None]
        meta = {
            "query_id": query_id,
            "thread_id": thread_id,
            "model": model_id,
            "scenario": scenario,
            **prompt_meta,
        }
        config = {
            "configurable": {"thread_id": thread_id},
            "run_id": uuid.UUID(query_id),
            "run_name": "thepower-soporte",
            "metadata": meta,
            "tags": ["thepower", "soporte", scenario],
            "callbacks": callbacks,
            "recursion_limit": 12,
        }
        if self.lf:
            from langfuse import propagate_attributes

            lf_ctx = propagate_attributes(
                session_id=thread_id,
                user_id="alumno-ficticio",
                tags=["thepower", scenario],
            )
        else:
            lf_ctx = nullcontext()
        try:
            with tracing_context(enabled=self.ls is not None, client=self.ls), lf_ctx:
                yield config
        finally:
            self.flush()

    def flush(self):
        if self.tracer:
            self.tracer.wait_for_futures()
        if self.ls:
            self.ls.flush(timeout=20)
        if self.lf:
            self.lf.flush()

    def close(self):
        try:
            self.flush()
        finally:
            if self.lf:
                self.lf.shutdown()
            if self.ls:
                self.ls.close(timeout=20)


def redact_adapter(*, data, **kwargs):
    return redact(data)
