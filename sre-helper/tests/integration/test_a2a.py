# Use importlib to load o11y-agent app without path conflicts and hyphen issues
import importlib.util
import os
from unittest.mock import patch

import pytest
from google.genai import types

# Removed legacy mocks that polluted global state

current_dir = os.path.dirname(os.path.abspath(__file__))
o11y_agent_path = os.path.abspath(os.path.join(current_dir, "../../../o11y-agent/app/agent.py"))

spec = importlib.util.spec_from_file_location("o11y_agent_app", o11y_agent_path)
o11y_agent_module = importlib.util.module_from_spec(spec)

def mock_get_mcp_server(self, name):
    if "logging" in name:
        return {
            "displayName": "logging",
            "mcpServerId": "logging-id",
            "interfaces": [{"protocolBinding": "HTTP_JSON", "url": "https://logging.googleapis.com/mcp"}]
        }
    elif "trace" in name:
        return {
            "displayName": "trace",
            "mcpServerId": "trace-id",
            "interfaces": [{"protocolBinding": "HTTP_JSON", "url": "https://cloudtrace.googleapis.com/mcp"}]
        }
    elif "metrics" in name:
        return {
            "displayName": "metrics",
            "mcpServerId": "metrics-id",
            "interfaces": [{"protocolBinding": "HTTP_JSON", "url": "https://monitoring.googleapis.com/mcp"}]
        }
    return {}

def mock_mcp_tool():
    """A mock tool for testing."""
    return "Mocked response"

with patch("google.adk.integrations.agent_registry.agent_registry.AgentRegistry.get_mcp_server", mock_get_mcp_server), \
     patch("google.adk.integrations.agent_registry.agent_registry.AgentRegistry.get_mcp_toolset", lambda self, name: mock_mcp_tool):
    spec.loader.exec_module(o11y_agent_module)

o11y_app = o11y_agent_module.app

@pytest.mark.asyncio
async def test_a2a_communication(monkeypatch):
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from unittest.mock import AsyncMock, patch

    from google.adk.agents.base_agent import BaseAgent

    with patch("google.adk.integrations.agent_registry.AgentRegistry.get_remote_a2a_agent") as mock_get_agent:
        mock_agent = AsyncMock(spec=BaseAgent)
        mock_agent.name = "o11y_agent"
        mock_agent.agent_card = "https://placeholder.url/agent_card"
        mock_get_agent.return_value = mock_agent

        import importlib

        import app.agent
        importlib.reload(app.agent)
        # Using live model as requested
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        from app.agent import root_agent

        session_service = InMemorySessionService()
        session = session_service.create_session_sync(user_id="test_user", app_name="test")
        runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

        message = types.Content(
            role="user", parts=[types.Part.from_text(text="Investigate incident 123 using o11y_agent.")]
        )

        events = list(
            runner.run(
                new_message=message,
                user_id="test_user",
                session_id=session.id,
            )
        )

        print(f"Events yielded count: {len(events)}")
        for e in events:
            print(f"Event from {e.author}: {e.content}")
            if hasattr(e, 'error_message') and e.error_message:
                print(f"  Error: {e.error_message}")

        # Verify that the observability delegator was called by inspecting events
        has_call = False
        for e in events:
            if e.content and e.content.parts:
                for p in e.content.parts:
                    if p.function_call and p.function_call.name == "o11y_agent":
                        has_call = True
                        break
                if has_call:
                    break

        assert has_call, "The observability delegator was not called"

# MCP tests moved to test_mcp.py
