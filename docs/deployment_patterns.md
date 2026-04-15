# Deployment Patterns and Troubleshooting

This document captures the lessons learned and solutions applied during the deployment of AutoSRE agents to Vertex AI Agent Engine (Reasoning Engine).

## 1. ModuleNotFoundError: No module named 'app.agent'

### The Problem
When deploying agents using the Vertex AI SDK (`client.agent_engines.create`), the source code is packaged and uploaded. If the local directory structure is not preserved exactly during pickling, `cloudpickle` may fail to resolve module paths in the remote container, leading to `ModuleNotFoundError`.

This is common when using `extra_packages` or staging files in a way that flattens the directory structure.

### The Solution: The "Temp Directory Trick"
To ensure that `cloudpickle` preserves the full module path (e.g., `app.agent`), we use a structured temporary directory during deployment:

1.  Create a temporary directory.
2.  Recreate the desired package structure inside it (e.g., `temp_dir/app/...`).
3.  Add `temp_dir` to `sys.path` before importing the agent object.
4.  Perform the deployment using the Vertex AI SDK.

Example implementation in `scripts/deploy.py`:
```python
# Create structured temp dir
with tempfile.TemporaryDirectory() as temp_dir:
    app_dir = os.path.join(temp_dir, "app")
    os.makedirs(app_dir)
    
    # Copy source files to recreate package structure
    # ...
    
    # Add temp_dir to path to force correct module resolution
    sys.path.insert(0, temp_dir)
    from app import agent
    
    # Deploy using the imported agent
    # ...
```

## 2. IAM Permissions for A2A and MCP Tools

### Agent Identity (SPIFFE)
Modern Reasoning Engine deployments use a per-agent SPIFFE identity (Workload Identity) rather than a standard service account. This allows for granular, resource-specific permissions.

The SPIFFE identity format:
`principal://agents.global.org-{ORGANIZATION_ID}.system.id.goog/resources/aiplatform/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}`

### Required Roles
To enable full functionality, including Agent-to-Agent (A2A) calls and MCP tool usage, the following roles must be granted to the agent's identity:

*   **`roles/aiplatform.user`**: Essential for `aiplatform.reasoningEngines.query`. Required for **both** the caller (to invoke another agent) and the specialist (to call tools).
*   **`roles/agentregistry.viewer`**: Required to resolve remote agents and MCP servers by name in the discovery service.
*   **`roles/mcp.toolUser`**: Required to invoke MCP tools.
*   **`roles/logging.viewer`**: Required to query Cloud Logging.
*   **`roles/cloudtrace.viewer`**: Required for the Cloud Trace MCP server.
*   **`roles/monitoring.viewer`**: Required for the Monitoring MCP server.
*   **`roles/errorreporting.viewer`**: Required for the Error Reporting MCP server.

### Setup Script
Use `scripts/setup_iam.sh` to automate the granting of these roles. Note that `roles/aiplatform.user` was added to this script to support A2A communication.

## 3. Current State (April 2026)

### Active Agents
*   **`o11y-agent`**: Observability agent with tools for Logging, Tracing, Monitoring, and Error Reporting.
*   **`sre-helper`**: Orchestrator agent that uses A2A to call specialized agents.

### Deployed Instances
*   **`o11y-agent`**: Reasoning Engine ID `2769617563565424640`
*   **`sre-helper`**: Reasoning Engine ID `775930303523848192`

Both agents are currently being redeployed using the "Temp Directory Trick" to resolve module pathing issues. Permissions have been granted to their respective SPIFFE identities.
