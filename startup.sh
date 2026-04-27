#!/bin/bash
set -e
echo "=== Axessia Startup ==="

# Install Playwright browsers if not already installed
export PLAYWRIGHT_BROWSERS_PATH=/home/playwright-browsers
if [ ! -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
    echo "[1/3] Installing Playwright Chromium..."
    playwright install chromium --with-deps 2>&1 | tail -5
fi
echo "[1/3] Playwright ready."

# Start FastAPI on port 8001
echo "[2/3] Starting FastAPI (port 8001)..."
cd /home/site/wwwroot
uvicorn api_worker:app --host 127.0.0.1 --port 8001 --workers 1 --timeout-keep-alive 120 &
API_PID=$!
sleep 4

# Verify api_worker started
if ! curl -sf http://127.0.0.1:8001/health > /dev/null; then
    echo "WARNING: api_worker health check failed — retrying in 5s..."
    sleep 5
fi
echo "[2/3] FastAPI started (PID $API_PID)."

# Start Streamlit on port 8000
echo "[3/3] Starting Streamlit (port 8000)..."
streamlit run app.py \
    --server.port 8000 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.maxUploadSize 50 \
    --browser.gatherUsageStats false
