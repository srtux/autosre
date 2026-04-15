import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="agent-o11y", location="us-central1")

agent_id = "775930303523848192"
try:
    engine = reasoning_engines.ReasoningEngine(f"projects/38829824347/locations/us-central1/reasoningEngines/{agent_id}")
    print("Agent Details:")
    print(f"Display Name: {engine.display_name}")
    
    # Try to find env vars in the resource
    if hasattr(engine, "gca_resource"):
         print("GCA Resource:")
         print(engine.gca_resource)
    else:
         print("No gca_resource attribute found.")
except Exception as e:
    print(f"Error: {e}")
