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

PROJECT_ID = "agent-o11y"
LOCATION = "us-central1"
BUCKET_NAME = "agent-o11y_cloudbuild"

# Initialize the Vertex AI client with v1beta1 API for agent identity support
client = vertexai.Client(
  project=PROJECT_ID,
  location=LOCATION,
  http_options=dict(api_version="v1beta1")
)

from vertexai._genai._agent_engines_utils import ModuleAgent, _generate_class_methods_spec_or_raise, _to_dict

agent_name = os.path.basename(agent_path)
print(f"Deploying {agent_name} with Agent Identity...")

# Define operations for AdkApp
operations = {
    "": ["get_session", "list_sessions", "create_session", "delete_session"],
    "async": ["async_get_session", "async_list_sessions", "async_create_session", "async_delete_session", "async_add_session_to_memory", "async_search_memory"],
    "stream": ["stream_query"],
    "async_stream": ["async_stream_query", "streaming_agent_run_with_events"],
}

print(f"Using operations for {agent_name}: {operations}")

# Use ModuleAgent to generate class_methods locally
module_agent = ModuleAgent(
    module_name="app.agent_engine_app",
    agent_name="app",
    register_operations=operations,
    sys_paths=[agent_path], # Ensure it can find app.agent_engine_app
)

# Generate class methods spec
try:
    class_methods_proto = _generate_class_methods_spec_or_raise(
        agent=module_agent,
        operations=operations,
    )
    class_methods = [_to_dict(spec) for spec in class_methods_proto]
    print(f"Generated {len(class_methods)} class methods.")
except Exception as e:
    print(f"Failed to generate class methods: {e}")
    sys.exit(1)

requirements = [
  "--extra-index-url https://us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/",
  "google-cloud-aiplatform[adk,agent_engines]",
  "a2a-sdk>=0.3.26,<0.4",
  "pydantic",
  "cloudpickle",
  "requests",
  "httpx",
  "httpx-sse",
  "google-cloud-iamconnectorcredentials",
]

import shutil
import tempfile

# Create a temp dir to package source code inside the project directory
tmp_dir = tempfile.mkdtemp(dir=agent_path)
print(f"Created temp dir {tmp_dir} for packaging source code.")

# Copy app directory to temp dir
app_src = os.path.join(agent_path, "app")
app_dst = os.path.join(tmp_dir, "o11y_agent")
if os.path.exists(app_src):
    shutil.copytree(app_src, app_dst)
    print(f"Copied {app_src} to {app_dst}")
else:
    print(f"Warning: {app_src} does not exist!")

# Update agent_engine_app.py in temp dir to use correct import
engine_app_path = os.path.join(app_dst, "agent_engine_app.py")
if os.path.exists(engine_app_path):
    with open(engine_app_path, "w") as f:
        f.write("""from o11y_agent.agent import app as agent_app
from vertexai.agent_engines import AdkApp

app = AdkApp(agent=agent_app)
""")
    print(f"Updated {engine_app_path} with correct import.")

# Write requirements.txt to the temp directory
requirements_path = os.path.join(tmp_dir, "requirements.txt")
with open(requirements_path, "w") as f:
    for req in requirements:
        f.write(req + "\n")
print(f"Created requirements.txt at {requirements_path}")

# Deploy the agent with Agent Identity using Mode B (Entrypoint)
try:
    remote_app = client.agent_engines.create(
      config={
        "display_name": f"{agent_name}-with-identity",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "source_packages": [app_dst, requirements_path],
        "entrypoint_module": "o11y_agent.agent_engine_app",
        "entrypoint_object": "app",
        "class_methods": class_methods,
        "staging_bucket": f"gs://{BUCKET_NAME}",
      },
    )
finally:
    # Clean up temp dir
    shutil.rmtree(tmp_dir)
    print(f"Cleaned up temp dir {tmp_dir}")

print(f"Deployment successful for {agent_dir}!")
print(f"Agent Engine ID: {remote_app.api_resource.name}")
print(f"Effective Identity: {remote_app.api_resource.spec.effective_identity}")
