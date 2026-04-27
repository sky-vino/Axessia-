# scanner_dynamic.py
# Dynamic Content Scanner — clicks interactive elements, opens modals/dropdowns,
# scans each state separately. Covers SPA frameworks (Angular, React, Vue).

import time
import logging
from playwright.sync_api import Page

log = logging.getLogger(__name__)

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js"

# Elements that typically open overlaid content without navigating
INTERACTIVE_SELECTORS = [
    # Buttons (non-submit, non-link)
    "button:not([type='submit']):not([disabled])",
    "[role='button']:not([disabled])",
    # Disclosure widgets
    "details > summary",
    "[aria-expanded='false']",
    # Tabs
    "[role='tab']:not([aria-selected='true'])",
    # Accordions
    ".accordion-header, .accordion-button",
    # Select / dropdown triggers
    "[aria-haspopup='listbox'], [aria-haspopup='dialog'], [aria-haspopup='menu']",
    # Custom dropdowns
    ".dropdown-toggle, .select-trigger",
]

NAV_KEYWORDS = ["logout", "signout", "delete", "remove", "submit", "buy", "pay", "checkout"]
MAX_ELEMENTS = 30       # max interactive elements to click
STATE_WAIT   = 1500     # ms to wait after click for DOM to settle


def _axe_on_current_state(page: Page) -> dict:
    """Run axe-core on the current DOM state."""
    try:
        page.add_script_tag(url=AXE_CDN)
        page.wait_for_function("typeof axe !== 'undefined'", timeout=8000)
        return page.evaluate("async () => await axe.run(document)") or {}
    except Exception as e:
        log.debug(f"axe failed on dynamic state: {e}")
        return {}


def _is_safe_to_click(element_info: dict) -> bool:
    """Determine if clicking this element is safe (won't navigate or destructive)."""
    text  = (element_info.get("text") or "").lower()
    href  = (element_info.get("href") or "")
    type_ = (element_info.get("type") or "").lower()

    if type_ in ("submit",):
        return False
    if href and href != "#" and not href.startswith("javascript"):
        return False
    if any(kw in text for kw in NAV_KEYWORDS):
        return False
    return True


def _get_interactive_elements(page: Page) -> list:
    """Find all safe-to-click interactive elements on the page."""
    elements = page.evaluate("""
        () => {
            const selectors = [
                'button:not([disabled]):not([type="submit"])',
                '[role="button"]:not([disabled])',
                'details > summary',
                '[aria-expanded="false"]',
                '[role="tab"]:not([aria-selected="true"])',
                '[aria-haspopup]',
                '.accordion-button, .accordion-header',
            ];

            const results = [];
            const seen = new Set();

            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    const html = el.outerHTML.substring(0, 150);
                    if (seen.has(html)) continue;
                    seen.add(html);

                    results.push({
                        selector: el.id ? '#' + el.id : sel,
                        text: (el.textContent || el.getAttribute('aria-label') || '').trim().substring(0, 80),
                        href: el.getAttribute('href') || '',
                        type: el.getAttribute('type') || '',
                        expanded: el.getAttribute('aria-expanded'),
                        role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        outerHTML: html,
                    });

                    if (results.length >= 40) return results;
                }
            }
            return results;
        }
    """)
    return elements or []


def _extract_violations(axe_result: dict) -> set:
    """Extract a set of violation IDs from axe result."""
    return {v["id"] for v in axe_result.get("violations", [])}


def scan_dynamic_states(page: Page, base_violations: set) -> list:
    """
    Click each interactive element, wait for DOM changes,
    run axe, detect NEW violations that only appear in this state.
    Returns list of dynamic state findings.
    """
    dynamic_findings = []
    elements = _get_interactive_elements(page)
    log.info(f"Dynamic scanner found {len(elements)} interactive elements")

    for el in elements[:MAX_ELEMENTS]:
        if not _is_safe_to_click(el):
            continue

        try:
            # Try to locate and click the element
            selector = el.get("selector", "")
            text     = el.get("text", "")

            # Use text-based locator for robustness
            if text and len(text) > 2:
                locator = page.get_by_role(
                    el.get("role", "button"),
                    name=text, exact=False
                )
                if not locator.count():
                    locator = page.locator(f"text={text[:30]}").first
            else:
                locator = page.locator(el.get("outerHTML", "button")).first

            if not locator.count():
                continue

            # Store state before click
            dom_before = page.content()

            # Click and wait
            locator.click(timeout=3000)
            page.wait_for_timeout(STATE_WAIT)

            # Check if DOM changed meaningfully
            dom_after = page.content()
            if dom_before == dom_after:
                # Nothing changed — dismiss if modal open, move on
                page.keyboard.press("Escape")
                continue

            # Run axe on new state
            state_axe = _axe_on_current_state(page)
            state_violations = _extract_violations(state_axe)

            # Find violations that only appear in this dynamic state
            new_violations = state_violations - base_violations
            if new_violations:
                # Capture screenshot of the dynamic state
                try:
                    screenshot = page.screenshot(timeout=3000)
                    import base64
                    screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")
                except Exception:
                    screenshot_b64 = None

                # Get details of new violations
                for v in state_axe.get("violations", []):
                    if v["id"] in new_violations:
                        dynamic_findings.append({
                            "trigger_element": text or selector,
                            "trigger_html":    el.get("outerHTML", ""),
                            "violation_id":    v["id"],
                            "violation_name":  v["help"],
                            "wcag":            next((t for t in v.get("tags",[]) if "." in t), "—"),
                            "impact":          v.get("impact","moderate"),
                            "nodes":           v.get("nodes",[])[:3],
                            "screenshot_b64":  screenshot_b64,
                        })

            # Dismiss the opened state
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

            # Click again to close if it was a toggle (aria-expanded)
            if el.get("expanded") == "false":
                try:
                    locator.click(timeout=2000)
                    page.wait_for_timeout(400)
                except Exception:
                    pass

        except Exception as e:
            log.debug(f"Dynamic click failed for {el.get('text','?')}: {e}")
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            continue

    return dynamic_findings
