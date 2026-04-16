# AutoSRE: Multi-Agent Observability Orchestrator

Welcome to the **AutoSRE** repository. This project implements an experimental multi-agent system designed to assist Site Reliability Engineers (SREs) in investigating incidents using advanced AI reasoning.

---

## Overview

The system uses a multi-agent architecture powered by Google's ADK (Agent Development Kit) and `gemini-2.5-flash`.

- **`sre-helper/`**: The **Root Orchestrator Agent**. It interacts with the user, gathers incident context, and delegates observability work to the `o11y-agent` via the A2A protocol using ADK's `AgentRegistry` + `sub_agents` pattern.
- **`o11y-agent/`**: The **Observability Specialist Agent**. It runs as an independent A2A service and is implemented as a **single `OpsAgent` with four MCP toolsets** — Logging, Trace, Monitoring, and Error Reporting — each backed by a Model Context Protocol (MCP) server in Agent Registry.
- **`docs/`**: Centralized documentation covering architecture, local testing workflows, and query guidelines.

---

## Quick Start

### Local Development & Testing

To test the full multi-agent flow locally with production-parity, we run the agents in separate processes communicating via HTTP (A2A protocol).

#### 1. Install Dependencies

Ensure you have `uv` installed, then run:

```bash
# In root directory
cd sre-helper && uv sync
cd ../o11y-agent && uv sync
```

#### 2. Start the Observability Agent

From the `o11y-agent` directory, start the A2A server on port 10000:

```bash
uv run uvicorn app.a2a_server:a2a_app_factory --factory --port 10000
```

#### 3. Run the Integration Tests

From the `sre-helper` directory, run the tests:

```bash
uv run pytest tests/integration -q
```

---

### Deployment to Google Cloud (GCP)

Deploy the agents to Vertex AI Agent Engine (Reasoning Engine) for production use. Each agent has its own deploy script; there is no longer a shared `scripts/deploy.py`.

#### 1. Set up Environment

Copy `.env.example` to `.env` and fill in the required values. At minimum, deployment requires:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_STORAGE_BUCKET`

`GOOGLE_CLOUD_LOCATION` is optional (defaults to `us-central1`). Ensure the Google Cloud SDK is configured (`gcloud config set project <your-project-id>`).

#### 2. Deploy o11y-agent (Child Agent First)

From the `o11y-agent` directory:

```bash
uv sync
uv run python deploy.py
```

#### 3. Deploy sre-helper (Root Agent)

From the `sre-helper` directory:

```bash
uv sync
uv run python deployment/deploy.py
```

---

## Common Workflows

Common development, testing, and deployment workflows are documented in [docs/local_running.md](docs/local_running.md).

---

## Deep Dives

For more details, refer to the central documentation:

- **[System Architecture](docs/architecture.md)**: High-level design and data flow.
- **[Local Running Guide](docs/local_running.md)**: Detailed local testing instructions.
- **[A2A Development Guide](docs/a2a_development.md)**: A2A payload shape and executor patterns.
- **[Deployment Patterns](docs/deployment_patterns.md)**: Lessons learned deploying to Agent Engine.
- **[Observability Queries](docs/observability_queries.md)**: Query guidelines for the specialist agent's toolsets.

## Code Quality

Keep the codebase pristine:

```bash
uv run ruff check .
```
