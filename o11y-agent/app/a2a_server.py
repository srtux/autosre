import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import get_ops_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create the normal ADK agent
agent = get_ops_agent()

# Export it as A2A app
# This returns a FastAPI app that can be run with uvicorn
a2a_app = to_a2a(agent, port=10000)
