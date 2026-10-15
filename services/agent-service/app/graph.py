import asyncio
import os
from datetime import date, timedelta

from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

MCP_URL = os.environ.get("MCP_URL", "http://finance-mcp-server:8002/mcp")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()   # "gemini" or "ollama"

# Gemini. "gemini-flash-latest" is an alias Google keeps pointing at its newest Flash model,
# so you don't have to chase model names. Set GEMINI_MODEL to pin a specific one.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

# If the main model is overloaded (HTTP 503) or unavailable, the agent automatically retries the
# same request with this lighter, cheaper model. Set it to an empty string to turn that off.
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

# Ollama (local alternative: your data never leaves your PC)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

SYSTEM_PROMPT = """You are SmartSpend, a personal finance assistant for an Indian user. All amounts are in Indian rupees (Rs).

Today's date is {today}. The current month is {current_month} and the previous month is {previous_month}.
When the user says "this month" use {current_month}; for "last month" use {previous_month}.
Always pass months to tools in YYYY-MM format.

Rules:
- Never guess or invent numbers. Use the tools to get real data, then answer from the tool results only.
- To explain why spending changed, use compare_months, then summarize the biggest category changes with percentages.
- For unusual or suspicious spending, use detect_unusual_expenses and repeat the reason it gives.
- For budgets, use get_budget_status to check them and create_budget to set them.
- If a tool returns an error, read the message, fix your input and try again once. If it still fails, tell the user plainly.
- If the data is empty for a month, say there are no transactions for that month.
- Keep answers short and clear. Use bullet points for comparisons.
- After explaining a change, offer to list the individual transactions behind it."""


def describe_llm() -> str:
    if LLM_PROVIDER == "gemini":
        fallback = f" (fallback: {GEMINI_FALLBACK_MODEL})" if GEMINI_FALLBACK_MODEL else ""
        return f"gemini:{GEMINI_MODEL}{fallback}"
    return f"{LLM_PROVIDER}:{OLLAMA_MODEL}"


def make_llm(model: str | None = None):
    """Create the chat model for the configured provider."""
    if LLM_PROVIDER == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Put it in smartspend/.env (see the setup steps), "
                "then run: docker compose up -d --force-recreate agent-service"
            )
        # max_retries counts attempts including the first one; timeout is in seconds.
        # 3 attempts x 25 s per model, times 2 models, stays under nginx's 180 s limit.
        return ChatGoogleGenerativeAI(
            model=model or GEMINI_MODEL, api_key=api_key, temperature=0, max_retries=3, timeout=25
        )
    if LLM_PROVIDER == "ollama":
        return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    raise RuntimeError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'gemini' or 'ollama'.")


def make_llm_with_tools(tools):
    """The main model, plus (for Gemini) an automatic fallback model for when it is overloaded."""
    primary = make_llm().bind_tools(tools)
    use_fallback = LLM_PROVIDER == "gemini" and GEMINI_FALLBACK_MODEL and GEMINI_FALLBACK_MODEL != GEMINI_MODEL
    if not use_fallback:
        return primary
    fallback = make_llm(GEMINI_FALLBACK_MODEL).bind_tools(tools)
    return primary.with_fallbacks([fallback])


def system_message() -> SystemMessage:
    today = date.today()
    previous = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    return SystemMessage(content=SYSTEM_PROMPT.format(
        today=today.isoformat(),
        current_month=today.strftime("%Y-%m"),
        previous_month=previous,
    ))


async def load_tools(retries: int = 30, delay: float = 2.0):
    """Connect to the Finance MCP server and fetch its tools.

    The MCP server may still be starting when this container starts, so retry for a while.
    """
    client = MultiServerMCPClient({"finance": {"url": MCP_URL, "transport": "streamable_http"}})
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            return await client.get_tools()
        except Exception as exc:  # noqa: BLE001 - we retry on any connection problem
            last_error = exc
            await asyncio.sleep(delay)
    raise RuntimeError(f"Could not reach the MCP server at {MCP_URL}: {last_error}")


def build_graph(tools, llm=None):
    """The agent: a loop between a model node and a tool node.

        START -> agent --(wants a tool?)--> tools -> agent -> ... -> END
    """
    llm_with_tools = llm.bind_tools(tools) if llm else make_llm_with_tools(tools)

    async def agent(state: MessagesState):
        response = await llm_with_tools.ainvoke([system_message(), *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)   # tool call -> "tools", otherwise END
    builder.add_edge("tools", "agent")

    # MemorySaver remembers each conversation (thread) so follow-ups like "yes, show me" work.
    # It lives in memory, so conversations reset when the container restarts.
    return builder.compile(checkpointer=MemorySaver())