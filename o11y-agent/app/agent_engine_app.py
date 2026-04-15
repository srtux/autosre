from app.agent import app as agent_app
from vertexai.agent_engines import AdkApp

app = AdkApp(agent=agent_app)
