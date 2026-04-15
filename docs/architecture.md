# System Architecture

This document describes the architecture of the AutoSRE system, which consists of a root agent orchestrating specialist observability agents.

## Overview

The system is designed to assist Site Reliability Engineers (SREs) in investigating incidents. It uses a multi-agent approach where a central orchestrator delegates tasks to specialized agents that have access to specific observability data sources via Model Context Protocol (MCP) servers.

## Component Diagram

The following diagram illustrates the relationship between the agents and the MCP servers.

```mermaid
graph TD
    User([User]) --> SREHelper[sre-helper Root Agent]
    SREHelper -->|Delegates to| O11yAgent[o11y-agent ParallelAgent]
    
    subgraph O11yAgent [Observability Agent]
        LoggingAgent[Logging Agent]
        TraceAgent[Trace Agent]
        MetricsAgent[Metrics Agent]
    end
    
    O11yAgent -.-> LoggingAgent
    O11yAgent -.-> TraceAgent
    O11yAgent -.-> MetricsAgent
    
    LoggingAgent -->|Uses| LoggingMCP[logging-mcp-server]
    TraceAgent -->|Uses| TraceMCP[trace-mcp-server]
    MetricsAgent -->|Uses| MetricsMCP[metrics-mcp-server]
    
    LoggingMCP -->|Queries| GCP_Logging[(Cloud Logging)]
    TraceMCP -->|Queries| GCP_Trace[(Cloud Trace)]
    MetricsMCP -->|Queries| GCP_Metrics[(Cloud Monitoring)]
```

## Components

### 1. SRE Helper (Root Agent)
- **File**: `sre-helper/app/agent.py`
- **Role**: Orchestrator for SRE incidents.
- **Model**: `gemini-2.5-flash`
- **Function**: Gathers incident details from the user and delegates the investigation to the `o11y-agent`.

### 2. Observability Agent (o11y-agent)
- **File**: `o11y-agent/app/agent.py`
- **Role**: Specialist agent for observability tasks.
- **Type**: `App` wrapping an `Agent`
- **Function**: Exposed as an A2A (Agent-to-Agent) server. It currently serves the **Logging Agent** directly to satisfy Vertex AI Reasoning Engine deployment expectations.
  > [!NOTE]
  > In the current implementation, this agent directly exposes the **Logging Agent** as the root of the app to avoid attribute validation failures (like missing `plugins` or `resumability_config`) observed when using `ParallelAgent` or raw agents without the `App` wrapper.

### 3. Specialist Agents
All specialist agents use `gemini-2.5-flash`.

- **Logging Agent**: Specialized in analyzing logs. Uses `logging-mcp-server`.
- **Trace Agent**: Specialized in analyzing traces. Uses `trace-mcp-server`.
- **Metrics Agent**: Specialized in analyzing metrics. Uses `metrics-mcp-server`.

### 4. MCP Servers
These servers provide tools for the agents to interact with Google Cloud services.
- **logging-mcp-server**: Tools for querying Cloud Logging.
- **trace-mcp-server**: Tools for querying Cloud Trace.
- **metrics-mcp-server**: Tools for querying Cloud Monitoring.

## Data Flow

1. The user interacts with the `sre-helper` agent describing an incident.
2. `sre-helper` identifies that it needs observability data and calls the `o11y-agent` (retrieved via `AgentRegistry`).
3. `o11y-agent` orchestrates the request among its sub-agents (Logging, Trace, Metrics).
4. Each sub-agent uses its specific MCP tool to query Google Cloud.
5. The results are aggregated and returned back to `sre-helper`, which then provides a consolidated response to the user.

## Security & Permissions

### Agent Identity and Access Control

When deployed to Vertex AI Reasoning Engine, agents need permissions to access the Agent Registry, query logs, and invoke MCP tools.

#### 1. SPIFFE Identity (Workload Identity Federation)
In this project environment, Reasoning Engines are identified by a SPIFFE-formatted principal rather than a standard service account.

**Format:**
`principal://agents.global.org-888160148396.system.id.goog/resources/aiplatform/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<REASONING_ENGINE_ID>`

**Required Roles:**
- **Agent Registry Viewer** (`roles/agentregistry.viewer`): To resolve remote agents and MCP servers.
- **Logging Viewer** (`roles/logging.viewer`): To query Cloud Logging.
- **MCP Tool User** (`roles/mcp.toolUser`): To invoke MCP tools.

**Example Commands:**
```bash
# Grant Logging Viewer
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="principal://agents.global.org-888160148396.system.id.goog/resources/aiplatform/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<REASONING_ENGINE_ID>" \
    --role="roles/logging.viewer"

# Grant MCP Tool User
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="principal://agents.global.org-888160148396.system.id.goog/resources/aiplatform/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<REASONING_ENGINE_ID>" \
    --role="roles/mcp.toolUser"
```

#### 2. Service Account Identity (Fallback)
If the agent falls back to using the Platform Service Agent identity, the following configuration applies:

**Principal:** `service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`

**Example Command:**
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/agentregistry.viewer"
```

#### 3. Enabling Agent Identity during Deployment
To ensure the agent is provisioned with a SPIFFE identity, you must specify `identity_type: AGENT_IDENTITY` when creating the agent instance.

**Using Python SDK:**
```python
from vertexai import types

remote_app = client.agent_engines.create(
  agent=app,
  config={
    "display_name": "running-agent-with-identity",
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    ...
  },
)
```

**Using `agents-cli`:**
Add `identity_type = "AGENT_IDENTITY"` to the `[tool.agents-cli.create_params]` section in your `pyproject.toml`:

```toml
[tool.agents-cli.create_params]
deployment_target = "agent_engine"
identity_type = "AGENT_IDENTITY"
```

#### 4. Recommended Deployment Method (Custom SDK Script)
Since `agents-cli` may not support setting the `identity_type` correctly via configuration files, a custom Python script is provided to deploy agents with Agent Identity enabled.

The script is located at `scripts/deploy.py`.

**To deploy an agent:**
1. Navigate to the agent's directory (to use its specific environment).
2. Run the script pointing to the current directory (`.`):

**For `o11y-agent`:**
```bash
cd o11y-agent
uv sync
uv run python ../scripts/deploy.py .
```

**For `sre-helper`:**
```bash
cd sre-helper
uv sync
uv run python ../scripts/deploy.py .
```
