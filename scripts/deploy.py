import vertexai
from vertexai import types
import os
import sys
import shutil
import tempfile

if len(sys.argv) < 2:
    print("Usage: uv run python scripts/deploy_with_sdk.py <agent_directory>")
    print("Example: uv run python scripts/deploy_with_sdk.py o11y-agent")
    sys.exit(1)

agent_dir = sys.argv[1]
agent_path = os.path.abspath(agent_dir)

if not os.path.exists(agent_path):
    print(f"Directory {agent_path} does not exist.")
    sys.exit(1)


# Project configuration
PROJECT_ID = "agent-o11y"
LOCATION = "us-central1"
BUCKET_NAME = "agent-o11y_cloudbuild"

# Initialize the Vertex AI client.
client = vertexai.Client(
    project=PROJECT_ID, location=LOCATION, http_options=dict(api_version="v1beta1")
)

agent_name = os.path.basename(agent_path)
print(f"Deploying {agent_name} with Agent Identity...")

# Create a temp dir to preserve 'app' directory structure
tmp_dir = tempfile.mkdtemp()
app_tmp_dir = os.path.join(tmp_dir, "app")
shutil.copytree(os.path.join(agent_path, "app"), app_tmp_dir)

# Import from the structured temp dir to ensure cloudpickle records it as app.agent
sys.path.insert(0, tmp_dir)
try:
    from app import agent as agent_app
except ImportError as e:
    print(f"Failed to import app from temp dir: {e}")
    shutil.rmtree(tmp_dir)
    sys.exit(1)

app = agent_app.app
print(f"Available methods on app: {dir(app)}")

# Find the wheel file in dist directory if it exists
wheel_file = None
dist_dir = os.path.join(agent_path, "dist")
if os.path.exists(dist_dir):
    for f in os.listdir(dist_dir):
        if f.endswith(".whl"):
            wheel_file = os.path.join(dist_dir, f)
            break

extra_packages = [tmp_dir]
if wheel_file:
    print(f"Found wheel file: {wheel_file}")
    extra_packages = [wheel_file]

remote_app = client.agent_engines.create(
    agent=app,
    config={
        "display_name": f"{agent_name}",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "requirements": [
            "google-cloud-aiplatform[adk,agent_engines]",
            "pydantic",
            "cloudpickle",
            "requests",
            "httpx",
            "httpx-sse",
            # Pin to a released a2a-sdk version to avoid runtime drift between
            # the objects cloudpickle serialized locally and whatever HEAD of
            # main the container would otherwise install.
            "a2a-sdk>=0.3.26,<0.4",
            "google-cloud-iamconnectorcredentials",
        ],
        "extra_packages": extra_packages,
        "staging_bucket": f"gs://{BUCKET_NAME}",
    },
)

# Clean up temp dir
shutil.rmtree(tmp_dir)

print(f"Deployment successful for {agent_dir}!")
print(f"Agent Engine ID: {remote_app.api_resource.name}")
print(f"Effective Identity: {remote_app.api_resource.spec.effective_identity}")

print(f"Deployment successful for {agent_dir}!")
print(f"Agent Engine ID: {remote_app.api_resource.name}")
print(f"Effective Identity: {remote_app.api_resource.spec.effective_identity}")
