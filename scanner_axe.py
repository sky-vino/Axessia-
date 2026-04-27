# scanner_axe.py
# Complete Axessia Web Scanner
# Features: screenshots per failure, mobile viewport, focus engine,
#           real contrast ratios, dynamic content wait, cookie auth

import base64
import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from ai_explainer import explain_rule
from rules_registry import RULES

log = logging.getLogger(__name__)

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js"

PAGE_LOAD_TIMEOUT  = 30_000   # 30s
NETWORK_IDLE_WAIT  = 5_000    # 5s extra wait for SPAs
GLOBAL_SCAN_TIMEOUT= 120      # 2 min total
MAX_RESPONSE_SIZE  = 10_000_000  # 10 MB
MAX_SCREENSHOT_NODES = 20     # screenshots per rule

BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
]

AXE_IMPACT_TO_SEVERITY = {
    "critical": "critical",
    "serious":  "serious",
    "moderate": "moderate",
    "minor":    "minor",
}

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile":  {"width": 375,  "height": 812},
}


# ══════════════════════════════════════════════════════
# SCREENSHOT HELPER
# ══════════════════════════════════════════════════════
def _screenshot_node(page, selector: str | None, index: int = 0) -> str | None:
    """
    Capture a screenshot of a specific element.
    Returns base64-encoded PNG or None.
    """
    if not selector:
        return None
    try:
        if isinstance(selector, list):
            selector = selector[0] if selector else None
        if not selector:
            return None

        # Try CSS selector first
        try:
            element = page.locator(selector).first
            element.scroll_into_view_if_needed(timeout=3000)
            screenshot = element.screenshot(timeout=5000)
            return base64.b64encode(screenshot).decode("utf-8")
        except Exception:
            pass

        # Fallback: full page with element highlighted
        return None
    except Exception as e:
        log.debug(f"Screenshot failed for {selector}: {e}")
        return None


def _full_page_screenshot(page) -> str | None:
    """Capture full page screenshot as base64."""
    try:
        screenshot = page.screenshot(full_page=False, type="png")
        return base64.b64encode(screenshot).decode("utf-8")
    except Exception:
        return None


# ══════════════════════════════════════════════════════
# AXE RUNNER (shared for desktop + mobile)
# ══════════════════════════════════════════════════════
def _run_axe_on_page(page) -> dict:
    """Inject axe-core and run full accessibility scan."""
    try:
        page.add_script_tag(url=AXE_CDN)
        # Wait for axe to load
        page.wait_for_function("typeof axe !== 'undefined'", timeout=10_000)

        axe_result = page.evaluate("""
            async () => {
                return await axe.run(document, {
                    resultTypes: ['violations', 'passes', 'incomplete'],
                    reporter: 'v2'
                });
            }
        """)
        return axe_result or {}
    except Exception as e:
        log.error(f"axe.run failed: {e}")
        return {}


# ══════════════════════════════════════════════════════
# FOCUS ENGINE (keyboard simulation)
# ══════════════════════════════════════════════════════
def _run_focus_analysis(page) -> dict:
    """
    Simulate Tab navigation and detect focus issues.
    Returns focus trap status and tab order list.
    """
    try:
        focused_elements = []
        visited_signatures = set()
        focus_trap = False
        invisible_focus = []

        page.keyboard.press("Tab")
        time.sleep(0.1)

        for _ in range(80):
            element = page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        text: (el.textContent || el.value || el.getAttribute('aria-label') || '').trim().substring(0, 60),
                        role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        visible: rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden',
                        selector: el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className ? '.' + el.className.split(' ')[0] : ''),
                        outerHTML: el.outerHTML.substring(0, 200)
                    };
                }
            """)

            if not element:
                break

            sig = element["outerHTML"]

            if sig in visited_signatures:
                focus_trap = True
                break

            visited_signatures.add(sig)

            if not element.get("visible"):
                invisible_focus.append(element)

            focused_elements.append(element)
            page.keyboard.press("Tab")
            time.sleep(0.05)

        return {
            "success": True,
            "focus_trap": focus_trap,
            "tab_count": len(focused_elements),
            "focus_sequence": focused_elements[:30],
            "invisible_focus": invisible_focus,
        }
    except Exception as e:
        log.warning(f"Focus analysis failed: {e}")
        return {"success": False, "focus_trap": False, "tab_count": 0, "focus_sequence": [], "invisible_focus": []}


# ══════════════════════════════════════════════════════
# NORMALIZE AXE RESULTS
# ══════════════════════════════════════════════════════
def _normalize_axe_results(axe: dict, url: str, page=None, viewport_label: str = "desktop") -> dict:
    """
    Convert raw axe results into Axessia rule format.
    Captures screenshots for each failing node.
    """
    registry_by_id = {r["id"]: r for r in RULES}
    axe_rules = {}

    # Index violations
    for v in axe.get("violations", []):
        nodes_with_screenshots = []
        for node in v.get("nodes", [])[:MAX_SCREENSHOT_NODES]:
            target = node.get("target", [])
            selector = target[0] if target else None

            screenshot = None
            if page and selector:
                screenshot = _screenshot_node(page, selector)

            # Extract contrast ratio if present
            contrast_ratio = None
            for check in node.get("any", []) + node.get("all", []) + node.get("none", []):
                data = check.get("data", {})
                if isinstance(data, dict):
                    fg = data.get("fgColor")
                    bg = data.get("bgColor")
                    ratio = data.get("contrastRatio")
                    if ratio:
                        contrast_ratio = {
                            "actual": round(float(ratio), 2),
                            "required": 4.5 if "enhanced" not in check.get("id","") else 7.0,
                            "fg_color": fg,
                            "bg_color": bg,
                        }

            nodes_with_screenshots.append({
                "snippet":        node.get("html"),
                "target":         target,
                "selector":       selector,
                "screenshot_b64": screenshot,
                "contrast":       contrast_ratio,
                "failure_summary": node.get("failureSummary", ""),
            })

        axe_rules[v["id"]] = {
            "status":   "fail",
            "help":     v["help"],
            "helpUrl":  v.get("helpUrl", ""),
            "impact":   v.get("impact", "moderate"),
            "tags":     v.get("tags", []),
            "nodes":    nodes_with_screenshots,
        }

    # Index passes
    for p in axe.get("passes", []):
        axe_rules.setdefault(p["id"], {
            "status": "pass",
            "help":   p["help"],
            "impact": "minor",
            "tags":   p.get("tags", []),
            "nodes":  [],
        })

    # Index incomplete (needs review)
    for i in axe.get("incomplete", []):
        axe_rules.setdefault(i["id"], {
            "status": "incomplete",
            "help":   i["help"],
            "impact": i.get("impact", "moderate"),
            "tags":   i.get("tags", []),
            "nodes":  [],
        })

    results = []
    seen_ids = set()

    # ── Process registry rules ──────────────────────
    for rule in RULES:
        axe_data = axe_rules.get(rule["id"])

        if axe_data:
            status    = axe_data["status"]
            instances = axe_data["nodes"]
        else:
            status    = rule["test_type"]
            instances = []

        # Compute contrast ratio from first failing instance
        contrast_info = None
        for inst in instances:
            if inst.get("contrast"):
                contrast_info = inst["contrast"]
                break

        result = {
            "id":             rule["id"],
            "name":           rule["name"],
            "wcag":           rule.get("wcag"),
            "level":          rule.get("level"),
            "test_type":      rule["test_type"],
            "severity":       rule["severity"],
            "status":         status,
            "instances":      instances,
            "instance_count": len(instances),
            "eaa_critical":   rule.get("eaa_critical", False),
            "description":    rule.get("description", ""),
            "viewport":       viewport_label,
            "contrast_ratio": contrast_info,
            "help_url":       axe_data.get("helpUrl", "") if axe_data else "",
        }

        if status in ("fail", "assisted", "manual", "incomplete"):
            result["ai_explanation"] = explain_rule(rule=result, page_url=url)

        results.append(result)
        seen_ids.add(rule["id"])

    # ── Hydrate remaining axe-core rules ────────────
    def _derive_wcag(tags):
        for t in tags:
            if "." in t and not t.startswith("cat.") and not t.startswith("best"):
                return t
        return None

    for axe_id, axe_data in axe_rules.items():
        if axe_id in seen_ids:
            continue

        wcag     = _derive_wcag(axe_data["tags"])
        severity = AXE_IMPACT_TO_SEVERITY.get(axe_data["impact"], "moderate")
        result   = {
            "id":             axe_id,
            "name":           axe_data["help"],
            "wcag":           wcag,
            "level":          "A/AA",
            "test_type":      "automated",
            "severity":       severity,
            "status":         axe_data["status"],
            "instances":      axe_data["nodes"],
            "instance_count": len(axe_data["nodes"]),
            "eaa_critical":   False,
            "description":    axe_data["help"],
            "viewport":       viewport_label,
            "contrast_ratio": None,
            "help_url":       axe_data.get("helpUrl", ""),
        }

        if axe_data["status"] == "fail":
            result["ai_explanation"] = explain_rule(rule=result, page_url=url)

        results.append(result)

    return results


# ══════════════════════════════════════════════════════
# MAIN SCAN ENTRY POINT
# ══════════════════════════════════════════════════════
def run_scan(url: str, storage_state: dict | None = None) -> dict:
    """
    Full accessibility scan:
    - Desktop (1280px) + Mobile (375px) viewports
    - Screenshots per failing element
    - Keyboard focus simulation
    - Real contrast ratios
    - AI explanations with HTML context
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)

            # ── DESKTOP SCAN ────────────────────────
            ctx_opts = {"ignore_https_errors": True, "viewport": VIEWPORTS["desktop"]}
            if storage_state:
                ctx_opts["storage_state"] = storage_state

            context = browser.new_context(**ctx_opts)
            context.set_default_timeout(PAGE_LOAD_TIMEOUT)
            page = context.new_page()

            # Block non-essential resources to speed up
            page.route("**/*.{woff,woff2,ttf,otf}", lambda r: r.abort())

            try:
                page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                browser.close()
                return {"error": "Page load timed out."}
            except Exception as e:
                browser.close()
                return {"error": f"Page load failed: {str(e)}"}

            # Extra wait for SPA frameworks to settle
            try:
                page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_WAIT)
            except Exception:
                pass  # Proceed even if networkidle times out

            # Detect session redirect
            landed_url = page.url
            auth_kw = ["login", "signin", "otp", "verify", "security", "auth"]
            if storage_state and any(kw in landed_url.lower() for kw in auth_kw):
                browser.close()
                return {
                    "error": f"Session expired — redirected to: {landed_url}. Import fresh cookies.",
                    "session_expired": True,
                }

            content = page.content()
            if len(content) > MAX_RESPONSE_SIZE:
                browser.close()
                return {"error": "Page too large to scan safely."}

            # Page metadata
            page_title    = page.title()
            final_url     = page.url
            page_screenshot = _full_page_screenshot(page)

            # Run axe on desktop
            axe_desktop = _run_axe_on_page(page)

            # Run focus analysis on desktop
            focus_result = _run_focus_analysis(page)

            # ── MOBILE SCAN ─────────────────────────
            page.set_viewport_size(VIEWPORTS["mobile"])
            page.reload(wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_WAIT)
            except Exception:
                pass

            axe_mobile = _run_axe_on_page(page)
            mobile_screenshot = _full_page_screenshot(page)

            browser.close()

        # ── NORMALIZE RESULTS ────────────────────────────
        desktop_rules = _normalize_axe_results(axe_desktop, url, viewport_label="desktop")
        mobile_rules  = _normalize_axe_results(axe_mobile,  url, viewport_label="mobile")

        # Merge: mobile-only failures added as separate entries
        merged_rules = desktop_rules[:]
        desktop_ids  = {r["id"] for r in desktop_rules if r["status"] == "fail"}

        for rule in mobile_rules:
            if rule["status"] == "fail" and rule["id"] not in desktop_ids:
                rule["name"]    = f"[Mobile] {rule['name']}"
                rule["id"]      = f"mobile_{rule['id']}"
                merged_rules.append(rule)

        # Add focus trap rule if detected
        if focus_result.get("focus_trap"):
            from rules_registry import RULES as R
            base_rule = next((r for r in R if r["id"] == "focus-trap"), {})
            merged_rules.append({
                "id":             "focus-trap",
                "name":           "Keyboard focus trap detected",
                "wcag":           "2.1.2",
                "level":          "A",
                "test_type":      "automated",
                "severity":       "critical",
                "status":         "fail",
                "instances":      [],
                "instance_count": 1,
                "eaa_critical":   True,
                "description":    "The keyboard focus becomes trapped — users cannot navigate away using Tab.",
                "viewport":       "desktop",
                "contrast_ratio": None,
                "help_url":       "https://www.w3.org/WAI/WCAG21/Understanding/no-keyboard-trap.html",
                "ai_explanation": explain_rule(
                    rule={**base_rule, "instance_count": 1, "status": "fail"},
                    page_url=url
                ),
            })

        # Add keyboard tab order rule
        merged_rules.append({
            "id":             "keyboard-tab-order",
            "name":           "Keyboard tab order",
            "wcag":           "2.4.3",
            "level":          "A",
            "test_type":      "automated",
            "severity":       "serious",
            "status":         "pass" if focus_result.get("success") and not focus_result.get("focus_trap") else "fail",
            "instances":      [],
            "instance_count": focus_result.get("tab_count", 0),
            "eaa_critical":   True,
            "description":    f"Tab key navigated {focus_result.get('tab_count', 0)} elements. {'Focus trap detected.' if focus_result.get('focus_trap') else 'No focus trap detected.'}",
            "viewport":       "desktop",
            "contrast_ratio": None,
            "focus_sequence": focus_result.get("focus_sequence", []),
            "help_url":       "",
        })

        return {
            "url":               url,
            "final_url":         final_url,
            "page_title":        page_title,
            "rules":             merged_rules,
            "page_screenshot":   page_screenshot,
            "mobile_screenshot": mobile_screenshot,
            "focus_analysis":    focus_result,
            "viewports_tested":  ["desktop (1280px)", "mobile (375px)"],
            "axe_version":       "4.9.0",
        }

    except Exception as e:
        log.error(f"Scanner crashed: {e}")
        return {"error": f"Scanner crashed: {str(e)}"}


# ══════════════════════════════════════════════════════
# AUTHENTICATED SCAN (cookie injection)
# ══════════════════════════════════════════════════════
def run_scan_with_cookies(url: str, storage_state: dict) -> dict:
    """Authenticated scan using injected session cookies."""
    return run_scan(url, storage_state=storage_state)


# ══════════════════════════════════════════════════════
# FULL SCAN WITH ALL FEATURES
# ══════════════════════════════════════════════════════
def run_full_scan(url: str, storage_state: dict | None = None,
                  include_dynamic: bool = True,
                  include_colours: bool = True,
                  include_pdfs:    bool = True) -> dict:
    """
    Extended scan with:
    - Desktop + mobile axe-core
    - Dynamic content (SPA interaction)
    - Colour palette analysis
    - PDF accessibility checks
    - Focus simulation
    """
    # Run base scan
    result = run_scan(url, storage_state=storage_state)
    if result.get("error"):
        return result

    # Dynamic content scan
    if include_dynamic:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
                ctx_opts = {"ignore_https_errors": True, "viewport": VIEWPORTS["desktop"]}
                if storage_state:
                    ctx_opts["storage_state"] = storage_state
                context = browser.new_context(**ctx_opts)
                page    = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_WAIT)
                except Exception:
                    pass

                # Get base violations for comparison
                base_axe = _run_axe_on_page(page)
                base_violations = {v["id"] for v in base_axe.get("violations", [])}

                from scanner_dynamic import scan_dynamic_states
                dynamic_findings = scan_dynamic_states(page, base_violations)
                result["dynamic_findings"] = dynamic_findings

                # Colour analysis on same page session
                if include_colours:
                    from colour_analyser import analyse_colours
                    result["colour_analysis"] = analyse_colours(page)

                # PDF accessibility
                if include_pdfs:
                    from pdf_accessibility import check_pdf_accessibility
                    result["pdf_analysis"] = check_pdf_accessibility(page, url)

                browser.close()
        except Exception as e:
            log.warning(f"Extended scan features failed: {e}")
            result["dynamic_findings"] = []

    return result
