# 🛠️ AutoSRE: Multi-Agent Observability Orchestrator

Welcome to the **AutoSRE** repository. This project implements an experimental multi-agent system designed to assist Site Reliability Engineers (SREs) in investigating incidents using advanced AI reasoning.

---

## 🗺️ Overview

The system uses a hierarchical multi-agent architecture powered by Google's ADK (Agent Development Kit) and `gemini-2.5-flash`.

- **`sre-helper/`**: The **Root Orchestrator Agent**. It interacts with the user, gathers incident context, and delegates complex observability tasks to specialized agents.
- **`o11y-agent/`**: The **Observability Specialist Agent**. It runs as an independent service (using the A2A protocol) and wraps sub-agents specialized in querying logs, traces, and metrics via Model Context Protocol (MCP) servers.
- **`docs/`**: Centralized documentation covering architecture, local testing workflows, and query guidelines.

---

## 🚀 Quick Start

### 💻 Local Development & Testing

To test the full multi-agent flow locally with production-parity, we run the agents in separate processes communicating via HTTP (A2A protocol).

#### 1. Install Dependencies

Ensure you have `uv` installed, then run:

```bash
# In root directory
cd sre-helper && uv sync
cd ../o11y-agent && uv sync
```

#### 2. Start the Observability Agent

From the `o11y-agent` directory, start the agent server:

```bash
uv run adk api_server --a2a --port=8005 ./
```

#### 3. Run the Integration Test

From the `sre-helper` directory, run the test script that calls the remote agent:

```bash
LOCAL_A2A=True uv run run_a2a_test.py
```

---

### ☁️ Deployment to Google Cloud (GCP)

Deploy the agents to Vertex AI Reasoning Engine for production use.

#### 1. Set up Environment

Ensure you have the Google Cloud SDK configured:

```bash
gcloud config set project <your-project-id>
```

#### 2. Deploy o11y-agent (Child Agent First)

From the `o11y-agent` directory:

```bash
uv sync
uv run python ../scripts/deploy.py .
```

#### 3. Deploy sre-helper (Root Agent)

From the `sre-helper` directory:

```bash
uv sync
uv run python ../scripts/deploy.py .
```

---

## 🛠️ Tooling & Commands

To manage the lifecycle of the agents, you should install the `agents-cli` tool.

### Installation
Ensure you have `uv` installed, then run:
```bash
uv tool install agents-cli
```

### Common Commands
Here are the most common commands used during development:

| Command | Purpose |
|:---|:---|
| `uv run agents-cli dev` | Interactive local testing |
| `uv run agents-cli test` | Run unit and integration tests |
| `uv run agents-cli eval` | Run evaluation against evalsets |
| `uv run agents-cli deploy` | Deploy agents to Agent Engine |

For a full list of commands and advanced usage, see `GEMINI.md`.

---

## 📚 Deep Dives

For more details, refer to the central documentation:

- **[System Architecture](docs/architecture.md)**: High-level design and data flow.
- **[Local Running Guide](docs/local_running.md)**: Detailed local testing instructions.
- **[Observability Queries](docs/observability_queries.md)**: Guidelines for specialist agents.

## 🛡️ Code Quality

Keep the codebase pristine:

```bash
uvx ruff check .
```
