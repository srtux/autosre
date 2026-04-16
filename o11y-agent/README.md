# Observability Agent (o11y-agent)

This component provides the observability specialist agent used by the AutoSRE system.

## Overview

The `o11y-agent` is exposed as an **A2A agent** and is designed to be called by the
root `sre-helper` agent to investigate incidents. The current implementation uses a
single ADK agent (`OpsAgent`) with MCP toolsets for:
- Cloud Logging
- Cloud Trace
- Cloud Monitoring
- Error Reporting

## Structure

- `app/agent.py`: Defines `OpsAgent`, lazy MCP tool initialization, and the A2A wrapper.
- `app/a2a_server.py`: Local A2A FastAPI export (`to_a2a(..., port=10000)`).
- `pyproject.toml`: Dependencies for this component.

## Usage

This agent can run locally as an A2A server (`LOCAL_A2A=True`) or be invoked through
the Vertex AI Reasoning Engine A2A endpoint in production.
