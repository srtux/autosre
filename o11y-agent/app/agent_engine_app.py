"""Vertex AI Agent Engine wrapper for the o11y-agent.

The ``AgentEngineApp`` subclasses ``AdkApp`` to add:

* OpenTelemetry / GenAI telemetry setup on ``set_up()``.
* A Cloud Logging client for structured logs.
* A ``register_feedback`` operation so the deployed agent can record feedback.

``get_app()`` is the canonical way to get an instance. It is lazy: the
observability agent itself is built on first call, never at module import,
which keeps this module side-effect free for Vertex AI cold-start.
"""

import logging
import os
import uuid
from typing import Literal

import google.cloud.logging as google_cloud_logging
from pydantic import BaseModel, Field
from vertexai.agent_engines import AdkApp


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry and GenAI telemetry with GCS upload.

    Mirrors ``sre-helper/sre_helper/app_utils/telemetry.py``. Kept local here
    because there is no shared package between o11y-agent and sre-helper.
    """
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    if bucket and capture_content != "false":
        logging.info(
            "Prompt-response logging enabled - mode: NO_CONTENT (metadata only, no prompts/responses)"
        )
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=o11y-agent,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logging.info(
            "Prompt-response logging disabled (set LOGS_BUCKET_NAME=gs://your-bucket and OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT to enable)"
        )

    return bucket


class Feedback(BaseModel):
    """Represents feedback for a conversation with the o11y-agent."""

    score: int | float
    text: str | None = None
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["o11y-agent"] = "o11y-agent"
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentEngineApp(AdkApp):
    """AdkApp subclass with telemetry, Cloud Logging, and feedback support."""

    def set_up(self) -> None:
        """Run once in the Agent Engine container before handling requests."""
        setup_telemetry()
        self._logging_client = google_cloud_logging.Client()
        super().set_up()

    def register_feedback(self, feedback: dict) -> None:
        """Validate and log feedback via Cloud Logging."""
        validated = Feedback.model_validate(feedback)
        logger = self._logging_client.logger("o11y-agent-feedback")
        logger.log_struct(validated.model_dump(), severity="INFO")

    def register_operations(self) -> dict:
        """Expose ``register_feedback`` alongside the default AdkApp operations."""
        operations = super().register_operations()
        operations.setdefault("", []).append("register_feedback")
        return operations


def get_app() -> AgentEngineApp:
    """Build the deployable ``AgentEngineApp``.

    Imports ``app.agent.get_ops_agent`` lazily so that merely importing this
    module does not trigger agent/MCP/registry work at Vertex AI cold-start.
    """
    # Lazy import to keep this module side-effect free.
    from app.agent import get_ops_agent

    return AgentEngineApp(agent=get_ops_agent(), enable_tracing=True)


# The deploy script calls ``get_app()`` explicitly; no module-level instance.
app = None


__all__ = ["AgentEngineApp", "Feedback", "get_app", "setup_telemetry"]
