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

import pytest


def test_get_app_returns_a2a_app() -> None:
    """Ensure app exports stay compatible with Agent Engine wrappers."""
    pytest.importorskip("a2a")
    pytest.importorskip("vertexai")

    from vertexai.preview.reasoning_engines.templates.a2a import A2aAgent

    from app.agent import app, get_app

    resolved = get_app()
    assert resolved is app
    assert isinstance(resolved, A2aAgent)
