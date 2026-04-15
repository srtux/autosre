import os

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentSkill, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from vertexai.preview.reasoning_engines.templates.a2a import A2aAgent, create_agent_card

# load_dotenv is safe at import time: it only reads a file if one exists and
# never touches the network. Anything that hits auth, the registry, or the
# MCP servers is deferred into the lazy builder below so that Vertex AI Agent
# Engine can import this module during cold start without tripping on missing
# env vars or permissions that are only ready once the runtime is fully up.
load_dotenv()


# Default MCP server resource names. Each can be overridden via env var so
# the same image can target different projects without code changes.
_DEFAULT_LOGGING_MCP_SERVER = (
    "projects/agent-o11y/locations/global/mcpServers/"
    "agentregistry-00000000-0000-0000-8775-8836af20f907"
)
_DEFAULT_TRACE_MCP_SERVER = (
    "projects/agent-o11y/locations/global/mcpServers/"
    "agentregistry-00000000-0000-0000-fc11-8c59ea75c8fb"
)
_DEFAULT_MONITORING_MCP_SERVER = (
    "projects/agent-o11y/locations/global/mcpServers/"
    "agentregistry-00000000-0000-0000-c0af-2a60b0a7228f"
)
_DEFAULT_ERROR_REPORTING_MCP_SERVER = (
    "projects/agent-o11y/locations/global/mcpServers/"
    "agentregistry-00000000-0000-0000-f5e4-899818873ec1"
)


_ops_agent: Agent | None = None


def _resolve_project_id() -> str:
    """Resolve the Google Cloud project ID without importing google.auth at
    module load time.

    Reads GOOGLE_CLOUD_PROJECT first, then falls back to
    google.auth.default(). Raises if neither is available.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        return project_id

    import google.auth  # deferred: keep module import auth-free

    _, project_id = google.auth.default()
    if not project_id:
        raise RuntimeError(
            "Could not resolve GOOGLE_CLOUD_PROJECT. Set it explicitly via "
            "env var or ensure application default credentials expose a project."
        )
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    return project_id


def get_ops_agent() -> Agent:
    """Lazily build and cache the observability ADK agent.

    All external dependencies (google.auth, AgentRegistry, MCP toolsets) are
    resolved on the first call instead of at module import. This keeps Agent
    Engine cold-start imports side-effect free.
    """
    global _ops_agent
    if _ops_agent is not None:
        return _ops_agent

    project_id = _resolve_project_id()
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

    registry = AgentRegistry(project_id=project_id, location="global")

    logging_mcp_server = os.environ.get(
        "LOGGING_MCP_SERVER_ID", _DEFAULT_LOGGING_MCP_SERVER
    )
    trace_mcp_server = os.environ.get(
        "TRACE_MCP_SERVER_ID", _DEFAULT_TRACE_MCP_SERVER
    )
    monitoring_mcp_server = os.environ.get(
        "MONITORING_MCP_SERVER_ID", _DEFAULT_MONITORING_MCP_SERVER
    )
    error_reporting_mcp_server = os.environ.get(
        "ERROR_REPORTING_MCP_SERVER_ID", _DEFAULT_ERROR_REPORTING_MCP_SERVER
    )

    print(
        "Initializing logging agent with MCP servers: "
        f"{logging_mcp_server}, {trace_mcp_server}, "
        f"{monitoring_mcp_server}, {error_reporting_mcp_server}"
    )

    _ops_agent = Agent(
        name="OpsAgent",
        model=Gemini(
            model="gemini-2.5-flash",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction="""
        You are a specialist in observability (logs, traces, metrics, and error reports). Use your tools to investigate production issues.
        You can query logs, view traces, check metrics, and list error reports.
        When querying logs using the MCP, use the Logging Query Language. Remember that Boolean operators (AND, OR, NOT) must be capitalized.
        You can filter by fields like resource.type, severity, and textPayload. Example: `resource.type=\"gce_instance\" AND severity>=ERROR`.
        """,
        tools=[
            registry.get_mcp_toolset(logging_mcp_server),
            registry.get_mcp_toolset(trace_mcp_server),
            registry.get_mcp_toolset(monitoring_mcp_server),
            registry.get_mcp_toolset(error_reporting_mcp_server),
        ],
    )
    return _ops_agent


class O11yAgentExecutor(AgentExecutor):
    """Executor for O11y Agent that wraps the ADK Agent."""

    def __init__(self):
        """Initialize the executor."""
        self._runner: Runner | None = None

    def _init_adk(self) -> Runner:
        """Build the Runner once on first execute to match the canonical
        A2aAgent executor pattern. Avoids rebuilding the agent/runner/session
        services on every request."""
        if self._runner is None:
            ops_agent = get_ops_agent()
            self._runner = Runner(
                app_name=ops_agent.name,
                agent=ops_agent,
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
            )
        return self._runner

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if not context.message:
            raise ValueError("Message should be present in request context")

        query = context.get_user_input()
        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if context.call_context:
            user_id = context.call_context.user.user_name
        else:
            user_id = "a2a_user"

        try:
            # Update status
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    "Processing request with O11y Agent...", task.context_id, task.id
                ),
            )

            runner = self._init_adk()

            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=user_id,
                state={},
                session_id=task.context_id,
            )

            content = types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            )

            print(f"Executing O11y Agent with query: {query}")

            response_text = ""
            async for event in runner.run_async(
                user_id=user_id, session_id=session.id, new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text
                            # Stream text to event queue
                            await event_queue.enqueue_event(
                                new_agent_text_message(
                                    part.text, task.context_id, task.id
                                )
                            )

            # Add response as artifact
            await updater.add_artifact(
                [Part(root=TextPart(text=response_text))],
                name="response",
            )

            await updater.complete()

        except Exception as e:
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(f"Error: {e!s}", task.context_id, task.id),
                final=True,
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


# Define skills
skill = AgentSkill(
    id="investigate_logs",
    name="Investigate Logs",
    description="Query and analyze logs using Logging Query Language",
    tags=["logging", "observability"],
    examples=["Show me errors for resource.type=gce_instance"],
)

# Create agent card
card = create_agent_card(
    agent_name="o11y_agent",
    description="Agent for investigating logs and observability data",
    skills=[skill],
)

# Instantiate A2aAgent
app = A2aAgent(
    agent_card=card,
    agent_executor_builder=O11yAgentExecutor,
)
