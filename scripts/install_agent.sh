#!/usr/bin/env bash
set -euo pipefail

# Simple installer for the KWS Agent
# Usage:
#   ./scripts/install_agent.sh --panel-url https://cp.karve.fun --agent-token <TOKEN> --server-name "My Remote Server"

PANEL_URL=""
AGENT_TOKEN=""
SERVER_NAME="remote-server"
IMAGE="kws-agent:latest"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --panel-url)
      PANEL_URL="$2"
      shift 2
      ;;
    --agent-token)
      AGENT_TOKEN="$2"
      shift 2
      ;;
    --server-name)
      SERVER_NAME="$2"
      shift 2
      ;;
    --image)
      IMAGE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$AGENT_TOKEN" ]]; then
  echo "--agent-token is required"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

echo "Pulling agent image ${IMAGE}"
docker pull "${IMAGE}" || true

echo "Starting agent container"
docker run -d --restart unless-stopped \
  --name kws-agent \
  -e AGENT_TOKEN="${AGENT_TOKEN}" \
  -e SERVER_NAME="${SERVER_NAME}" \
  -p 8001:8001 \
  "${IMAGE}" || docker restart kws-agent

echo "Agent installed. Configure the panel at ${PANEL_URL:-your control panel} to use the agent URL: http://<server-ip>:8001"
