import vertexai
from vertexai import types
from vertexai.agent_engines import AdkApp
import os
import sys

if len(sys.argv) < 2:
    print("Usage: uv run python scripts/deploy_with_sdk.py <agent_directory>")
    print("Example: uv run python scripts/deploy_with_sdk.py o11y-agent")
    sys.exit(1)

agent_dir = sys.argv[1]
agent_path = os.path.abspath(agent_dir)

if not os.path.exists(agent_path):
    print(f"Directory {agent_path} does not exist.")
    sys.exit(1)

# Add the agent directory to sys.path to import its app
sys.path.insert(0, agent_path)

print(f"Importing app from {agent_dir}/app/agent.py ...")
try:
    from app.agent import app as agent_app
except ImportError as e:
    print(f"Failed to import app from {agent_dir}/app/agent.py: {e}")
    sys.exit(1)

# Project configuration
PROJECT_ID = "agent-o11y"
LOCATION = "us-central1"
BUCKET_NAME = "agent-o11y_cloudbuild"

# Initialize the Vertex AI client.
# We explicitly use the v1beta1 API version because Agent Identity (SPIFFE)
# support is currently available in the beta API surface.
client = vertexai.Client(
  project=PROJECT_ID,
  location=LOCATION,
  http_options=dict(api_version="v1beta1")
)

# Wrap the agent in AdkApp to ensure compatibility with the Reasoning Engine runtime
app = AdkApp(agent=agent_app)

agent_name = os.path.basename(agent_path)
print(f"Deploying {agent_name} with Agent Identity...")

# Deploy the agent with Agent Identity enabled.
# This bypasses agents-cli to ensure we can enforce the use of SPIFFE identities.
remote_app = client.agent_engines.create(
  agent=app,
  config={
    "display_name": f"{agent_name}-with-identity",
    # Enforce the use of SPIFFE-based Workload Identity Federation
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    # List packages that must be installed in the remote container.
    # We include pydantic and cloudpickle to satisfy SDK serialization checks.
    "requirements": [
      "google-cloud-aiplatform[adk,agent_engines]",
      "pydantic",
      "cloudpickle",
      "requests",
      "httpx",
      "httpx-sse",
      "a2a-sdk>=0.3.26",
    ],
    "staging_bucket": f"gs://{BUCKET_NAME}",
  },
)

print(f"Deployment successful for {agent_dir}!")
print(f"Agent Engine ID: {remote_app.api_resource.name}")
print(f"Effective Identity: {remote_app.api_resource.spec.effective_identity}")
