"""Configuración explícita; la consola decide cuándo cargar el entorno."""

from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "openai/gpt-6-luna"


@dataclass(frozen=True)
class Settings:
    model_id: str
    base_url: str
    timeout_s: float = 45.0
    max_tokens: int = 600


def settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    return Settings(
        os.getenv("MODEL_ID") or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL,
        os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
    )


def make_model(cfg: Settings):
    if not os.getenv("OPENROUTER_API_KEY"):
        raise ValueError(
            "Falta OPENROUTER_API_KEY; configura .env sin compartir la clave."
        )
    from langchain_openrouter import ChatOpenRouter
    from openrouter import OpenRouter

    # El adaptador recibe milisegundos. Inyectar SDK evita su retry por defecto.
    client = OpenRouter(
        api_key=os.environ["OPENROUTER_API_KEY"],
        server_url=cfg.base_url,
        timeout_ms=int(cfg.timeout_s * 1000),
        retry_config=None,
    )
    return ChatOpenRouter(
        model=cfg.model_id,
        base_url=cfg.base_url,
        temperature=0,
        client=client,
        reasoning={"effort": "none"},
        model_kwargs={"service_tier": "priority"},
        max_tokens=cfg.max_tokens,
        timeout=int(cfg.timeout_s * 1000),
        max_retries=0,
    )


class LazyModel:
    """Compatibilidad de demos antiguas: crear el cliente solo en invoke/stream."""

    def __init__(self, tools=None):
        self.tools = tools
        self._model = None

    def bind_tools(self, tools):
        return LazyModel(tools)

    def _get(self):
        if self._model is None:
            base = make_model(settings())
            self._model = (
                base.bind_tools(self.tools) if self.tools is not None else base
            )
        return self._model

    def invoke(self, *args, **kwargs):
        return self._get().invoke(*args, **kwargs)

    def stream(self, *args, **kwargs):
        return self._get().stream(*args, **kwargs)
