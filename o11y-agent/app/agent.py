from google.adk.agents import Agent, ParallelAgent

from google.adk.models import Gemini
from google.genai import types
from google.adk.integrations.agent_registry import AgentRegistry


import os
import google.auth
from dotenv import load_dotenv

load_dotenv()

# Use environment variables loaded from .env, fallback to default auth if not set
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not project_id:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

registry = AgentRegistry(project_id=project_id, location="global")




# Define sub-agents with MCP tools

logging_mcp_server = os.environ.get(
    "LOGGING_MCP_SERVER_ID",
    f"projects/{project_id}/locations/global/mcpServers/agentregistry-00000000-0000-0000-8775-8836af20f907"
)

logging_agent = Agent(
    name="LoggingAgent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a specialist in analyzing logs. Use your tools to investigate log data. When querying logs using the MCP, use the Logging Query Language. Remember that Boolean operators (AND, OR, NOT) must be capitalized. You can filter by fields like resource.type, severity, and textPayload. Example: `resource.type=\"gce_instance\" AND severity>=ERROR`.",
    tools=[registry.get_mcp_toolset(logging_mcp_server)],
)

# Wrap in ParallelAgent

observability_agent = ParallelAgent(
    name="o11y_agent",
    sub_agents=[logging_agent],
)

app = observability_agent
root_agent = observability_agent
