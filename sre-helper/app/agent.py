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

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentSkill, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from vertexai.preview.reasoning_engines.templates.a2a import A2aAgent, create_agent_card

from app_utils import config


# Get observability delegator from registry as requested by user
def make_a2a_wrapper():
    async def o11y_agent(query: str) -> str:
        """Call the o11y agent using A2A protocol (handles local and remote)."""
        import asyncio
        import uuid

        import google.auth
        import google.auth.transport.requests
        import httpx

        if config.is_local_a2a():
            print("Using local A2A client...")
            from a2a.client import A2AClient
            from a2a.client.card_resolver import A2ACardResolver
            from a2a.types import MessageSendParams, SendMessageRequest

            async with httpx.AsyncClient() as httpx_client:
                resolver = A2ACardResolver(
                    httpx_client=httpx_client,
                    base_url="http://localhost:10000",
                )
                agent_card = await resolver.get_agent_card()
                client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

                send_message_payload = {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": query}],
                        "contextId": str(uuid.uuid4()),
                        "messageId": str(uuid.uuid4()),
                    }
                }
                request = SendMessageRequest(
                    id=str(uuid.uuid4()),
                    params=MessageSendParams(**send_message_payload),
                )
                response = await client.send_message(request)
                return str(response)

        else:
            url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/agent-o11y/locations/us-central1/reasoningEngines/2769617563565424640/a2a/v1/message:send"
            print(f"Calling remote agent A2A URL: {url}")

            # Get auth headers
            credentials, _ = google.auth.default()
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            }

            # A2A Message format
            data = {
                "message": {
                    "role": "1",  # As shown in official docs for REST
                    "content": [{"text": query}],
                    "contextId": str(uuid.uuid4()),
                    "messageId": str(uuid.uuid4()),
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code != 200:
                    print(f"Error Response: {response.text}")
                response.raise_for_status()
                result = response.json()

                task_id = result.get("task", {}).get("id")
                if not task_id:
                    return f"Failed to start task: {result}"

                print(f"Task started with ID: {task_id}. Polling for result...")

                # Polling loop
                task_url = url.replace("message:send", f"tasks/{task_id}")
                for _ in range(30):  # Poll for 30 seconds max
                    task_response = await client.get(task_url, headers=headers)
                    task_response.raise_for_status()
                    task_data = task_response.json()

                    state = task_data.get("status", {}).get("state")
                    print(f"Task state: {state}")

                    if state == "TASK_STATE_COMPLETED":
                        # Extract result from history
                        history = task_data.get("history", [])
                        for msg in reversed(history):
                            if (
                                msg.get("role") == "ROLE_AGENT"
                                or msg.get("role") == "agent"
                            ):
                                content = msg.get("content", [])
                                texts = [p["text"] for p in content if "text" in p]
                                if texts:
                                    return "\n".join(texts)
                        return str(task_data)
                    elif state == "TASK_STATE_FAILED":
                        return f"Task failed: {task_data}"

                    await asyncio.sleep(1)

                return f"Task timed out. Last state: {state}"

    return o11y_agent


class SreHelperAgentExecutor(AgentExecutor):
    def __init__(self):
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.message:
            raise ValueError("Message should be present in request context")
        query = context.get_user_input()
        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    "Processing with SRE Helper...", task.context_id, task.id
                ),
            )

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

            runner = Runner(
                app_name=root_agent.name,
                agent=root_agent,
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
            )

            session = await runner.session_service.create_session(
                app_name=root_agent.name,
                user_id="a2a_user",
                state={},
                session_id=task.context_id,
            )

            content = types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            )

            response_text = ""
            async for event in runner.run_async(
                user_id="a2a_user", session_id=session.id, new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text
                            await event_queue.enqueue_event(
                                new_agent_text_message(
                                    part.text, task.context_id, task.id
                                )
                            )

            await updater.add_artifact(
                [Part(root=TextPart(text=response_text))],
                name="response",
            )
            await updater.complete()

        except Exception as e:
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(f"Error: {e!s}", task.context_id, task.id),
                final=True,
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


# Define skills
skill = AgentSkill(
    id="orchestrate_sre",
    name="Orchestrate SRE",
    description="Orchestrate SRE investigation and delegate to o11y agent",
    tags=["sre", "orchestration"],
    examples=["Investigate high CPU usage"],
)

# Create agent card
card = create_agent_card(
    agent_name="sre_helper",
    description="Orchestrator for SRE incidents",
    skills=[skill],
)


class CustomA2aAgent(A2aAgent):
    def query(self, query: str) -> str:
        """Dummy query method to pass SDK validation.
        A2A communication happens via on_message_send."""
        return "This is an A2A agent. Please use the A2A protocol to interact."


# Instantiate CustomA2aAgent
app = CustomA2aAgent(
    agent_card=card,
    agent_executor_builder=SreHelperAgentExecutor,
)


def get_app() -> A2aAgent:
    """Return the exported A2A app.

    Maintains compatibility with Agent Engine wrappers that expect a `get_app()`
    factory in `app.agent`.
    """
    return app
