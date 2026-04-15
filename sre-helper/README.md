# sre-helper

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: ADK development CLI - Install with `uv tool install agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install required packages and launch the local development environment:

```bash
agents-cli install && agents-cli dev
```

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli dev`     | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli test`     | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Engine                                                                |
| `agents-cli register-gemini-enterprise` | Register deployed agent to Gemini Enterprise                    |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra prod` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli upgrade` | Auto-upgrade to latest version while preserving customizations |
| `agents-cli extract` | Extract minimal, shareable version of your agent |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli dev` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli enhance`.
To set up your production infrastructure, run `agents-cli infra prod`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

## Documentation

Central documentation is located in the `docs/` folder at the root of the repository.
- [System Architecture](../docs/architecture.md)
- [Observability Query Guidelines](../docs/observability_queries.md)
