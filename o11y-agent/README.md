# Observability Agent (o11y-agent)

This component provides a specialized parallel agent for observability tasks in the SRE Helper system.

## Overview

The `o11y-agent` is a `ParallelAgent` that wraps three specialist agents:
- **LoggingAgent**: Queries logs using `logging-mcp-server`.
- **TraceAgent**: Queries traces using `trace-mcp-server`.
- **MetricsAgent**: Queries metrics using `metrics-mcp-server`.

It is designed to be called by the root `sre-helper` agent to perform detailed investigations.

## Structure

- `app/agent.py`: Defines the agents and the `ParallelAgent` structure.
- `pyproject.toml`: Dependencies for this component.

## Usage

This agent is exposed as an A2A server and is intended to be retrieved via the `AgentRegistry` by the root agent.
