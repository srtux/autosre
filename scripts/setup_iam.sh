#!/bin/bash
# Setup IAM permissions for AutoSRE agents

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <PROJECT_ID> <PROJECT_NUMBER> [REASONING_ENGINE_ID]"
  echo "If REASONING_ENGINE_ID is provided, grants roles to the SPIFFE identity."
  echo "Otherwise, grants roles to the Platform Service Agent."
  exit 1
fi

PROJECT_ID=$1
PROJECT_NUMBER=$2
REASONING_ENGINE_ID=$3

if [ -n "$REASONING_ENGINE_ID" ]; then
  MEMBER="principal://agents.global.org-888160148396.system.id.goog/resources/aiplatform/projects/$PROJECT_NUMBER/locations/us-central1/reasoningEngines/$REASONING_ENGINE_ID"
  echo "Using SPIFFE identity: $MEMBER"
else
  MEMBER="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  echo "Using Service Account identity: $MEMBER"
fi

echo "Granting roles..."

# Grant Agent Registry Viewer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$MEMBER" \
    --role="roles/agentregistry.viewer"

# Grant Logging Viewer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$MEMBER" \
    --role="roles/logging.viewer"

# Grant MCP Tool User
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$MEMBER" \
    --role="roles/mcp.toolUser"

echo "Done."

