"""Deployment script for the o11y-agent to Vertex AI Agent Engine.

Usage::

    uv run python deploy.py               # create / deploy
    uv run python deploy.py --delete ID   # delete a deployed resource

Environment variables (required unless noted):

* ``GOOGLE_CLOUD_PROJECT`` - target project id.
* ``GOOGLE_CLOUD_STORAGE_BUCKET`` - staging bucket name (no ``gs://`` prefix).
* ``GOOGLE_CLOUD_LOCATION`` - optional; defaults to ``us-central1``.

This script follows the "Temp Directory Trick" from
``docs/deployment_patterns.md`` section 1: it stages a copy of the ``app/``
package into a temporary directory *outside* the project directory so that
``cloudpickle`` preserves the full ``app.*`` module path in the deployed
artifact and ``shutil.copytree`` cannot recurse into its own destination.
"""

import os
import shutil
import sys
import tempfile

import vertexai
from dotenv import load_dotenv
from vertexai import types


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Environment variable {name} is required")
    return v


def main() -> None:
    load_dotenv()

    project_id = _require_env("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    bucket = _require_env("GOOGLE_CLOUD_STORAGE_BUCKET")

    print(f"PROJECT: {project_id}\nLOCATION: {location}\nBUCKET: {bucket}")

    client = vertexai.Client(
        project=project_id,
        location=location,
        http_options=dict(api_version="v1beta1"),
    )

    agent_path = os.path.abspath(os.path.dirname(__file__))

    # Use tempfile.TemporaryDirectory OUTSIDE agent_path so shutil.copytree
    # cannot recurse into its own destination.
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Recreate the app/ package structure per deployment_patterns.md §1
        app_dst = os.path.join(tmp_dir, "app")
        app_src = os.path.join(agent_path, "app")
        shutil.copytree(app_src, app_dst)

        # Write requirements.txt into tmp_dir (kept in sync with
        # requirements.txt / pyproject.toml in the project root).
        requirements = [
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-adk>=1.30.0",
            "a2a-sdk>=0.3.26",
            "pydantic",
            "cloudpickle",
            "python-dotenv",
            "google-cloud-logging",
            "google-cloud-iamconnectorcredentials",
            "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
        ]
        requirements_path = os.path.join(tmp_dir, "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write("\n".join(requirements) + "\n")

        # Put tmp_dir on sys.path so cloudpickle resolves `app.*` to the
        # staged copy (not the in-tree one) and clear any stale imports.
        sys.path.insert(0, tmp_dir)
        for m in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[m]

        from app.agent_engine_app import get_app

        app = get_app()

        print("Deploying o11y-agent with Agent Identity...")
        remote_app = client.agent_engines.create(
            agent=app,
            config={
                "display_name": "o11y-agent",
                "identity_type": types.IdentityType.AGENT_IDENTITY,
                "staging_bucket": f"gs://{bucket}",
                "requirements": requirements,
                "extra_packages": [os.path.join(tmp_dir, "app")],
            },
        )
        print(f"Deployment successful. Engine ID: {remote_app.api_resource.name}")


def _delete(resource_id: str) -> None:
    from vertexai import agent_engines

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai.init(project=project_id, location=location)
    agent_engines.get(resource_id).delete(force=True)
    print(f"Deleted: {resource_id}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        if len(sys.argv) < 3:
            print("Usage: python deploy.py --delete <resource_id>")
            sys.exit(1)
        _delete(sys.argv[2])
    else:
        main()
