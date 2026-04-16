import os
import sys
import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

# Ensure the parent directory is in sys.path to import sre_helper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sre_helper.agent import root_agent

def create() -> None:
    """Creates an agent engine for SRE Helper."""
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)

    # We must use the internal registry URL for corporate environment
    requirements = [
      "google-cloud-aiplatform[adk,agent_engines]",
      "a2a-sdk>=0.3.26,<0.4",
      "pydantic",
      "cloudpickle",
      "requests",
      "httpx",
      "httpx-sse",
      "google-cloud-iamconnectorcredentials",
      "python-dotenv",
      "google-cloud-logging",
    ]

    print("Creating remote agent on Vertex AI...")
    remote_agent = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        requirements=requirements,
    )
    print(f"Created remote agent: {remote_agent.resource_name}")

def main() -> None:
    load_dotenv()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "agent-o11y")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    bucket = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET", "agent-o11y_cloudbuild")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    if not project_id or not location or not bucket:
        print("Missing required project, location, or bucket configuration.")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    # Simple arg parsing instead of absl
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        if len(sys.argv) < 3:
            print("Usage: python deploy.py --delete <resource_id>")
            return
        resource_id = sys.argv[2]
        remote_agent = agent_engines.get(resource_id)
        remote_agent.delete(force=True)
        print(f"Deleted remote agent: {resource_id}")
    else:
        # Default to create
        create()

if __name__ == "__main__":
    main()
