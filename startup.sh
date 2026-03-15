#!/bin/bash
# ======================================================
# AXESSIA – Azure App Service Startup Script
# ======================================================
# In Azure Portal → App Service → Configuration →
# General Settings → Startup Command:
#   bash startup.sh
# ======================================================

set -e

echo "============================================"
echo "  AXESSIA – Starting on Azure App Service"
echo "============================================"

# ── Persist Playwright browsers in /home so they
#    survive restarts (but require reinstall after redeploy)
export PLAYWRIGHT_BROWSERS_PATH=/home/playwright-browsers

echo "[1/3] Installing Playwright Chromium browser..."
playwright install chromium
playwright install-deps chromium
echo "      Done."

# ── Start FastAPI on internal port 8001 ──────────────
echo "[2/3] Starting FastAPI (port 8001, internal only)..."
uvicorn api_worker:app \
  --host 127.0.0.1 \
  --port 8001 \
  --workers 1 &
FASTAPI_PID=$!
echo "      FastAPI PID: $FASTAPI_PID"

# Give FastAPI time to bind before Streamlit starts
sleep 3

# ── Start Streamlit on public port 8000 ──────────────
echo "[3/3] Starting Streamlit (port 8000, public)..."
streamlit run app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false

# If Streamlit exits, stop FastAPI too
kill $FASTAPI_PID 2>/dev/null || true
