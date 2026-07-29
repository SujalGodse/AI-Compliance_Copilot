#!/bin/bash
# =============================================================
# milvus_docker_setup.sh
# AI Compliance Copilot — Milvus Standalone GPU Server Setup
#
# Copy this file to CDAC PARAM Shavak (192.168.6.50) and run:
#   scp milvus_docker_setup.sh student15@192.168.6.50:~/
#   ssh student15@192.168.6.50 -p 22
#   bash ~/milvus_docker_setup.sh
# =============================================================

set -e

MILVUS_VERSION="v2.4.9"
MILVUS_PORT=19530
METRICS_PORT=9091

echo "============================================================"
echo "  Milvus Standalone Setup — CDAC PARAM Shavak"
echo "  Version : $MILVUS_VERSION"
echo "============================================================"

# ── Step 1: Check Docker ────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo "[!] Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "[OK] Docker installed. You may need to re-login for group changes."
fi

echo "[OK] Docker available: $(docker --version)"

# ── Step 2: Download Milvus standalone script ───────────────
echo "[START] Downloading Milvus standalone_embed.sh..."
wget -q "https://github.com/milvus-io/milvus/releases/download/${MILVUS_VERSION}/milvus-standalone-docker-compose.yml" \
     -O docker-compose-milvus.yml

# ── Step 3: Start Milvus Standalone ────────────────────────
echo "[START] Starting Milvus Standalone (ports $MILVUS_PORT, $METRICS_PORT)..."
docker compose -f docker-compose-milvus.yml up -d

# ── Step 4: Wait for healthy state ─────────────────────────
echo "[START] Waiting for Milvus to be healthy..."
for i in $(seq 1 30); do
    STATUS=$(curl -s http://localhost:${METRICS_PORT}/healthz 2>/dev/null || echo "")
    if echo "$STATUS" | grep -q "Success"; then
        echo "[OK] Milvus is healthy!"
        break
    fi
    echo "  ... waiting ($i/30)"
    sleep 3
done

# ── Step 5: Verify ─────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Milvus Status"
echo "============================================================"
docker ps --filter "name=milvus"
echo ""
curl -s http://localhost:${METRICS_PORT}/healthz | python3 -m json.tool 2>/dev/null || \
    echo "Health endpoint response: $(curl -s http://localhost:${METRICS_PORT}/healthz)"

echo ""
echo "[OK] Milvus Standalone is running on GPU server."
echo ""
echo "Now on your LOCAL machine, open the SSH tunnel:"
echo "  ssh -N -L 19530:localhost:19530 -L 9091:localhost:9091 student15@192.168.6.50 -p 22"
echo ""
echo "Then verify with:"
echo "  python milvus_setup.py"
