"""Tiny MCP client: connects to the server, lists its tools and calls a few.

This is the same thing the LangGraph agent will do in Step 5.
"""
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://localhost:8002/mcp"


async def main():
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:")
            for tool in tools.tools:
                print(f"  - {tool.name}")

            print("\nget_monthly_summary(2026-10):")
            result = await session.call_tool("get_monthly_summary", {"month": "2026-10"})
            print(json.dumps(json.loads(result.content[0].text), indent=2))

            print("\ncompare_months(2026-10 vs 2026-09):")
            result = await session.call_tool(
                "compare_months", {"month": "2026-10", "previous_month": "2026-09"}
            )
            print(json.dumps(json.loads(result.content[0].text), indent=2))

            print("\ndetect_unusual_expenses(2026-10):")
            result = await session.call_tool("detect_unusual_expenses", {"month": "2026-10"})
            print(json.dumps(json.loads(result.content[0].text), indent=2))
            
            print("\ncreate_budget calls:")
            for category, limit in [("Food", 1000), ("Shopping", 40000), ("Groceries", 5000), ("Total", 50000)]:
                result = await session.call_tool("create_budget", {"category": category, "monthly_limit": limit})
                print(" ", json.loads(result.content[0].text))

            print("\nget_budget_status(2026-10):")
            result = await session.call_tool("get_budget_status", {"month": "2026-10"})
            for b in json.loads(result.content[0].text)["budgets"]:
                print(f"  {b['category']:10s} spent {b['spent']:>9,.1f} of {b['monthly_limit']:>9,.0f}  ({b['percent_used']}%)  {b['status']}")

asyncio.run(main())