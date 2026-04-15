import logging
import os
import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from vertexai.agent_engines.templates.adk import AdkApp

from app.agent import app as adk_app

# Load environment variables from .env file at runtime
load_dotenv()

class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app."""
        vertexai.init()
        super().set_up()
        logging.basicConfig(level=logging.INFO)

logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
agent_engine = AgentEngineApp(
    app=adk_app,
    artifact_service_builder=lambda: (
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    ),
)
