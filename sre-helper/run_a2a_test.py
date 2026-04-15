import os
import sys

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# Setup environment
os.environ["LOCAL_A2A"] = "True"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent import root_agent  # noqa: E402


def run_test():
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="local_user", app_name="a2a_test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="a2a_test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Investigate incident 123. Ask o11y_agent to check logs.")]
    )

    print("--- Running SRE Helper A2A Test ---")
    events = list(
        runner.run(
            new_message=message,
            user_id="local_user",
            session_id=session.id,
        )
    )

    for e in events:
        print(f"Event from {e.author}: {e.content}")
        if hasattr(e, 'error_message') and e.error_message:
            print(f"  Error: {e.error_message}")

if __name__ == "__main__":
    run_test()
