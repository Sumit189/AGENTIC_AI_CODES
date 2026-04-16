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

async def run_agent(feature_request: str):
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="github_agent_app",
        user_id="sumit"
    )

    runner = Runner(
        agent=root_agent,
        app_name="github_agent_app",
        session_service=session_service,
    )

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

if __name__ == "__main__":
    feature_request = """
    Repository: [Link to your GitHub repository]
    
    Feature request: Add a divide function to mcp_server.py
    It should take two numbers and return their quotient.
    Follow the same style as the existing add and subtract functions.
    """
    asyncio.run(run_agent(feature_request))