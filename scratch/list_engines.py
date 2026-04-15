import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="agent-o11y", location="us-central1")

try:
    engines = reasoning_engines.ReasoningEngine.list()
    print("All engines via reasoning_engines:")
    for e in engines:
        print(f"Name: {e.display_name}, ID: {e.resource_name}")
except Exception as e:
    print(f"Error listing via reasoning_engines: {e}")

try:
    client = vertexai.Client(project="agent-o11y", location="us-central1")
    agents = list(client.agent_engines.list())
    print("\nAll agents via Client:")
    for a in agents:
        print(f"Name: {a.api_resource.display_name}, ID: {a.api_resource.name}")
except Exception as e:
    print(f"Error listing via Client: {e}")
