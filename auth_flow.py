# ======================================================
# AXESSIA – Sky Authenticated Login Flow
#
# Sky login page (test-www.sky.it) uses a React SPA with
# plain <input> elements — no type/name/id on the fields.
# Strategy: wait for networkidle, then use positional
# selectors (first visible input = email, second = password)
# and spoof a real browser to avoid headless detection.
# ======================================================

import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ── Spoof a real Chrome browser to avoid bot detection ─
BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",  # hides webdriver flag
    "--disable-infobars",
    "--window-size=1280,800",
]

# Realistic Chrome user agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT = 30_000   # ms
WAIT_TIMEOUT = 15_000   # ms for element waits

# ── Regex to extract OTP from page text ───────────────
SKY_CODE_PATTERN = re.compile(
    r'(?:your sky code is|sky code|security code|otp|codice)[:\s]+([0-9]{4,8})',
    re.IGNORECASE,
)

OTP_CONFIRM_SELECTORS = [
    'button:has-text("Confirmation")',
    'button:has-text("Confirm")',
    'button:has-text("Conferma")',
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Verify")',
    'button:has-text("Verifica")',
    'button:has-text("Continue")',
    'button:has-text("Continua")',
]


# ── Helpers ────────────────────────────────────────────

def _find_visible(page, selectors: list[str]):
    """Return first visible element matching any selector."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el, sel
        except Exception:
            continue
    return None, None


def _get_all_visible_inputs(page):
    """Return all visible input elements (excludes hidden/checkbox/radio)."""
    try:
        all_inputs = page.query_selector_all("input")
        visible = []
        for inp in all_inputs:
            try:
                if not inp.is_visible():
                    continue
                t = (inp.get_attribute("type") or "text").lower()
                if t in ("hidden", "checkbox", "radio", "submit", "button", "image"):
                    continue
                visible.append(inp)
            except Exception:
                continue
        return visible
    except Exception:
        return []


def _fill_otp_boxes(page, otp_code: str) -> bool:
    """Fill OTP — handles 6 separate single-digit boxes OR a single field."""
    # Strategy 1: 6 separate maxlength=1 boxes
    boxes = [
        b for b in page.query_selector_all('input[maxlength="1"]')
        if b.is_visible()
    ]
    if len(boxes) >= len(otp_code):
        for i, digit in enumerate(otp_code):
            try:
                boxes[i].click()
                boxes[i].fill(digit)
            except Exception:
                pass
        return True

    # Strategy 2: click first box, keyboard.type distributes digits
    if boxes:
        try:
            boxes[0].click()
            page.keyboard.type(otp_code)
            return True
        except Exception:
            pass

    # Strategy 3: single OTP field
    single_sels = [
        'input[autocomplete="one-time-code"]',
        'input[inputmode="numeric"]',
        'input[name="otp"]',
        'input[name="code"]',
        'input[type="text"][maxlength="6"]',
        'input[type="number"][maxlength="6"]',
    ]
    for sel in single_sels:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(otp_code)
                return True
        except Exception:
            continue

    # Strategy 4: use any visible input on the OTP page
    visible = _get_all_visible_inputs(page)
    if visible:
        try:
            visible[0].click()
            visible[0].fill(otp_code)
            return True
        except Exception:
            pass

    return False


def _extract_otp_from_page(page) -> str | None:
    """Read 'Your sky code is: XXXXXX' from page text."""
    try:
        body_text = page.inner_text("body")
        match = SKY_CODE_PATTERN.search(body_text)
        if match:
            return match.group(1).strip()

        # Also scan individual elements
        for sel in ["p", "span", "div", "label", "h1", "h2", "h3"]:
            try:
                for el in page.query_selector_all(sel):
                    try:
                        text = el.inner_text()
                        m = SKY_CODE_PATTERN.search(text)
                        if m:
                            return m.group(1).strip()
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return None


# ======================================================
# MAIN: fully_automated_login
# ======================================================

def fully_automated_login(
    login_url: str,
    email: str,
    password: str,
) -> dict:
    """
    Full Sky login:
      1. Navigate to login URL
      2. Wait for SPA to render
      3. Fill first visible input = email
         Fill second visible input (or password type) = password
      4. Click Log in button
      5. Wait for OTP page
      6. Read OTP code from page text
      7. Fill 6 digit boxes
      8. Click Confirmation
      9. Return authenticated cookies
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS,
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
                # Remove webdriver JS property that sites detect
                java_script_enabled=True,
            )

            # Hide Playwright / webdriver fingerprint
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()

            # ── Navigate to login page ─────────────────
            try:
                page.goto(login_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                browser.close()
                return {"success": False, "error": "Login page timed out.", "stage": "phase1"}
            except Exception as e:
                browser.close()
                return {"success": False, "error": f"Could not open login page: {e}", "stage": "phase1"}

            # ── Wait for SPA to render fully ──────────
            # First wait for any input to appear
            try:
                page.wait_for_selector("input", timeout=WAIT_TIMEOUT, state="visible")
            except Exception:
                pass

            # Then wait for network to settle (JS bundles loaded)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass

            # Small extra delay for React to mount components
            page.wait_for_timeout(1500)

            # ── Get all visible inputs ─────────────────
            visible_inputs = _get_all_visible_inputs(page)

            if len(visible_inputs) < 1:
                # Debug: grab page title and URL for error message
                title = page.title()
                url_now = page.url
                browser.close()
                return {
                    "success": False,
                    "error": (
                        f"No visible input fields found on the login page. "
                        f"Page title: '{title}', URL: '{url_now}'. "
                        "Sky may be blocking the automated browser. "
                        "Please try again in a moment."
                    ),
                    "stage": "phase1",
                }

            # ── Fill email (first input) ───────────────
            try:
                visible_inputs[0].click()
                visible_inputs[0].fill(email)
            except Exception as e:
                browser.close()
                return {"success": False, "error": f"Could not fill email field: {e}", "stage": "phase1"}

            # ── Fill password ──────────────────────────
            # Prefer input[type="password"], fall back to second visible input
            pw_el = None
            try:
                pw_el = page.query_selector('input[type="password"]')
                if pw_el and not pw_el.is_visible():
                    pw_el = None
            except Exception:
                pw_el = None

            if pw_el is None and len(visible_inputs) >= 2:
                pw_el = visible_inputs[1]

            if pw_el is None:
                browser.close()
                return {"success": False, "error": "Could not find the password field.", "stage": "phase1"}

            try:
                pw_el.click()
                pw_el.fill(password)
            except Exception as e:
                browser.close()
                return {"success": False, "error": f"Could not fill password field: {e}", "stage": "phase1"}

            # ── Click Log in button ────────────────────
            login_btn_selectors = [
                'button:has-text("Log in")',
                'button:has-text("Log In")',
                'button:has-text("Accedi")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Continue")',
                'button:has-text("Continua")',
                'button[type="submit"]',
                'input[type="submit"]',
                '[data-testid*="login"]',
                '[data-testid*="submit"]',
            ]

            login_btn, login_sel = _find_visible(page, login_btn_selectors)
            if not login_btn:
                browser.close()
                return {"success": False, "error": "Could not find the Log in button.", "stage": "phase1"}

            login_btn.click()

            # ── Wait for OTP page to load ──────────────
            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                pass

            # Wait for OTP input boxes to appear
            try:
                page.wait_for_selector(
                    'input[maxlength="1"], input[autocomplete="one-time-code"], input[inputmode="numeric"]',
                    timeout=WAIT_TIMEOUT,
                    state="visible",
                )
            except Exception:
                pass

            try:
                page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass

            page.wait_for_timeout(1000)

            # Check for wrong credentials (still on login page)
            current_url = page.url
            if "login" in current_url.lower() and "security" not in current_url.lower():
                try:
                    body = page.inner_text("body")
                    error_keywords = [
                        "incorrect", "invalid", "wrong", "error",
                        "errato", "non valido", "sbagliato", "not found",
                    ]
                    if any(kw in body.lower() for kw in error_keywords):
                        browser.close()
                        return {
                            "success": False,
                            "error": "Incorrect email or password. Please check your credentials.",
                            "stage": "phase1",
                        }
                except Exception:
                    pass

            # ── Read OTP from page ─────────────────────
            otp_code = _extract_otp_from_page(page)

            if not otp_code:
                # Save state so user can enter OTP manually
                storage_state = context.storage_state()
                otp_url = page.url
                browser.close()
                return {
                    "success": False,
                    "needs_manual_otp": True,
                    "storage_state": storage_state,
                    "otp_url": otp_url,
                    "error": (
                        "Logged in successfully but could not read the OTP code from the page. "
                        "Please check your SMS and enter the code manually below."
                    ),
                    "stage": "otp_read",
                }

            # ── Fill OTP boxes ─────────────────────────
            filled = _fill_otp_boxes(page, otp_code)
            if not filled:
                storage_state = context.storage_state()
                otp_url = page.url
                browser.close()
                return {
                    "success": False,
                    "needs_manual_otp": True,
                    "storage_state": storage_state,
                    "otp_url": otp_url,
                    "otp_code_found": otp_code,
                    "error": (
                        f"Found the code ({otp_code}) but could not fill the boxes. "
                        "Please enter it manually below."
                    ),
                    "stage": "otp_fill",
                }

            # ── Click Confirmation ─────────────────────
            confirm_btn, _ = _find_visible(page, OTP_CONFIRM_SELECTORS)
            if confirm_btn:
                confirm_btn.click()
            else:
                page.keyboard.press("Enter")

            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                pass

            page.wait_for_timeout(1500)

            # ── Verify login succeeded ─────────────────
            final_url = page.url
            auth_keywords = ["login", "signin", "otp", "verify", "security", "auth", "token"]
            if any(kw in final_url.lower() for kw in auth_keywords):
                browser.close()
                return {
                    "success": False,
                    "error": (
                        f"OTP confirmation may have failed — still on: {final_url}. "
                        "The code may have expired. Please try logging in again."
                    ),
                    "stage": "phase2",
                }

            final_storage_state = context.storage_state()
            browser.close()

            return {
                "success": True,
                "storage_state": final_storage_state,
                "final_url": final_url,
                "otp_used": otp_code,
            }

    except Exception as e:
        return {"success": False, "error": f"Login crashed: {str(e)}", "stage": "unknown"}


# ======================================================
# FALLBACK: manual OTP when code not readable from page
# ======================================================

def phase2_manual_otp(otp_url: str, otp_code: str, storage_state: dict) -> dict:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                storage_state=storage_state,
                user_agent=USER_AGENT,
                ignore_https_errors=True,
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()

            try:
                page.goto(otp_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            except Exception:
                pass

            try:
                page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass

            page.wait_for_timeout(1000)

            filled = _fill_otp_boxes(page, otp_code.strip())
            if not filled:
                browser.close()
                return {"success": False, "error": "Could not fill the OTP input."}

            confirm_btn, _ = _find_visible(page, OTP_CONFIRM_SELECTORS)
            if confirm_btn:
                confirm_btn.click()
            else:
                page.keyboard.press("Enter")

            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except Exception:
                pass

            page.wait_for_timeout(1000)

            final_url = page.url
            auth_keywords = ["login", "signin", "otp", "verify", "security", "auth"]
            if any(kw in final_url.lower() for kw in auth_keywords):
                browser.close()
                return {
                    "success": False,
                    "error": f"Still on auth page after OTP: {final_url}. Code may be wrong or expired.",
                }

            final_storage_state = context.storage_state()
            browser.close()
            return {"success": True, "storage_state": final_storage_state, "final_url": final_url}

    except Exception as e:
        return {"success": False, "error": f"Manual OTP crashed: {str(e)}"}


# ======================================================
# HELPER: verify session is still alive
# ======================================================

def verify_session(target_url: str, storage_state: dict) -> dict:
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
            landed_url = page.url
            browser.close()
            auth_keywords = ["login", "signin", "security", "otp", "auth"]
            return {
                "valid": not any(kw in landed_url.lower() for kw in auth_keywords),
                "landed_url": landed_url,
            }
    except Exception as e:
        return {"valid": False, "landed_url": "", "error": str(e)}