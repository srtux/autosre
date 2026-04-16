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

from unittest.mock import MagicMock

import pydantic
import pytest


@pytest.fixture
def agent_app(monkeypatch: pytest.MonkeyPatch):
    """Build an AgentEngineApp without any cloud calls."""
    pytest.importorskip("a2a")
    pytest.importorskip("vertexai")
    pytest.importorskip("google.adk")

    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")
    # ``AdkApp.__init__`` reads ``vertexai.init`` global config, so we must
    # set a project before ``get_app()`` constructs the wrapper.
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setattr("vertexai.init", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "vertexai.agent_engines.templates.adk.AdkApp.set_up",
        lambda self: None,
    )

    mock_client = MagicMock()
    monkeypatch.setattr("google.cloud.logging.Client", lambda: mock_client)

    # Avoid hitting the registry / network during agent construction.
    from sre_helper import agent as agent_module

    fake_agent = MagicMock(name="fake_agent")
    monkeypatch.setattr(agent_module, "_build_agent", lambda: fake_agent)
    monkeypatch.setattr(agent_module, "_app", None)

    agent_engine = agent_module.get_app()
    # Manually wire the logging client because ``set_up`` is stubbed above.
    agent_engine._logging_client = mock_client
    return agent_engine


def test_agent_feedback(agent_app) -> None:
    """Feedback should validate and be accepted by the Agent Engine wrapper."""
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "user_id": "test-user-456",
        "session_id": "test-session-456",
    }

    agent_app.register_feedback(feedback_data)

    with pytest.raises(pydantic.ValidationError):
        invalid_feedback = {
            "score": "invalid",
            "text": "Bad feedback",
            "user_id": "test-user-789",
            "session_id": "test-session-789",
        }
        agent_app.register_feedback(invalid_feedback)


def test_register_operations_includes_feedback(agent_app) -> None:
    """``register_feedback`` should be exposed as a sync operation."""
    operations = agent_app.register_operations()
    assert "register_feedback" in operations.get("", [])
