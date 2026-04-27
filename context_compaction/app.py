import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from google.genai import types

load_dotenv()
### Before starting make sure to set up your .env file with the following variables:
# GOOGLE_API_KEY

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

COMPACTION_THRESHOLD = 3

def should_compact(history: list) -> bool:
    """Check if history has crossed the threshold."""
    return len(history) >= COMPACTION_THRESHOLD


import asyncio
import random
from google.genai.errors import ServerError

async def generate_with_retry(client, contents, config=None, retries=10):
    for attempt in range(retries):
        try:
            return client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=contents,
                config=config
            )
        except ServerError as e:
            if attempt == retries - 1:
                raise

            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)

        except Exception as e:
            # Non-retryable errors
            raise e


async def compact_history(history):
    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['parts'][0]}"
        for msg in history
    )
    summary_prompt = f"""Summarize this conversation in 3-4 lines.
Keep all important facts — names, preferences, key decisions.
Be concise.

Conversation:
{conversation_text}
"""
    response = await generate_with_retry(
        client,
        contents=summary_prompt,
    )
    summary = response.text
    print(f"\n[Summary]: {summary}\n")
    compacted = [
        {"role": "user",  "parts": [f"[Conversation summary]: {summary}"]},
        {"role": "model", "parts": ["Understood. I have context from our previous conversation."]}
    ] + history[-2:]

    print(f"\n[Compacted {len(history)} → {len(compacted)} messages]")
    return compacted

async def chat_with_manual_compaction():
    history = []
    print("=== TEST ===\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        history.append({"role": "user", "parts": [user_input]})

        if should_compact(history):
            history = await compact_history(history)

        response = await generate_with_retry(
        client,
        contents=[
            genai_types.Content(
                role=msg["role"],
                parts=[genai_types.Part.from_text(text=msg["parts"][0])]
            )
            for msg in history
        ],
        config=genai_types.GenerateContentConfig(
            system_instruction="You are a helpful personal assistant. Remember everything the user tells you. Reply one liner message only."
        )
    )

        reply = response.text
        history.append({"role": "model", "parts": [reply]})
        print(f"Agent: {reply}")
        print(f"[History: {len(history)} messages]\n")
        print("=== ===\n")
async def main():
    await chat_with_manual_compaction()


if __name__ == "__main__":
    asyncio.run(main())