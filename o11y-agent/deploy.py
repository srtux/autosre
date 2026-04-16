import vertexai
from vertexai import types
import os
import sys
import shutil
import tempfile

# Initialize the Vertex AI client with v1beta1 API for agent identity support
PROJECT_ID = "agent-o11y"
LOCATION = "us-central1"
BUCKET_NAME = "agent-o11y_cloudbuild"

client = vertexai.Client(
  project=PROJECT_ID,
  location=LOCATION,
  http_options=dict(api_version="v1beta1")
)

from vertexai._genai._agent_engines_utils import ModuleAgent, _generate_class_methods_spec_or_raise, _to_dict

# Assume running from the o11y-agent directory
agent_path = os.path.abspath(".")
agent_name = os.path.basename(agent_path)

print(f"Deploying {agent_name} with Agent Identity...")

# Add the agent directory and app directory to sys.path to import its app
sys.path.insert(0, agent_path)
sys.path.insert(0, os.path.join(agent_path, "app"))

print(f"Importing app from app/agent.py ...")
try:
    from app.agent import app as agent_app
except ImportError as e:
    print(f"Failed to import app from app/agent.py: {e}")
    sys.exit(1)

# Define operations for AdkApp
operations = {
    "": ["get_session", "list_sessions", "create_session", "delete_session"],
    "async": ["async_get_session", "async_list_sessions", "async_create_session", "async_delete_session", "async_add_session_to_memory", "async_search_memory"],
    "stream": ["stream_query"],
    "async_stream": ["async_stream_query", "streaming_agent_run_with_events"],
}

print(f"Using operations for {agent_name}: {operations}")

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

# Create a temp dir to package source code inside the project directory
tmp_dir = tempfile.mkdtemp(dir=agent_path)
print(f"Created temp dir {tmp_dir} for packaging source code.")

# Copy files from app directory directly to temp dir (FLAT structure)
app_src = os.path.join(agent_path, "app")
if os.path.exists(app_src):
    for item in os.listdir(app_src):
        s = os.path.join(app_src, item)
        d = os.path.join(tmp_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
    print(f"Copied contents of {app_src} to {tmp_dir}")
else:
    print(f"Warning: {app_src} does not exist!")
    sys.exit(1)

# Create sitecustomize.py directly in temp dir
sitecustomize_path = os.path.join(tmp_dir, "sitecustomize.py")
with open(sitecustomize_path, "w") as f:
    f.write("""import sys
import os
print(f"SITE_CUSTOMIZE: CWD={os.getcwd()}")
print(f"SITE_CUSTOMIZE: sys.path={sys.path}")
print(f"SITE_CUSTOMIZE: __file__={__file__}")
sys.path.insert(0, os.path.dirname(__file__))
""")
print(f"Created {sitecustomize_path}")

# Create agent_engine_app.py directly in temp dir
engine_app_path = os.path.join(tmp_dir, "agent_engine_app.py")
with open(engine_app_path, "w") as f:
    f.write("""from agent import app as agent_app
from vertexai.agent_engines import AdkApp

app = AdkApp(agent=agent_app)
app.name = "o11y_agent"
""")
print(f"Created {engine_app_path} with flat import and correct app name.")

# Write requirements.txt to the temp directory
requirements_path = os.path.join(tmp_dir, "requirements.txt")
with open(requirements_path, "w") as f:
    for req in requirements:
        f.write(req + "\n")
print(f"Created requirements.txt at {requirements_path}")

# Use ModuleAgent to generate class_methods locally
# We must add tmp_dir to sys.path so it can find agent_engine_app
sys.path.insert(0, tmp_dir)

# Clean up sys.modules to avoid conflicts with previously loaded app
to_delete = [name for name in sys.modules if name == "app" or name.startswith("app.")]
for name in to_delete:
    del sys.modules[name]

module_agent = ModuleAgent(
    module_name="agent_engine_app",
    agent_name="app",
    register_operations=operations,
    sys_paths=["."], 
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
    shutil.rmtree(tmp_dir)
    sys.exit(1)
finally:
    # Remove tmp_dir from sys.path to avoid side effects
    sys.path.remove(tmp_dir)

# Deploy the agent with Agent Identity using Mode B (Entrypoint)
try:
    remote_app = client.agent_engines.create(
      config={
        "display_name": f"{agent_name}-with-identity",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "source_packages": [tmp_dir, requirements_path],
        "entrypoint_module": "agent_engine_app",
        "entrypoint_object": "app",
        "class_methods": class_methods,
        "staging_bucket": f"gs://{BUCKET_NAME}",
      },
    )
finally:
    # Clean up temp dir
    shutil.rmtree(tmp_dir)
    print(f"Cleaned up temp dir {tmp_dir}")

print(f"Deployment successful for {agent_name}!")
print(f"Agent Engine ID: {remote_app.api_resource.name}")
print(f"Effective Identity: {remote_app.api_resource.spec.effective_identity}")
