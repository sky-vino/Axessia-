# api_worker.py — Axessia FastAPI Worker v4.0

import os, time, socket, ipaddress
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from scanner_axe import run_scan
from crawl_orchestrator import crawl_site_sections

API_KEY    = os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")
RATE_LIMIT = int(os.getenv("AXESSIA_RATE_LIMIT", "20"))
RATE_WINDOW= int(os.getenv("AXESSIA_RATE_WINDOW", "60"))

request_log:    dict = defaultdict(list)
_mobile_results: dict = {}

app = FastAPI(title="Axessia API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ScanRequest(BaseModel):
    url: HttpUrl

class CrawlRequest(BaseModel):
    seed_url: HttpUrl
    max_pages_per_section: int = 2

class MobileIngestRequest(BaseModel):
    session_id: str; app_package: str; platform: str = "android"
    screens: list; app_risk: str = "unknown"; device_id: str = ""; scanned_at: str = ""

class ExtensionIngestRequest(BaseModel):
    url: str; violations: list; passes: list
    source: str = "chrome-extension"; scanned_at: str = ""

def _validate_url(url: str):
    from urllib.parse import urlparse
    host = urlparse(url).hostname
    try:
        ip = socket.gethostbyname(host)
        obj = ipaddress.ip_address(ip)
        if obj.is_private or obj.is_loopback: raise HTTPException(400, "Blocked: internal address.")
        if ip == "169.254.169.254": raise HTTPException(400, "Blocked: metadata service.")
    except HTTPException: raise
    except Exception: raise HTTPException(400, "Invalid host.")

def _rate_limit(ip: str):
    now = time.time()
    request_log[ip] = [t for t in request_log[ip] if t > now - RATE_WINDOW]
    if len(request_log[ip]) >= RATE_LIMIT: raise HTTPException(429, "Rate limit exceeded.")
    request_log[ip].append(now)

@app.middleware("http")
async def auth(request: Request, call_next):
    if request.url.path in ("/health", "/", "/docs", "/openapi.json"): return await call_next(request)
    if request.headers.get("x-api-key") != API_KEY: raise HTTPException(401, "Unauthorized")
    _rate_limit(request.client.host)
    return await call_next(request)

@app.get("/")
def root(): return {"service": "Axessia API", "status": "ok", "version": "4.0.0"}

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/scan")
def scan_url(payload: ScanRequest):
    url = str(payload.url)
    _validate_url(url)
    try: return run_scan(url)
    except Exception as e: raise HTTPException(500, f"Scan failed: {e}")

@app.post("/crawl")
def crawl_site(payload: CrawlRequest):
    seed = str(payload.seed_url)
    _validate_url(seed)
    if not 1 <= payload.max_pages_per_section <= 5: raise HTTPException(400, "max_pages_per_section must be 1-5")
    try: return crawl_site_sections(seed_url=seed, run_scan_func=run_scan, max_pages_per_section=payload.max_pages_per_section)
    except Exception as e: raise HTTPException(500, f"Crawl failed: {e}")

@app.post("/ingest-mobile")
def ingest_mobile(payload: MobileIngestRequest):
    _mobile_results[payload.session_id] = payload.dict()
    return {"status": "ok", "session_id": payload.session_id, "screens": len(payload.screens)}

@app.get("/mobile-results/{session_id}")
def get_mobile(session_id: str):
    r = _mobile_results.get(session_id)
    if not r: raise HTTPException(404, "No results yet.")
    return r

@app.delete("/mobile-results/{session_id}")
def del_mobile(session_id: str):
    _mobile_results.pop(session_id, None)
    return {"status": "cleared"}

@app.post("/ingest-extension")
def ingest_extension(payload: ExtensionIngestRequest):
    SEV = {"critical":"critical","serious":"serious","moderate":"moderate","minor":"minor"}
    rules = []
    for v in payload.violations:
        rules.append({"id":v.get("id",""),"name":v.get("help",""),"wcag":next((t for t in v.get("tags",[]) if "." in t),"—"),
            "level":"A/AA","test_type":"automated","severity":SEV.get(v.get("impact","moderate"),"moderate"),
            "status":"fail","instance_count":len(v.get("nodes",[])),"eaa_critical":False,
            "instances":[{"snippet":n.get("html",""),"target":n.get("target",[])} for n in v.get("nodes",[])[:5]]})
    for p in payload.passes:
        rules.append({"id":p.get("id",""),"name":p.get("help",""),"wcag":"—","level":"A/AA",
            "test_type":"automated","severity":"minor","status":"pass","instance_count":0,"instances":[]})
    score = round(len([r for r in rules if r["status"]=="pass"])/max(len(rules),1)*100,1)
    fails = len([r for r in rules if r["status"]=="fail"])
    try:
        from regression_tracker import save_snapshot, save_history
        from eaa_mapping import evaluate_eaa
        eaa = evaluate_eaa(rules)
        save_snapshot(payload.url, {"url":payload.url,"rules":rules}, score)
        save_history(payload.url, score, fails, eaa.get("risk_level","—"))
    except Exception: pass
    return {"status":"ok","url":payload.url,"violations":len(payload.violations),"score":score}
