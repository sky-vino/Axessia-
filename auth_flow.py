# ======================================================
# AXESSIA – Sky Authenticated Login Flow
#
# Sky's WAF blocks requests from Azure/cloud IPs so
# automated browser login from Azure is not possible.
#
# Solution: Cookie Import
#   1. User logs in manually in their own browser
#   2. User exports cookies using a browser extension
#   3. Axessia uses those cookies to scan — no login
#      attempt from Azure needed at all.
# ======================================================

import json
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT = 30_000


# ======================================================
# PARSE COOKIES — accepts multiple formats
# ======================================================

def parse_cookies(raw_input: str) -> dict | None:
    """
    Accepts cookies in any of these formats:

    Format 1 — JSON array (EditThisCookie / Cookie-Editor export):
    [{"name":"session","value":"abc","domain":".sky.it",...}, ...]

    Format 2 — JSON object (key:value pairs):
    {"session": "abc", "token": "xyz"}

    Format 3 — Plain cookie string (from browser DevTools):
    session=abc; token=xyz; other=value

    Returns Playwright storage_state dict or None on failure.
    """
    raw = raw_input.strip()
    if not raw:
        return None

    cookies = []

    # ── Format 1: JSON array ───────────────────────
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            for c in parsed:
                cookie = {
                    "name":   c.get("name", ""),
                    "value":  c.get("value", ""),
                    "domain": c.get("domain", ".sky.it"),
                    "path":   c.get("path", "/"),
                }
                # sameSite must be one of: "Strict", "Lax", "None"
                same_site = c.get("sameSite", "Lax")
                if same_site not in ("Strict", "Lax", "None"):
                    same_site = "Lax"
                cookie["sameSite"] = same_site
                if c.get("secure"):
                    cookie["secure"] = True
                if c.get("httpOnly"):
                    cookie["httpOnly"] = True
                if cookie["name"]:
                    cookies.append(cookie)
        except Exception:
            return None

    # ── Format 2: JSON object ──────────────────────
    elif raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            for name, value in parsed.items():
                cookies.append({
                    "name":     name,
                    "value":    str(value),
                    "domain":   ".sky.it",
                    "path":     "/",
                    "sameSite": "Lax",
                })
        except Exception:
            return None

    # ── Format 3: cookie string ────────────────────
    else:
        try:
            for part in raw.split(";"):
                part = part.strip()
                if "=" in part:
                    name, _, value = part.partition("=")
                    name  = name.strip()
                    value = value.strip()
                    if name:
                        cookies.append({
                            "name":     name,
                            "value":    value,
                            "domain":   ".sky.it",
                            "path":     "/",
                            "sameSite": "Lax",
                        })
        except Exception:
            return None

    if not cookies:
        return None

    return {"cookies": cookies, "origins": []}


# ======================================================
# VERIFY SESSION using imported cookies
# ======================================================

def verify_session_from_cookies(
    target_url: str,
    storage_state: dict,
) -> dict:
    """
    Navigates to target_url with injected cookies and checks
    whether we land on real content or get redirected to login.
    """
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

            landed_url  = page.url
            page_title  = page.title()
            browser.close()

            auth_keywords = ["login", "signin", "security", "otp", "auth", "error"]
            is_auth = any(kw in landed_url.lower() for kw in auth_keywords)

            return {
                "valid":      not is_auth,
                "landed_url": landed_url,
                "page_title": page_title,
            }
    except Exception as e:
        return {"valid": False, "landed_url": "", "error": str(e)}


# ======================================================
# LEGACY stubs — kept so app_wsc.py imports don't break
# ======================================================

def fully_automated_login(login_url, email, password):
    """
    Not used — Sky WAF blocks Azure IPs.
    Cookie import is used instead.
    """
    return {
        "success": False,
        "error": (
            "Direct login from Azure is blocked by Sky's firewall (WAF). "
            "Please use the Cookie Import method instead."
        ),
        "stage": "blocked",
    }


def phase2_manual_otp(otp_url, otp_code, storage_state):
    return {"success": False, "error": "Not applicable — use cookie import."}


def verify_session(target_url, storage_state):
    return verify_session_from_cookies(target_url, storage_state)