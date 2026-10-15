import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from .graph import LLM_PROVIDER, build_graph, describe_llm, load_tools

MAX_STEPS = 12   # stops a confused model from looping between tools forever
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tools = await load_tools()
    app.state.tool_names = [t.name for t in tools]
    app.state.graph = build_graph(tools)
    yield


app = FastAPI(title="SmartSpend - Agent Service", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str = "default"   # use a different id to start a fresh conversation


class ToolCall(BaseModel):
    name: str
    args: dict


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[ToolCall]   # which tools the agent called for this message
    model: str | None = None     # which model wrote the answer (shows when the fallback was used)


def _explain(exc: Exception) -> tuple[int, str]:
    """Turn an LLM error into (HTTP status, a plain explanation of what to do about it)."""
    if LLM_PROVIDER != "gemini":
        return 502, f"Check that Ollama is running and that the model ({describe_llm()}) has been pulled."

    code = getattr(exc, "code", None)   # Google's errors carry the HTTP status code
    text = str(exc).lower()
    if code == 503 or "unavailable" in text or "high demand" in text:
        return 503, (
            "Google's Gemini service is overloaded right now. This is temporary and is not a problem "
            "with your setup. Wait a few seconds and send your message again."
        )
    if code == 429 or "resource_exhausted" in text or "quota" in text:
        return 429, "You reached the Gemini rate limit or quota. Wait a minute and try again."
    if code in (401, 403) or "api key" in text or "permission_denied" in text or "unauthenticated" in text:
        return 502, "Gemini rejected the API key. Check GOOGLE_API_KEY in smartspend/.env and recreate the container."
    if code == 404 or "not found" in text:
        return 502, f"Gemini could not find the model. Check the model names ({describe_llm()}) in docker-compose.yml."
    return 502, "The agent failed. If this keeps happening, run: docker compose logs agent-service"


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "llm": describe_llm(), "tools": request.app.state.tool_names}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    config = {"configurable": {"thread_id": payload.thread_id}, "recursion_limit": MAX_STEPS}
    try:
        result = await request.app.state.graph.ainvoke(
            {"messages": [HumanMessage(content=payload.message)]}, config
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Chat failed: %s", exc)
        status, explanation = _explain(exc)
        raise HTTPException(status_code=status, detail=f"{explanation} (details: {str(exc)[:200]})")

    messages = result["messages"]
    last_human = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    tools_used = [
        ToolCall(name=call["name"], args=call["args"])
        for m in messages[last_human + 1:]
        if isinstance(m, AIMessage)
        for call in m.tool_calls
    ]
    model = getattr(messages[-1], "response_metadata", {}).get("model_name") or None
    return ChatResponse(answer=_text(messages[-1].content), tools_used=tools_used, model=model)