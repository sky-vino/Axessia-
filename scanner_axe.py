from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from ai_explainer import explain_rule
from rules_registry import RULES

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js"

PAGE_LOAD_TIMEOUT  = 30000
GLOBAL_SCAN_TIMEOUT = 60
MAX_RESPONSE_SIZE  = 5_000_000

AXE_IMPACT_TO_SEVERITY = {
    "critical": "critical",
    "serious":  "serious",
    "moderate": "moderate",
    "minor":    "minor",
}

BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
]


def derive_wcag(tags: list[str]) -> str | None:
    for tag in tags:
        if "." in tag:
            return tag
    return None


def _normalize_axe_results(axe: dict, url: str) -> dict:
    axe_rules = {}

    for v in axe.get("violations", []):
        axe_rules[v["id"]] = {
            "status": "fail",
            "help":   v["help"],
            "impact": v.get("impact", "moderate"),
            "tags":   v.get("tags", []),
            "nodes":  v.get("nodes", []),
        }

    for p in axe.get("passes", []):
        axe_rules.setdefault(p["id"], {
            "status": "pass",
            "help":   p["help"],
            "impact": "minor",
            "tags":   p.get("tags", []),
            "nodes":  [],
        })

    results  = []
    seen_ids = set()

    for rule in RULES:
        axe_data = axe_rules.get(rule["id"])
        if axe_data:
            status    = axe_data["status"]
            instances = [{"snippet": n.get("html"), "target": n.get("target")} for n in axe_data["nodes"]]
        else:
            status    = rule["test_type"]
            instances = []

        result = {
            "id": rule["id"], "name": rule["name"],
            "wcag": rule.get("wcag"), "level": rule.get("level"),
            "test_type": rule["test_type"], "severity": rule["severity"],
            "status": status, "instances": instances,
            "instance_count": len(instances),
        }
        if status in ("fail", "assisted", "manual"):
            result["ai_explanation"] = explain_rule(rule=result, page_url=url)
        results.append(result)
        seen_ids.add(rule["id"])

    for axe_id, axe_data in axe_rules.items():
        if axe_id in seen_ids:
            continue
        wcag      = derive_wcag(axe_data["tags"])
        severity  = AXE_IMPACT_TO_SEVERITY.get(axe_data["impact"], "moderate")
        instances = [{"snippet": n.get("html"), "target": n.get("target")} for n in axe_data["nodes"]]
        result = {
            "id": axe_id, "name": axe_data["help"],
            "wcag": wcag, "level": "A/AA",
            "test_type": "automated", "severity": severity,
            "status": axe_data["status"], "instances": instances,
            "instance_count": len(instances),
        }
        if axe_data["status"] == "fail":
            result["ai_explanation"] = explain_rule(rule=result, page_url=url)
        results.append(result)

    return {"rules": results}


def run_scan(url: str) -> dict:
    """Public URL scan — no authentication. Used by FastAPI /scan endpoint."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(user_agent="Axessia-Scanner/1.0", ignore_https_errors=True)
            context.set_default_timeout(PAGE_LOAD_TIMEOUT)
            page = context.new_page()
            page.route("**/*", lambda route, request: (
                route.abort() if request.url.startswith(("file:", "data:")) else route.continue_()
            ))
            try:
                page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                browser.close()
                return {"error": "Page load timed out."}
            except Exception as e:
                browser.close()
                return {"error": f"Page load failed: {str(e)}"}

            if len(page.content()) > MAX_RESPONSE_SIZE:
                browser.close()
                return {"error": "Page too large to scan safely."}

            page.add_script_tag(url=AXE_CDN)
            try:
                axe = page.evaluate("async () => { return await axe.run(document); }")
            except Exception as e:
                browser.close()
                return {"error": f"Axe execution failed: {str(e)}"}
            browser.close()
    except Exception as e:
        return {"error": f"Scanner crashed: {str(e)}"}

    return _normalize_axe_results(axe, url)


def run_scan_with_cookies(url: str, storage_state: dict) -> dict:
    """
    Authenticated scan — injects saved session cookies so Playwright
    lands on the real page, not the login redirect.

    storage_state: dict from auth_flow.phase2_submit_otp()
    Called directly from app_wsc.py (NOT via FastAPI).
    """
    axe = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                storage_state=storage_state,
                user_agent="Axessia-Scanner/1.0",
                ignore_https_errors=True,
            )
            context.set_default_timeout(PAGE_LOAD_TIMEOUT)
            page = context.new_page()
            page.route("**/*", lambda route, request: (
                route.abort() if request.url.startswith(("file:", "data:")) else route.continue_()
            ))

            try:
                page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                browser.close()
                return {"error": "Page load timed out."}
            except Exception as e:
                browser.close()
                return {"error": f"Page load failed: {str(e)}"}

            # Detect session expiry — server redirected us back to login
            landed_url = page.url
            auth_keywords = ["login", "signin", "otp", "verify", "auth", "token"]
            if any(kw in landed_url.lower() for kw in auth_keywords):
                browser.close()
                return {
                    "error": (
                        f"Session expired — redirected to: {landed_url}. "
                        "Please log in again using the Authenticated Scan panel."
                    ),
                    "session_expired": True,
                }

            if len(page.content()) > MAX_RESPONSE_SIZE:
                browser.close()
                return {"error": "Page too large to scan safely."}

            page.add_script_tag(url=AXE_CDN)
            try:
                axe = page.evaluate("async () => { return await axe.run(document); }")
            except Exception as e:
                browser.close()
                return {"error": f"Axe execution failed: {str(e)}"}
            browser.close()

    except Exception as e:
        return {"error": f"Authenticated scanner crashed: {str(e)}"}

    return _normalize_axe_results(axe, url)
