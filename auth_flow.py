# ======================================================
# AXESSIA – Cookie Import for Authenticated Scanning
# ======================================================
import json
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BROWSER_ARGS = [
    "--disable-dev-shm-usage", "--no-sandbox",
    "--disable-gpu", "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
PAGE_TIMEOUT = 30_000


def _sanitize_cookie(c: dict) -> dict | None:
    """
    Playwright setCookies ONLY accepts these exact fields:
    name, value, domain, path, expires, httpOnly, secure, sameSite

    Everything else (storeId, id, hostOnly, session, partitionKey,
    expirationDate, firstPartyDomain, etc.) causes a crash.
    We build a brand new dict with ONLY allowed fields.
    """
    name  = str(c.get("name", "")).strip()
    value = c.get("value", "")

    # Skip cookies with no name
    if not name:
        return None

    # ── Build clean cookie with ONLY Playwright-allowed fields ──
    clean = {
        "name":   name,
        "value":  str(value) if value is not None else "",
        "domain": str(c.get("domain") or ".sky.it"),
        "path":   str(c.get("path")   or "/"),
    }

    # expires — must be a float Unix timestamp
    exp = c.get("expires") or c.get("expirationDate") or c.get("expiry")
    if exp is not None:
        try:
            f = float(exp)
            if f > 0:
                clean["expires"] = f
        except (TypeError, ValueError):
            pass

    # httpOnly — only if explicitly True
    if c.get("httpOnly") is True:
        clean["httpOnly"] = True

    # secure — only if explicitly True
    if c.get("secure") is True:
        clean["secure"] = True

    # sameSite — must be exactly "Strict", "Lax", or "None"
    raw_ss = c.get("sameSite") or c.get("samesite") or ""
    if isinstance(raw_ss, str):
        raw_ss = raw_ss.strip().capitalize()
    clean["sameSite"] = raw_ss if raw_ss in ("Strict", "Lax", "None") else "Lax"

    return clean


def parse_cookies(raw_input: str) -> dict | None:
    """
    Accepts cookies in 3 formats:
    1. JSON array  — from Cookie-Editor / Cookie Manager export
    2. JSON object — key:value pairs
    3. Plain string — name=value; name2=value2
    Returns Playwright storage_state dict or None on failure.
    """
    raw = raw_input.strip()
    if not raw:
        return None

    cookies = []

    if raw.startswith("["):
        try:
            for c in json.loads(raw):
                clean = _sanitize_cookie(c)
                if clean:
                    cookies.append(clean)
        except Exception:
            return None

    elif raw.startswith("{"):
        try:
            for name, value in json.loads(raw).items():
                clean = _sanitize_cookie({"name": name, "value": str(value)})
                if clean:
                    cookies.append(clean)
        except Exception:
            return None

    else:
        try:
            for part in raw.split(";"):
                part = part.strip()
                if "=" in part:
                    name, _, value = part.partition("=")
                    clean = _sanitize_cookie({"name": name.strip(), "value": value.strip()})
                    if clean:
                        cookies.append(clean)
        except Exception:
            return None

    if not cookies:
        return None
    return {"cookies": cookies, "origins": []}


def verify_session_from_cookies(target_url: str, storage_state: dict) -> dict:
    """Check if cookies give access to target_url (not redirected to login)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                storage_state=storage_state,
                user_agent=USER_AGENT,
                ignore_https_errors=True,
            )
            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            landed_url = page.url
            page_title = page.title()
            browser.close()
            auth_kw = ["login", "signin", "security", "otp", "auth", "error"]
            return {
                "valid":      not any(kw in landed_url.lower() for kw in auth_kw),
                "landed_url": landed_url,
                "page_title": page_title,
            }
    except Exception as e:
        return {"valid": False, "landed_url": "", "error": str(e)}


# Legacy stubs so imports don't break
def verify_session(target_url, storage_state):
    return verify_session_from_cookies(target_url, storage_state)