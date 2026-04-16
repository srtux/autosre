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

import pytest


def test_get_app_returns_adk_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ``get_app()`` lazily constructs an AdkApp subclass.

    The module must import cleanly with no network side effects, and
    ``get_app()`` must build the wrapper on first call.
    """
    pytest.importorskip("a2a")
    pytest.importorskip("vertexai")
    pytest.importorskip("google.adk")

    # ``AdkApp.__init__`` reads ``vertexai.init`` global config, so the
    # project must be set before ``get_app()`` constructs the wrapper.
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    from vertexai.agent_engines.templates.adk import AdkApp

    # Stub out the lazy agent builder so we don't hit the registry or network.
    from sre_helper import agent as agent_module

    fake_agent = MagicMock(name="fake_agent")
    monkeypatch.setattr(agent_module, "_build_agent", lambda: fake_agent)
    # Reset cached singleton so the test is hermetic.
    monkeypatch.setattr(agent_module, "_app", None)

    resolved = agent_module.get_app()
    assert isinstance(resolved, AdkApp)
    # Calling again returns the cached instance.
    assert agent_module.get_app() is resolved
