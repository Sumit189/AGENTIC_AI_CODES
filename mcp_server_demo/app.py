import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
import os

MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[MCP_SERVER_PATH],
        )
    )
)

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="calculator_agent",
    instruction="You are a calculator assistant. Use the available tools to perform calculations.",
    tools=[toolset],
)

async def run_agent(query: str):
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="calculator_app",
        user_id="user_1"
    )

    runner = Runner(
        agent=root_agent,
        app_name="calculator_app",
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    print(f"\nQuery: {query}")
    async for event in runner.run_async(
        session_id=session.id,
        user_id=session.user_id,
        new_message=content
    ):
        if event.is_final_response() and event.content:
            print(f"Answer: {event.content.parts[0].text}")

async def main():
    await run_agent("What is 25 multiplied by 4?")
    await run_agent("Add 100 and 250, then subtract 75 from the result.")
    await run_agent("What is 144 divided by 12?")

if __name__ == "__main__":
    asyncio.run(main())