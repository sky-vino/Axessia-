# ======================================================
# AXESSIA – FastAPI Worker (Azure-Ready)
# Endpoints:
#   GET  /health
#   POST /scan          — web scanning via Playwright
#   POST /crawl         — multi-page crawl
#   POST /ingest-mobile — receive Android scan from local runner
#   GET  /mobile-results/{session_id} — dashboard polls this
#   DELETE /mobile-results/{session_id} — clear a session
# ======================================================

import os
import time
import socket
import ipaddress
from urllib.parse import urlparse
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from scanner_axe import run_scan
from crawl_orchestrator import crawl_site_sections

# ── Config ──────────────────────────────────────────────
API_KEY         = os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")
ALLOWED_ORIGINS = os.getenv(
    "AXESSIA_ALLOWED_ORIGINS",
    "http://localhost:8501,http://localhost:8000"
).split(",")
RATE_LIMIT  = int(os.getenv("AXESSIA_RATE_LIMIT",  "10"))
RATE_WINDOW = int(os.getenv("AXESSIA_RATE_WINDOW", "60"))

request_log: dict      = defaultdict(list)
_mobile_results: dict  = {}   # session_id → scan result

# ── App ─────────────────────────────────────────────────
app = FastAPI(title="Axessia API Worker", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["*"],
)

# ── Models ───────────────────────────────────────────────
class ScanRequest(BaseModel):
    url: HttpUrl

class CrawlRequest(BaseModel):
    seed_url: HttpUrl
    max_pages_per_section: int = 2

class MobileIngestRequest(BaseModel):
    session_id:  str
    app_package: str
    platform:    str  = "android"
    screens:     list
    app_risk:    str  = "unknown"
    device_id:   str  = ""
    scanned_at:  str  = ""

# ── Security utilities ───────────────────────────────────
def validate_url_security(url: str):
    parsed = urlparse(url)
    host   = parsed.hostname
    try:
        ip     = socket.gethostbyname(host)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
            raise HTTPException(status_code=400, detail="Blocked: internal address.")
        if ip == "169.254.169.254":
            raise HTTPException(status_code=400, detail="Blocked: metadata service.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or unresolvable host.")

def enforce_rate_limit(client_ip: str):
    now          = time.time()
    window_start = now - RATE_WINDOW
    request_log[client_ip] = [t for t in request_log[client_ip] if t > window_start]
    if len(request_log[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    request_log[client_ip].append(now)

# ── Auth middleware ──────────────────────────────────────
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/"):
        return await call_next(request)
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    enforce_rate_limit(request.client.host)
    return await call_next(request)

# ── Endpoints ────────────────────────────────────────────
@app.get("/")
def root():
    return {"service": "Axessia API Worker", "status": "ok", "version": "3.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scan")
def scan_url(payload: ScanRequest):
    url = str(payload.url)
    validate_url_security(url)
    try:
        return run_scan(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.post("/crawl")
def crawl_site(payload: CrawlRequest):
    seed_url = str(payload.seed_url)
    validate_url_security(seed_url)
    if not (1 <= payload.max_pages_per_section <= 5):
        raise HTTPException(status_code=400, detail="max_pages_per_section must be 1–5.")
    try:
        return crawl_site_sections(
            seed_url=seed_url,
            run_scan_func=run_scan,
            max_pages_per_section=payload.max_pages_per_section,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")

# ── Mobile endpoints ─────────────────────────────────────
@app.post("/ingest-mobile")
def ingest_mobile(payload: MobileIngestRequest):
    """
    Called by local_mobile_runner.py running on the tester's laptop.
    Stores results keyed by session_id so the dashboard can display them.
    """
    _mobile_results[payload.session_id] = {
        "session_id":  payload.session_id,
        "app_package": payload.app_package,
        "platform":    payload.platform,
        "screens":     payload.screens,
        "app_risk":    payload.app_risk,
        "device_id":   payload.device_id,
        "scanned_at":  payload.scanned_at,
    }
    return {
        "status":   "ok",
        "session_id": payload.session_id,
        "screens":  len(payload.screens),
    }

@app.get("/mobile-results/{session_id}")
def get_mobile_results(session_id: str):
    """Polled by app_msa.py dashboard to check if results have arrived."""
    result = _mobile_results.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="No results for this session yet.")
    return result

@app.delete("/mobile-results/{session_id}")
def delete_mobile_results(session_id: str):
    """Clear results for a completed session."""
    _mobile_results.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}
