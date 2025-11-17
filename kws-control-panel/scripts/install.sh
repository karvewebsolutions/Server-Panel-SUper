#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

if ! command -v docker-compose &> /dev/null; then
  echo "Installing docker-compose..."
  DOCKER_COMPOSE_VERSION="2.29.7"
  curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

echo "Starting KWS Control Panel stack..."
cd "$(dirname "$0")/../infra"
docker-compose up -d --build
