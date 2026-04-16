#!/bin/bash
# Setup IAM permissions for AutoSRE agents.
#
# Required env vars:
#   ORGANIZATION_ID    - GCP organization ID (used in the SPIFFE principal)
#   PROJECT_ID         - GCP project ID hosting the Reasoning Engine
#   PROJECT_NUMBER     - Numeric project number (for the SPIFFE principal)
#   REASONING_ENGINE_ID - Reasoning Engine ID for the deployed agent
#
# Optional env vars:
#   LOCATION           - GCP location (default: us-central1)
#   USE_SERVICE_ACCOUNT - If set to "true", bind roles to the Platform Service
#                         Agent fallback instead of the SPIFFE identity.

set -euo pipefail

: "${ORGANIZATION_ID:?ORGANIZATION_ID env var required}"
: "${PROJECT_ID:?PROJECT_ID env var required}"
: "${PROJECT_NUMBER:?PROJECT_NUMBER env var required}"

LOCATION="${LOCATION:-us-central1}"
USE_SERVICE_ACCOUNT="${USE_SERVICE_ACCOUNT:-false}"

if [ "${USE_SERVICE_ACCOUNT}" = "true" ]; then
  MEMBER="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  echo "Using Service Account identity: ${MEMBER}"
else
  : "${REASONING_ENGINE_ID:?REASONING_ENGINE_ID env var required (or set USE_SERVICE_ACCOUNT=true)}"
  MEMBER="principal://agents.global.org-${ORGANIZATION_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}"
  echo "Using SPIFFE identity: ${MEMBER}"
fi

echo "Granting roles on project ${PROJECT_ID}..."

ROLES=(
  "roles/agentregistry.viewer"
  "roles/logging.viewer"
  "roles/mcp.toolUser"
  "roles/cloudtrace.viewer"
  "roles/monitoring.viewer"
  "roles/errorreporting.viewer"
  "roles/aiplatform.user"
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="${ROLE}"
done

echo "Done."
