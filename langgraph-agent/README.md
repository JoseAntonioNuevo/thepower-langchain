# LangGraph Python quickstart

Calculator agent from the official [LangGraph Graph API quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart). Isolated from the course `app/` graph.

Client is always OpenRouter (`ChatOpenRouter`). Base URL and model come from the repo-root `.env`. The client uses `reasoning.effort` `none` and `service_tier` `priority` (fast mode):

```
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-6-luna
```

## Setup

```bash
cd langgraph-agent
python3 -m venv .venv   # 3.10+; this repo used 3.12
source .venv/bin/activate
pip install -r requirements.txt
```

Put `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_MODEL` in the repo-root `.env`.

Tracing uses Langfuse v4 (`CallbackHandler` + `propagate_attributes`). Also set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL` in that same `.env`. LangSmith stays off for this demo.

## Run

```bash
python agent.py
```

Invokes the graph with “Add 3 and 4.” The CLI prints a Langfuse trace URL. In the UI, filter by session `langgraph-agent-demo` or tag `calculator`.
