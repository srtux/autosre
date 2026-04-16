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

"""SRE helper orchestrator agent.

This module is intentionally side-effect free at import time (see
``docs/deployment_patterns.md`` §3). ``load_dotenv`` is safe because it only
reads a file if one exists. Everything that touches auth, the Agent Registry,
or the network is deferred into :func:`_build_agent` / :func:`get_app`, so
that Vertex AI Agent Engine can import this module during cold-start without
tripping on missing env vars or permissions.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from .app_utils.telemetry import setup_telemetry
from .app_utils.typing import Feedback

load_dotenv()


_DEFAULT_REMOTE_AGENT = (
    "projects/agent-o11y/locations/us-central1/agents/"
    "agentregistry-00000000-0000-0000-9d8c-9b2c5ee73ba1"
)


# Lazy singletons. None until the first call to ``get_app()`` or ``_build_agent()``.
_agent: Any | None = None
_app: Any | None = None


def _resolve_project_id() -> str:
    """Resolve the Google Cloud project ID without importing google.auth at
    module load time."""
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


def _build_agent() -> Any:
    """Build and cache the root orchestrator ADK agent.

    All external dependencies (AgentRegistry, remote A2A resolution) are
    resolved on the first call instead of at module import. This keeps Agent
    Engine cold-start imports side-effect free.
    """
    global _agent
    if _agent is not None:
        return _agent

    # Deferred imports: these touch auth/registry state that may not be ready
    # at module load time on a cold-start container.
    from google.adk.agents import Agent
    from google.adk.integrations.agent_registry import AgentRegistry
    from google.adk.models import Gemini
    from google.genai import types

    project_id = _resolve_project_id()
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

    remote_agent_resource = os.environ.get(
        "O11Y_AGENT_RESOURCE", _DEFAULT_REMOTE_AGENT
    )

    registry = AgentRegistry(project_id=project_id, location=location)
    remote_agent = registry.get_remote_a2a_agent(remote_agent_resource)

    _agent = Agent(
        name="sre_helper",
        model=Gemini(
            model="gemini-2.5-flash",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=(
            "You are the orchestrator for SRE incidents. Gather incident "
            "details and delegate investigation to o11y_agent."
        ),
        sub_agents=[remote_agent],
    )
    return _agent


def _build_agent_engine_app_class() -> type:
    """Build the ``AgentEngineApp`` class lazily.

    ``vertexai`` imports may not be available at install time (and we do not
    want module import to pull them), so we construct the subclass on first
    call to :func:`get_app`.
    """
    from vertexai.agent_engines.templates.adk import AdkApp

    class AgentEngineApp(AdkApp):  # type: ignore[misc, valid-type]
        """AdkApp subclass that adds feedback logging for Agent Engine."""

        def set_up(self) -> None:
            """Configure telemetry and the Cloud Logging client on cold start."""
            setup_telemetry()

            from google.cloud import logging as google_cloud_logging

            self._logging_client = google_cloud_logging.Client()
            super().set_up()

        def register_feedback(self, feedback: dict[str, Any]) -> None:
            """Validate feedback and log it via Cloud Logging."""
            feedback_obj = Feedback.model_validate(feedback)
            try:
                logger = self._logging_client.logger("sre-helper")
                logger.log_struct(feedback_obj.model_dump(), severity="INFO")
            except Exception as exc:  # pragma: no cover - logging is best-effort
                logging.error("Failed to log struct feedback: %s", exc)

        def register_operations(self) -> dict[str, list[str]]:
            """Expose ``register_feedback`` as a sync operation on the engine."""
            operations = super().register_operations()
            sync_ops = list(operations.get("", []))
            if "register_feedback" not in sync_ops:
                sync_ops.append("register_feedback")
            operations[""] = sync_ops
            return operations

    return AgentEngineApp


def get_app() -> Any:
    """Lazily build and cache the :class:`AgentEngineApp` wrapping the
    root ADK agent.

    The first invocation resolves the remote A2A agent via the registry, so
    this function must NOT be called at module import time. Deployment code
    and tests should call it explicitly.
    """
    global _app
    if _app is not None:
        return _app

    agent_engine_app_cls = _build_agent_engine_app_class()
    _app = agent_engine_app_cls(agent=_build_agent(), enable_tracing=True)
    return _app


# Module-level ``app`` and ``root_agent`` stay ``None`` until ``get_app()`` is
# called. This keeps module import side-effect free per
# ``docs/deployment_patterns.md`` §3.
app: Any | None = None
root_agent: Any | None = None
