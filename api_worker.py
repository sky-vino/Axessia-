# ======================================================
# AXESSIA – HARDENED API WORKER (ENTERPRISE MODE)
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

# ======================================================
# CONFIGURATION
# ======================================================

API_KEY = "super-secret-demo-key"
RATE_LIMIT = 5  # requests
RATE_WINDOW = 60  # seconds

# In-memory rate tracking
request_log = defaultdict(list)

# ======================================================
# FASTAPI APP
# ======================================================

app = FastAPI(
    title="Axessia API Worker",
    description="Enterprise-secure Accessibility scanning worker",
    version="2.0.0",
)

# ======================================================
# CORS – RESTRICTED
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ======================================================
# REQUEST MODELS
# ======================================================

class ScanRequest(BaseModel):
    url: HttpUrl


class CrawlRequest(BaseModel):
    seed_url: HttpUrl
    max_pages_per_section: int = 2


# ======================================================
# SECURITY UTILITIES
# ======================================================

def validate_url_security(url: str):
    """
    Prevent SSRF by blocking internal/private IP ranges.
    """
    parsed = urlparse(url)
    host = parsed.hostname

    try:
        ip = socket.gethostbyname(host)
        ip_obj = ipaddress.ip_address(ip)

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
        ):
            raise HTTPException(
                status_code=400,
                detail="Blocked internal or unsafe address.",
            )

        # Explicit Azure metadata block
        if ip == "169.254.169.254":
            raise HTTPException(
                status_code=400,
                detail="Blocked metadata service access.",
            )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unresolvable host.",
        )


def enforce_rate_limit(client_ip: str):
    now = time.time()
    window_start = now - RATE_WINDOW

    # Remove old requests
    request_log[client_ip] = [
        t for t in request_log[client_ip] if t > window_start
    ]

    if len(request_log[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )

    request_log[client_ip].append(now)


# ======================================================
# AUTH MIDDLEWARE
# ======================================================

@app.middleware("http")
async def security_middleware(request: Request, call_next):

    # Skip health check
    if request.url.path == "/health":
        return await call_next(request)

    # API Key validation
    api_key_header = request.headers.get("x-api-key")
    if api_key_header != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Rate limiting
    client_ip = request.client.host
    enforce_rate_limit(client_ip)

    return await call_next(request)


# ======================================================
# HEALTH CHECK
# ======================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ======================================================
# SECURE SCAN ENDPOINT
# ======================================================

@app.post("/scan")
def scan_url(payload: ScanRequest):

    url = str(payload.url)
    validate_url_security(url)

    try:
        return run_scan(url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}",
        )


# ======================================================
# SECURE CRAWL ENDPOINT
# ======================================================

@app.post("/crawl")
def crawl_site(payload: CrawlRequest):

    seed_url = str(payload.seed_url)
    validate_url_security(seed_url)

    if payload.max_pages_per_section < 1 or payload.max_pages_per_section > 5:
        raise HTTPException(
            status_code=400,
            detail="max_pages_per_section must be between 1 and 5",
        )

    try:
        return crawl_site_sections(
            seed_url=seed_url,
            run_scan_func=run_scan,
            max_pages_per_section=payload.max_pages_per_section,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Crawl failed: {str(e)}",
        )
