import os

import google.auth
from dotenv import load_dotenv

load_dotenv()


def get_project_id() -> str:
    """Get the Google Cloud project ID."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        _, project_id = google.auth.default()
    return project_id


def get_location() -> str:
    """Get the Google Cloud location."""
    return os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")


def use_vertex_ai() -> bool:
    """Check if Vertex AI should be used."""
    return os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True"


def is_local_a2a() -> bool:
    """Check if local A2A simulation is enabled."""
    return os.environ.get("LOCAL_A2A", "False") == "True"


PROJECT_ID = get_project_id()
LOCATION = get_location()
USE_VERTEXAI = use_vertex_ai()
LOCAL_A2A = is_local_a2a()
