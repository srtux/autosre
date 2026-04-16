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

"""Deploy ``sre-helper`` to Vertex AI Agent Engine.

Usage::

    uv run python deployment/deploy.py             # create / update
    uv run python deployment/deploy.py --delete <resource_id>

Required env vars:

* ``GOOGLE_CLOUD_PROJECT`` — GCP project ID.
* ``GOOGLE_CLOUD_STORAGE_BUCKET`` — staging bucket (no ``gs://`` prefix).

Optional:

* ``GOOGLE_CLOUD_LOCATION`` (default ``us-central1``).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

import vertexai
from dotenv import load_dotenv
from vertexai import types

from sre_helper.agent import get_app
from sre_helper.app_utils.telemetry import setup_telemetry

REQUIREMENTS = [
    "google-adk>=1.30.0",
    "google-cloud-aiplatform[evaluation,agent-engines]>=1.130.0",
    "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
    "gcsfs>=2024.11.0",
    "google-cloud-logging>=3.12.0,<4.0.0",
    "protobuf>=6.31.1,<7.0.0",
    "a2a-sdk>=0.3.26",
    "python-dotenv>=1.0.0",
    "pydantic",
    "cloudpickle",
]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Missing required environment variable: {name}. "
            "See deployment/deploy.py docstring."
        )
    return value


def _stage_source(agent_path: str) -> str:
    """Recreate the package layout inside a temporary directory so
    ``cloudpickle`` resolves ``sre_helper.*`` module paths on the remote side
    (see docs/deployment_patterns.md §1)."""
    tmp_dir = tempfile.mkdtemp(prefix="sre-helper-deploy-")
    pkg_src = os.path.join(agent_path, "sre_helper")
    pkg_dst = os.path.join(tmp_dir, "sre_helper")
    shutil.copytree(pkg_src, pkg_dst)
    return tmp_dir


def create(project_id: str, location: str, bucket: str) -> None:
    """Deploy the agent to Vertex AI Agent Engine."""
    setup_telemetry()

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    client = vertexai.Client(
        project=project_id,
        location=location,
        http_options={"api_version": "v1beta1"},
    )

    # ``get_app()`` returns an AgentEngineApp (AdkApp subclass) with
    # register_feedback already exposed via register_operations().
    app = get_app()

    agent_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    tmp_dir = _stage_source(agent_path)

    requirements_path = os.path.join(tmp_dir, "requirements.txt")
    with open(requirements_path, "w") as fh:
        for req in REQUIREMENTS:
            fh.write(req + "\n")

    try:
        remote_app = client.agent_engines.create(
            agent=app,
            config={
                "display_name": "sre-helper",
                "identity_type": types.IdentityType.AGENT_IDENTITY,
                "source_packages": [tmp_dir, requirements_path],
                "staging_bucket": f"gs://{bucket}",
            },
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("Deployment successful for sre-helper!")
    print(f"Agent Engine resource: {remote_app.api_resource.name}")


def delete(project_id: str, location: str, bucket: str, resource_id: str) -> None:
    """Delete a deployed agent engine instance."""
    from vertexai import agent_engines

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")


def main() -> None:
    load_dotenv()

    project_id = _require_env("GOOGLE_CLOUD_PROJECT")
    bucket = _require_env("GOOGLE_CLOUD_STORAGE_BUCKET")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        if len(sys.argv) < 3:
            raise SystemExit("Usage: python deploy.py --delete <resource_id>")
        delete(project_id, location, bucket, sys.argv[2])
    else:
        create(project_id, location, bucket)


if __name__ == "__main__":
    main()
