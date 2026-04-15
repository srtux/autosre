# Copyright 2026 Google LLC

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.models import Gemini

# GoogleAuth removed due to import error
from google.genai import types

from app.app_utils.config import LOCAL_A2A, LOCATION, PROJECT_ID

# Initialize Agent Registry
registry = AgentRegistry(project_id=PROJECT_ID, location=LOCATION)


# Get observability delegator from registry as requested by user
def make_a2a_wrapper():
    def o11y_agent(query: str) -> str:
        """Call the remote o11y agent using A2A protocol."""
        from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        if LOCAL_A2A:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            agent_card_path = os.path.abspath(os.path.join(current_dir, "../../o11y-agent/app/agent.json"))
            remote_agent = RemoteA2aAgent(
                name="o11y_agent",
                agent_card=agent_card_path
            )
        else:
            remote_agent = registry.get_remote_a2a_agent("agents/o11y-agent")

        session_service = InMemorySessionService()
        session = session_service.create_session_sync(user_id="local_user", app_name="o11y_call")
        runner = Runner(agent=remote_agent, session_service=session_service, app_name="o11y_call")

        events = list(runner.run(
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)]),
            user_id="local_user",
            session_id=session.id,
        ))

        response = ""
        for e in events:
            if e.author == "o11y_agent":
                 if e.content and e.content.parts:
                     for p in e.content.parts:
                         if p.text:
                             response += p.text
        return response or "No response from remote agent"
    return o11y_agent

o11y_agent = make_a2a_wrapper()


root_agent = Agent(
    name="sre_helper",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are the orchestrator for SRE incidents. Gather incident details and delegate investigation to o11y_agent.",
    tools=[o11y_agent],
)

app = App(
    root_agent=root_agent,
    name="sre_helper",
)
