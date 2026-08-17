"""Calculator agent from the LangGraph Graph API quickstart."""

from __future__ import annotations

import hashlib
import operator
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

# Same .env as the course scripts (OPENROUTER_API_KEY at the repo root).
# This isolated demo does not use LangSmith; the course .env may enable it.
# load_dotenv must run before any langfuse import (client reads env at init).
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
os.environ["LANGSMITH_TRACING"] = "false"
os.environ.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
# langfuse-cli still reads LANGFUSE_HOST; keep it aligned with the SDK var.
os.environ.setdefault("LANGFUSE_HOST", os.environ["LANGFUSE_BASE_URL"])
os.environ.setdefault("OTEL_SERVICE_NAME", "langgraph-agent")

_DEMO_USER = "langgraph-agent-demo"
_SESSION_ID = "langgraph-agent-demo"

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def _openrouter_base_url() -> str:
    base_url = (os.environ.get("OPENROUTER_BASE_URL") or _DEFAULT_BASE_URL).strip()
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return base_url.rstrip("/")


if not os.environ.get("OPENROUTER_API_KEY"):
    raise SystemExit(
        "Falta OPENROUTER_API_KEY. Pégala en el .env de la raíz del repo "
        "(igual que langgraph/02_tools.py)."
    )

MODELO = os.environ.get("OPENROUTER_MODEL", "").strip()
if not MODELO:
    raise SystemExit(
        "Falta OPENROUTER_MODEL en el .env de la raíz "
        "(p. ej. google/gemma-4-31b-it)."
    )

BASE_URL = _openrouter_base_url()
# OpenRouter upstream, e.g. Cerebras. Same pattern as langgraph/02_tools.py.
UPSTREAM = os.environ.get("OPENROUTER_PROVIDER", "").strip()
model_kwargs: dict = {"model": MODELO, "base_url": BASE_URL, "temperature": 0}
if UPSTREAM:
    model_kwargs["openrouter_provider"] = {"order": [UPSTREAM]}
# Client is always OpenRouter. Base URL, model, and upstream come from .env.
model = ChatOpenRouter(**model_kwargs)


@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or not."""
    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content=(
                            "You are a helpful assistant tasked with performing "
                            "arithmetic on a set of inputs."
                        )
                    )
                ]
                + state["messages"],
                config={"run_name": "generate-response"},
            )
        ],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def tool_node(state: MessagesState):
    """Performs the tool call."""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
    return {"messages": result}


def route_after_model(state: MessagesState) -> Literal["run-tools", END]:
    """Route to tools if the last model message requested a tool call."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "run-tools"
    return END


agent_builder = StateGraph(MessagesState)
agent_builder.add_node("decide-or-answer", llm_call)
agent_builder.add_node("run-tools", tool_node)
agent_builder.add_edge(START, "decide-or-answer")
agent_builder.add_conditional_edges(
    "decide-or-answer", route_after_model, ["run-tools", END]
)
agent_builder.add_edge("run-tools", "decide-or-answer")
agent = agent_builder.compile()


def _user_id() -> str:
    """16 hex of SHA-256. Never send an email or other PII as user_id."""
    return hashlib.sha256(_DEMO_USER.encode()).hexdigest()[:16]


def _last_ai_text(messages: list[AnyMessage]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue
        if getattr(message, "tool_calls", None):
            continue
        content = getattr(message, "content", "")
        return content if isinstance(content, str) else str(content)
    return ""


def main() -> None:
    if not os.environ.get("LANGFUSE_PUBLIC_KEY") or not os.environ.get(
        "LANGFUSE_SECRET_KEY"
    ):
        raise SystemExit(
            "Falta LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY en el .env de la raíz."
        )

    # Import after load_dotenv so the client picks up LANGFUSE_* from .env.
    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    langfuse = get_client()
    if not langfuse.auth_check():
        raise SystemExit(
            "Langfuse auth failed. Check LANGFUSE_PUBLIC_KEY, "
            "LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL."
        )

    question = "Add 3 and 4."
    handler = CallbackHandler()
    hashed = _user_id()
    print(
        f"provider=openrouter base_url={BASE_URL} model={MODELO}"
        + (f" upstream={UPSTREAM}" if UPSTREAM else "")
    )
    print(f"langfuse session_id={_SESSION_ID} user_id={hashed}")

    try:
        with langfuse.start_as_current_observation(
            as_type="agent",
            name="solve-arithmetic",
            input=question,
        ) as span:
            with propagate_attributes(
                trace_name="solve-arithmetic",
                user_id=hashed,
                session_id=_SESSION_ID,
                tags=["langgraph-agent", "calculator"],
                environment="development",
                metadata={
                    "model": MODELO,
                    "provider": "openrouter",
                    "upstream": UPSTREAM or None,
                },
            ):
                result = agent.invoke(
                    {"messages": [HumanMessage(content=question)]},
                    config={
                        "callbacks": [handler],
                        "run_name": "handle-calculator-turn",
                        "tags": ["langgraph-agent", "calculator"],
                        "metadata": {
                            "model": MODELO,
                            "provider": "openrouter",
                        },
                    },
                )
            answer = _last_ai_text(result["messages"])
            span.update(output=answer)
            span.score_trace(
                name="answer_present",
                value=1.0 if answer.strip() else 0.0,
                data_type="NUMERIC",
            )
    finally:
        # Short CLI: without shutdown() the batch is dropped on exit.
        langfuse.shutdown()

    for message in result["messages"]:
        message.pretty_print()

    trace_id = getattr(handler, "last_trace_id", None)
    host = os.environ["LANGFUSE_BASE_URL"].rstrip("/")
    if trace_id:
        print(f"langfuse trace: {host}/trace/{trace_id}")


if __name__ == "__main__":
    main()
