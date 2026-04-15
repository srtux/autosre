#!/bin/bash
# Setup IAM permissions for AutoSRE agents

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <PROJECT_ID> <PROJECT_NUMBER>"
  exit 1
fi

PROJECT_ID=$1
PROJECT_NUMBER=$2

echo "Granting roles/agentregistry.viewer to AI Platform service agent..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/agentregistry.viewer"

echo "Done."
