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
import os
import sys
from typing import Any
import vertexai
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.integrations.agent_registry import AgentRegistry
from google.cloud import logging as google_cloud_logging
from google.genai import types

# Use relative imports to match sample style
from .app_utils.telemetry import setup_telemetry
from .app_utils.typing import Feedback

load_dotenv()

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "agent-o11y")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# Initialize registry and get remote agent
registry = AgentRegistry(project_id=project_id, location=location)
remote_agent = registry.get_remote_a2a_agent("projects/agent-o11y/locations/us-central1/agents/agentregistry-00000000-0000-0000-9d8c-9b2c5ee73ba1")

class SreHelperAgent(Agent):
    """Custom SRE Helper Agent that adds feedback functionality."""
    
    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        logging.info(f"Received feedback: {feedback}")
        try:
            logging_client = google_cloud_logging.Client()
            logger = logging_client.logger("sre-helper")
            feedback_obj = Feedback.model_validate(feedback)
            logger.log_struct(feedback_obj.model_dump(), severity="INFO")
        except Exception as e:
            logging.error(f"Failed to log struct feedback: {e}")

sre_helper = SreHelperAgent(
    name="sre_helper",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are the orchestrator for SRE incidents. Gather incident details and delegate investigation to o11y_agent.",
    sub_agents=[remote_agent],
)

root_agent = sre_helper
