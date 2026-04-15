# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import google.adk.agents
import google.adk.tools
import pytest
from google.adk.events.event import Event

from app.agent_engine_app import AgentEngineApp


class DummyGoogleAuth:
    def __init__(self, **kwargs):
        pass


google.adk.tools.GoogleAuth = getattr(google.adk.tools, "GoogleAuth", DummyGoogleAuth)


class DummyRemoteA2aAgent:
    def __init__(self, name="o11y_agent", **kwargs):
        self.name = name
        self.__name__ = name

    def __call__(self, *args, **kwargs):
        return "Mocked response"


google.adk.agents.RemoteA2aAgent = getattr(
    google.adk.agents, "RemoteA2aAgent", DummyRemoteA2aAgent
)


@pytest.fixture
def agent_app(monkeypatch: pytest.MonkeyPatch) -> "AgentEngineApp":
    """Fixture to create and set up AgentEngineApp instance"""
    # Set integration test flag to mock external services
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from unittest.mock import MagicMock

    mock_client = MagicMock()
    monkeypatch.setattr("google.cloud.logging.Client", lambda: mock_client)

    from app.agent_engine_app import agent_engine

    agent_engine.set_up()
    return agent_engine


@pytest.mark.asyncio
async def test_agent_stream_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Integration test for the agent stream query functionality.
    Tests that the agent returns valid streaming responses.
    """
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from unittest.mock import MagicMock

    mock_client = MagicMock()
    monkeypatch.setattr("google.cloud.logging.Client", lambda: mock_client)

    from unittest.mock import MagicMock, patch

    with patch(
        "google.adk.integrations.agent_registry.AgentRegistry.get_remote_a2a_agent"
    ) as mock_get_agent:
        mock_get_agent.return_value = DummyRemoteA2aAgent(name="o11y_agent")
        import importlib

        import app.agent
        import app.agent_engine_app

        importlib.reload(app.agent)
        importlib.reload(app.agent_engine_app)
        from app.agent import root_agent
        from app.agent_engine_app import agent_engine

    from google.adk.models import Gemini
    from google.genai import types

    from app.agent_engine_app import agent_engine

    root_agent.model = Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    )

    agent_engine.set_up()
    message = "Hi!"
    events = []
    async for event in agent_engine.async_stream_query(message=message, user_id="test"):
        events.append(event)
    assert len(events) > 0, "Expected at least one chunk in response"

    # Check for valid content in the response
    has_text_content = False
    for event in events:
        validated_event = Event.model_validate(event)
        content = validated_event.content
        if (
            content is not None
            and content.parts
            and any(part.text for part in content.parts)
        ):
            has_text_content = True
            break

    assert has_text_content, "Expected at least one event with text content"


def test_agent_feedback(agent_app: "AgentEngineApp") -> None:
    """
    Integration test for the agent feedback functionality.
    Tests that feedback can be registered successfully.
    """
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "user_id": "test-user-456",
        "session_id": "test-session-456",
    }

    # Should not raise any exceptions
    agent_app.register_feedback(feedback_data)

    # Test invalid feedback
    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",  # Score must be numeric
            "text": "Bad feedback",
            "user_id": "test-user-789",
            "session_id": "test-session-789",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
