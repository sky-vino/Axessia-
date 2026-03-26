# ======================================================
# AXESSIA – Sky Authenticated Login Flow
#
# Sky test environment login:
#   Page 1: test-www.sky.it/login
#           Fields: "Username or email" + "Password"
#           Button: "Log in"
#
#   Page 2: test-www.sky.it/security/
#           Shows: "Your sky code is: XXXXXX"  ← read from page
#           Input: 6 separate single-digit boxes
#           Button: "Confirmation"
#
# The OTP is displayed on the page in the test environment,
# so Playwright reads it automatically — user only needs to
# provide their email and password. Everything else is automatic.
# ======================================================

import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
]

PAGE_TIMEOUT = 30_000   # ms


# ── Helpers ────────────────────────────────────────────

def _find_selector(page, candidates: list[str]) -> str | None:
    for sel in candidates:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return sel
        except Exception:
            continue
    return None


def _safe_goto(page, url: str) -> str | None:
    """Navigate and return error string or None on success."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        return None
    except PlaywrightTimeoutError:
        return "Page timed out loading."
    except Exception as e:
        return f"Could not open page: {e}"


# ── Selectors tuned to Sky's actual HTML ───────────────

# Page 1 — login form
EMAIL_SELECTORS = [
    'input[name="username"]',
    'input[name="email"]',
    'input[type="email"]',
    'input[id="username"]',
    'input[id="email"]',
    'input[placeholder*="Username" i]',
    'input[placeholder*="email" i]',
    'input[autocomplete="username"]',
    'input[autocomplete="email"]',
]

PASSWORD_SELECTORS = [
    'input[type="password"]',
    'input[name="password"]',
    'input[id="password"]',
    'input[autocomplete="current-password"]',
]

LOGIN_SUBMIT_SELECTORS = [
    'button:has-text("Log in")',
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Accedi")',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    '[data-testid*="login"]',
    '[data-testid*="submit"]',
]

# Page 2 — OTP entry
# Sky shows 6 separate single-digit input boxes
OTP_BOX_SELECTORS = [
    'input[maxlength="1"]',               # most common for digit boxes
    'input[type="text"][maxlength="1"]',
    'input[type="number"][maxlength="1"]',
    'input[inputmode="numeric"][maxlength="1"]',
    '[data-testid*="otp"]',
    '[data-testid*="code"]',
    '.otp-input',
    '.code-input',
]

# Single-field OTP fallback (in case Sky ever switches to one box)
OTP_SINGLE_SELECTORS = [
    'input[autocomplete="one-time-code"]',
    'input[inputmode="numeric"]',
    'input[name="otp"]',
    'input[name="code"]',
    'input[name="verificationCode"]',
    'input[type="text"][maxlength="6"]',
    'input[type="number"][maxlength="6"]',
]

OTP_CONFIRM_SELECTORS = [
    'button:has-text("Confirmation")',     # Sky's actual button text
    'button:has-text("Confirm")',
    'button:has-text("Conferma")',
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Verify")',
    'button:has-text("Verifica")',
    'button:has-text("Continue")',
    '[data-testid*="confirm"]',
    '[data-testid*="verify"]',
    '[data-testid*="submit"]',
]

# Regex to extract the code from "Your sky code is: 462628"
SKY_CODE_PATTERN = re.compile(
    r'(?:your sky code is|sky code|security code|otp|codice)[:\s]+([0-9]{4,8})',
    re.IGNORECASE,
)


# ======================================================
# EXTRACT OTP FROM PAGE
# Reads "Your sky code is: XXXXXX" directly from the DOM
# ======================================================

def _extract_otp_from_page(page) -> str | None:
    """
    Tries to find the OTP code that Sky displays on the
    security page in the test environment.
    Returns the code string (e.g. "462628") or None.
    """
    try:
        # Strategy 1: search all visible text for the pattern
        body_text = page.inner_text("body")
        match = SKY_CODE_PATTERN.search(body_text)
        if match:
            return match.group(1).strip()

        # Strategy 2: check specific elements that might contain the code
        code_candidates = [
            '[class*="code"]',
            '[class*="otp"]',
            '[class*="security"]',
            'p', 'span', 'div',
        ]
        for sel in code_candidates:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    text = el.inner_text()
                    m = SKY_CODE_PATTERN.search(text)
                    if m:
                        return m.group(1).strip()
            except Exception:
                continue

    except Exception:
        pass

    return None


# ======================================================
# FILL OTP — handles both 6 separate boxes AND single field
# ======================================================

def _fill_otp(page, otp_code: str) -> bool:
    """
    Fills the OTP code into the page.
    Handles:
      - 6 separate single-digit input boxes (Sky's actual UI)
      - Single OTP input field (fallback)
    Returns True if filled successfully.
    """
    # Strategy 1: find all maxlength="1" boxes and fill each
    boxes = page.query_selector_all('input[maxlength="1"]')
    visible_boxes = [b for b in boxes if b.is_visible()]

    if len(visible_boxes) >= len(otp_code):
        for i, digit in enumerate(otp_code):
            try:
                visible_boxes[i].click()
                visible_boxes[i].fill(digit)
            except Exception:
                pass
        return True

    # Strategy 2: focus first box, type full code (browser auto-distributes)
    if visible_boxes:
        try:
            visible_boxes[0].click()
            page.keyboard.type(otp_code)
            return True
        except Exception:
            pass

    # Strategy 3: single OTP field
    single_sel = _find_selector(page, OTP_SINGLE_SELECTORS)
    if single_sel:
        try:
            page.fill(single_sel, otp_code)
            return True
        except Exception:
            pass

    return False


# ======================================================
# MAIN: fully_automated_login
# Runs both phases without user intervention for OTP.
# Credentials → login page → OTP page → read code → confirm → cookies
# ======================================================

def fully_automated_login(
    login_url: str,
    email: str,
    password: str,
) -> dict:
    """
    Complete Sky login in one shot.

    Returns:
        {
            "success": True,
            "storage_state": {...},   # authenticated session cookies
            "final_url": "...",
            "otp_used": "462628",     # for debug/transparency
        }
        or
        {
            "success": False,
            "error": "...",
            "stage": "phase1" | "otp_read" | "phase2",
        }
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
            )
            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()

            # ══════════════════════════════════════════
            # PHASE 1 — Fill email + password → Log in
            # ══════════════════════════════════════════
            err = _safe_goto(page, login_url)
            if err:
                browser.close()
                return {"success": False, "error": err, "stage": "phase1"}

            # Find email field
            email_sel = _find_selector(page, EMAIL_SELECTORS)
            if not email_sel:
                browser.close()
                return {
                    "success": False,
                    "error": (
                        "Could not find the email / username field on the login page. "
                        "The page structure may have changed."
                    ),
                    "stage": "phase1",
                }

            page.fill(email_sel, email)

            # Find password field
            pw_sel = _find_selector(page, PASSWORD_SELECTORS)
            if not pw_sel:
                browser.close()
                return {
                    "success": False,
                    "error": "Could not find the password field.",
                    "stage": "phase1",
                }

            page.fill(pw_sel, password)

            # Click Log in
            submit_sel = _find_selector(page, LOGIN_SUBMIT_SELECTORS)
            if not submit_sel:
                browser.close()
                return {
                    "success": False,
                    "error": "Could not find the Log in button.",
                    "stage": "phase1",
                }

            page.click(submit_sel)

            # Wait for OTP page to load
            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                pass  # continue regardless

            # Check for wrong credentials (still on login page with error)
            current_url = page.url
            if "login" in current_url.lower() and "security" not in current_url.lower():
                # Look for error message on page
                try:
                    body = page.inner_text("body")
                    if any(kw in body.lower() for kw in [
                        "incorrect", "invalid", "wrong", "error",
                        "errato", "non valido", "sbagliato",
                    ]):
                        browser.close()
                        return {
                            "success": False,
                            "error": "Incorrect email or password. Please check your credentials.",
                            "stage": "phase1",
                        }
                except Exception:
                    pass

            # ══════════════════════════════════════════
            # PHASE 2 — Read OTP from page, fill boxes,
            #           click Confirmation
            # ══════════════════════════════════════════

            # Give the OTP page a moment to fully render
            try:
                page.wait_for_selector(
                    'input[maxlength="1"], input[autocomplete="one-time-code"]',
                    timeout=10_000,
                )
            except Exception:
                pass  # page might already be ready

            # Read the OTP code that Sky displays on the page
            otp_code = _extract_otp_from_page(page)

            if not otp_code:
                # OTP not visible on page — ask user to enter it manually
                # Save state so phase2_manual_otp() can continue
                storage_state = context.storage_state()
                otp_url       = page.url
                browser.close()
                return {
                    "success":       False,
                    "needs_manual_otp": True,
                    "storage_state": storage_state,
                    "otp_url":       otp_url,
                    "error": (
                        "Could not read the OTP code automatically from the page. "
                        "Please enter it manually below."
                    ),
                    "stage": "otp_read",
                }

            # Fill the 6 digit boxes with the code
            filled = _fill_otp(page, otp_code)
            if not filled:
                storage_state = context.storage_state()
                otp_url       = page.url
                browser.close()
                return {
                    "success":          False,
                    "needs_manual_otp": True,
                    "storage_state":    storage_state,
                    "otp_url":          otp_url,
                    "otp_code_found":   otp_code,
                    "error": (
                        f"Found the code ({otp_code}) but could not fill the input boxes. "
                        "Please enter it manually below."
                    ),
                    "stage": "otp_fill",
                }

            # Click Confirmation button
            confirm_sel = _find_selector(page, OTP_CONFIRM_SELECTORS)
            if confirm_sel:
                page.click(confirm_sel)
            else:
                # Last resort: press Enter on the last filled box
                page.keyboard.press("Enter")

            # Wait for post-OTP navigation
            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                pass

            # Verify we are no longer on an auth/security page
            final_url     = page.url
            auth_keywords = ["login", "signin", "otp", "verify", "security", "auth", "token"]
            still_on_auth = any(kw in final_url.lower() for kw in auth_keywords)

            if still_on_auth:
                browser.close()
                return {
                    "success": False,
                    "error": (
                        f"OTP confirmation may have failed — still on auth page: {final_url}. "
                        "The code may have expired. Please try logging in again."
                    ),
                    "stage": "phase2",
                }

            # ── Capture fully authenticated session ───
            final_storage_state = context.storage_state()
            browser.close()

            return {
                "success":       True,
                "storage_state": final_storage_state,
                "final_url":     final_url,
                "otp_used":      otp_code,
            }

    except Exception as e:
        return {"success": False, "error": f"Login crashed: {str(e)}", "stage": "unknown"}


# ======================================================
# FALLBACK: manual OTP submission
# Used when OTP code is not visible on the page
# ======================================================

def phase2_manual_otp(
    otp_url: str,
    otp_code: str,
    storage_state: dict,
) -> dict:
    """
    Restores session from phase 1, fills OTP manually, completes login.
    Only called when fully_automated_login() returns needs_manual_otp=True.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                storage_state=storage_state,
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
            )
            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()

            err = _safe_goto(page, otp_url)
            if err:
                browser.close()
                return {"success": False, "error": err}

            filled = _fill_otp(page, otp_code.strip())
            if not filled:
                browser.close()
                return {"success": False, "error": "Could not fill the OTP input boxes."}

            confirm_sel = _find_selector(page, OTP_CONFIRM_SELECTORS)
            if confirm_sel:
                page.click(confirm_sel)
            else:
                page.keyboard.press("Enter")

            try:
                page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
            except PlaywrightTimeoutError:
                pass

            final_url     = page.url
            auth_keywords = ["login", "signin", "otp", "verify", "security", "auth", "token"]
            if any(kw in final_url.lower() for kw in auth_keywords):
                browser.close()
                return {
                    "success": False,
                    "error": (
                        f"Still on auth page after OTP: {final_url}. "
                        "The code may be wrong or expired."
                    ),
                }

            final_storage_state = context.storage_state()
            browser.close()
            return {
                "success":       True,
                "storage_state": final_storage_state,
                "final_url":     final_url,
            }

    except Exception as e:
        return {"success": False, "error": f"Manual OTP crashed: {str(e)}"}


# ======================================================
# HELPER — verify session is still alive
# ======================================================

def verify_session(target_url: str, storage_state: dict) -> dict:
    try:
        with sync_playwright() as p:
            browser  = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context  = browser.new_context(
                storage_state=storage_state,
                ignore_https_errors=True,
            )
            context.set_default_timeout(PAGE_TIMEOUT)
            page = context.new_page()
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            except Exception:
                pass
            landed_url    = page.url
            browser.close()
            auth_keywords = ["login", "signin", "security", "otp", "auth"]
            is_auth       = any(kw in landed_url.lower() for kw in auth_keywords)
            return {"valid": not is_auth, "landed_url": landed_url}
    except Exception as e:
        return {"valid": False, "landed_url": "", "error": str(e)}
