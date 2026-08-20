#!/usr/bin/env bash
# ==============================================================================
# Offline LLM Assistant — Air-Gapped Installation & Startup Script
# ==============================================================================
set -euo pipefail

echo "============================================================"
echo " Starting Air-Gapped Offline LLM Assistant Deployment..."
echo "============================================================"

# 1. Enforce Air-Gap / Network Isolation Check
echo "[1/5] Verifying host network isolation..."
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "WARNING: Host has outbound internet connectivity."
    echo "In high-security production, disable external network interfaces."
else
    echo "Verified: No external internet route detected."
fi

# 2. Check Docker / Podman availability
echo "[2/5] Checking container runtime..."
if command -v docker >/dev/null 2>&1; then
    CONTAINER_CMD="docker"
elif command -v podman >/dev/null 2>&1; then
    CONTAINER_CMD="podman"
else
    echo "ERROR: Neither Docker nor Podman is installed on this host."
    exit 1
fi

# 3. Create required persistent storage directories
echo "[3/5] Initializing local storage and models directories..."
mkdir -p data/postgres data/qdrant data/storage models

# 4. Verify Docker Compose Environment
echo "[4/5] Preparing environment configuration..."
COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../compose" && pwd)"
if [ ! -f "${COMPOSE_DIR}/.env" ]; then
    if [ -f "${COMPOSE_DIR}/.env.example" ]; then
        cp "${COMPOSE_DIR}/.env.example" "${COMPOSE_DIR}/.env"
        echo "Created .env from .env.example"
    fi
fi

# 5. Start Containerized Services
echo "[5/5] Launching offline service containers..."
cd "${COMPOSE_DIR}"
${CONTAINER_CMD} compose up -d

echo ""
echo "============================================================"
echo " Deployment Complete!"
echo " Web UI:      http://localhost:3000"
echo " Backend API: http://localhost:8000"
echo " Health API:  http://localhost:8000/health"
echo "============================================================"
