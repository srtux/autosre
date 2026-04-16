"""A2A server entry point for the o11y-agent.

Run locally from the ``o11y-agent/`` directory:

    uv run uvicorn app.a2a_server:a2a_app_factory --factory --port 10000

The ``--factory`` flag tells uvicorn to call ``a2a_app_factory()`` at boot time
to get the ASGI app. Building the agent only when uvicorn invokes the factory
keeps this module import side-effect free, per
``docs/deployment_patterns.md`` section 3.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import get_ops_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a


def a2a_app_factory():
    """ASGI app factory.

    Used with ``uvicorn app.a2a_server:a2a_app_factory --factory``. uvicorn
    calls this lazily when the server boots so agent construction (which
    touches auth, the agent registry, and MCP toolsets) never runs at
    module import time.
    """
    agent = get_ops_agent()
    return to_a2a(agent, port=10000)
