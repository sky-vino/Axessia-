#!/bin/bash
# ======================================================
# AXESSIA – Azure App Service Startup Script
# ======================================================

set -e

echo "========================================="
echo "  AXESSIA – Starting on Azure App Service"
echo "========================================="

# ── Playwright Chromium ────────────────────────────────
export PLAYWRIGHT_BROWSERS_PATH=/home/playwright-browsers

echo "[1/3] Installing Playwright Chromium..."
playwright install chromium
playwright install-deps chromium
echo "      Done."

# ── FastAPI on internal port 8001 ─────────────────────
echo "[2/3] Starting FastAPI on port 8001..."
uvicorn api_worker:app --host 127.0.0.1 --port 8001 --workers 1 &
sleep 3
echo "      FastAPI started."

# ── Streamlit on public port 8000 ─────────────────────
echo "[3/3] Starting Streamlit on port 8000..."
streamlit run app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
