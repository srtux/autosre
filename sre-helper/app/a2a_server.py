import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("LOCAL_A2A", "True")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

import app_utils.config  # noqa: E402

app_utils.config.LOCAL_A2A = app_utils.config.is_local_a2a()

from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402
from google.adk.agents import Agent  # noqa: E402
from google.adk.models import Gemini  # noqa: E402

from agent import make_a2a_wrapper  # noqa: E402

o11y_agent = make_a2a_wrapper()

agent = Agent(
    name="sre_helper",
    model=Gemini(model="gemini-2.5-flash"),
    instruction="You are the orchestrator for SRE incidents. Gather incident details and delegate investigation to o11y_agent.",
    tools=[o11y_agent],
)

# Export as A2A app
a2a_app = to_a2a(agent, port=10001)
