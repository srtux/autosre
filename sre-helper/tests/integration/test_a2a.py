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

import importlib
import asyncio
from unittest.mock import AsyncMock

import pytest


def test_a2a_wrapper_uses_local_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """LOCAL_A2A=True should route through the SDK A2A client path."""
    pytest.importorskip("a2a")
    pytest.importorskip("vertexai")

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("LOCAL_A2A", "True")

    import app.agent

    importlib.reload(app.agent)

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeResolver:
        def __init__(self, httpx_client, base_url):
            self.base_url = base_url

        async def get_agent_card(self):
            return {"name": "o11y"}

    class FakeA2AClient:
        def __init__(self, httpx_client, agent_card):
            self.agent_card = agent_card

        async def send_message(self, request):
            return {"ok": True, "transport": "local", "request_id": request.id}

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("a2a.client.card_resolver.A2ACardResolver", FakeResolver)
    monkeypatch.setattr("a2a.client.A2AClient", FakeA2AClient)

    wrapped = app.agent.make_a2a_wrapper()
    response = asyncio.run(wrapped("check local"))
    assert "local" in str(response)


def test_a2a_wrapper_uses_remote_rest_when_local_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOCAL_A2A=False should route through REST message:send and task polling."""
    pytest.importorskip("a2a")
    pytest.importorskip("vertexai")

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("LOCAL_A2A", "False")

    import app.agent

    importlib.reload(app.agent)

    class DummyCreds:
        token = "fake-token"

        def refresh(self, request):
            return None

    monkeypatch.setattr("google.auth.default", lambda: (DummyCreds(), "test-project"))

    send_response = AsyncMock()
    send_response.status_code = 200
    send_response.json.return_value = {"task": {"id": "task-123"}}
    send_response.raise_for_status.return_value = None

    poll_response = AsyncMock()
    poll_response.json.return_value = {
        "status": {"state": "TASK_STATE_COMPLETED"},
        "history": [{"role": "ROLE_AGENT", "content": [{"text": "remote complete"}]}],
    }
    poll_response.raise_for_status.return_value = None

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return send_response

        async def get(self, *args, **kwargs):
            return poll_response

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    wrapped = app.agent.make_a2a_wrapper()
    response = asyncio.run(wrapped("check remote"))
    assert response == "remote complete"
