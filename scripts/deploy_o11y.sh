#!/bin/bash
# Deploy o11y-agent with required environment variables

if [ -z "$1" ]; then
  echo "Usage: $0 <PROJECT_ID>"
  exit 1
fi

PROJECT_ID=$1
REGION="us-central1"

echo "Setting environment variables for deployment..."
export OTEL_SEMCONV_STABILITY_OPT_IN="gen_ai_latest_experimental"
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="true"

cd o11y-agent || exit 1

echo "Running deployment..."
uv run agents-cli deploy --project="$PROJECT_ID" --region="$REGION"
