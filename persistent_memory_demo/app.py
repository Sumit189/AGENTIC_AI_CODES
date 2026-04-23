import asyncio
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from google.adk.sessions import DatabaseSessionService

load_dotenv()
### Before starting make sure to set up your .env file with the following variables:
# GITHUB_PERSONAL_ACCESS_TOKEN
# GOOGLE_API_KEY

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-github",
            ],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
            }
        )
    )
)

root_agent = LlmAgent(
    model=Gemini(model="gemini-3-flash-preview", retry_options=retry_config),
    name="github_agent",
    instruction="""You are a senior software engineer.
When given a feature request:
1. Read the relevant files in the repository using get_file_contents to understand the existing code structure
2. Create a new branch with a descriptive name using create_branch. If the branch already exists, add a timestamp suffix (e.g., feature/description-of-change-HHMMSS)
3. Make the required code changes using push_files
4. Open a pull request with a clear title and description using create_pull_request

Important notes:
- Keep code consistent with the existing style
- Write a clear PR description explaining what was changed and why
- Use conventional branch naming: feature/description-of-change
- If you get an error that a reference already exists, retry with a different branch name
""",
    tools=[toolset],
)

async def run_agent(feature_request: str, session: any, runner: Runner):
    content = types.Content(
        role="user",
        parts=[types.Part(text=feature_request)]
    )

    print(f"Feature Request: {feature_request}\n")
    print("Agent working...\n")

    async for event in runner.run_async(
        session_id=session.id,
        user_id=session.user_id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    print(f"Tool called: {part.function_call.name}")
        
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text if hasattr(event.content.parts[0], 'text') else None
            if text and text != "None":
                print(f"\nAgent: {text}")


async def main():
    DB_URL = "sqlite+aiosqlite:///./agent_memory.db"
    session_service = DatabaseSessionService(db_url=DB_URL)

    session = await session_service.create_session(
        app_name="github_agent_app",
        user_id="sumit"
    )
    APP_NAME  = "github_agent_app"
    USER_ID   = "sumit"
    SESSION_ID = "sumit_main_session"

    try:
        # Try to load existing session
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        if session:
            print(f"Loaded existing session — {len(session.events)} events in history")
    except Exception:
        pass

    if session is None:
        # Create new session if not found
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

    runner = Runner(
        agent=root_agent,
        app_name="github_agent_app",
        session_service=session_service,
    )

    # feature_request = """
    # Hi my name is Sumit, Say Hi
    # """
    # await run_agent(feature_request, session, runner)

    feature_request2 = """
    Whats my name that i told earlier?
    """
    await run_agent(feature_request2, session, runner)


if __name__ == "__main__":
    asyncio.run(main())