# login_manager.py
# Automated login flow using Playwright
# Handles: username/password, OTP pages, session storage

import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

log = logging.getLogger(__name__)

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


class LoginResult:
    def __init__(self, success: bool, storage_state=None, error=None,
                 needs_otp=False, otp_screenshot=None):
        self.success       = success
        self.storage_state = storage_state
        self.error         = error
        self.needs_otp     = needs_otp
        self.otp_screenshot= otp_screenshot


def detect_otp_page(page) -> bool:
    """Check if current page is asking for OTP/2FA."""
    otp_indicators = [
        "input[name*='otp']", "input[name*='code']",
        "input[name*='pin']",  "input[name*='token']",
        "input[autocomplete='one-time-code']",
        "[aria-label*='code']", "[aria-label*='OTP']",
        "text=verification code", "text=one-time",
        "text=authentication code", "text=sky code",
    ]
    for sel in otp_indicators:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            pass
    return False


def detect_login_page(page) -> bool:
    """Check if current page is a login page."""
    auth_kw = ["login", "signin", "sign-in", "authenticate", "logon"]
    url     = page.url.lower()
    if any(kw in url for kw in auth_kw):
        return True
    # Check for password input
    try:
        if page.locator("input[type='password']").count() > 0:
            return True
    except Exception:
        pass
    return False


def _fill_login_form(page, username: str, password: str) -> bool:
    """Find and fill login form fields."""
    # Try common username field selectors
    user_selectors = [
        "input[type='email']",
        "input[name*='user']", "input[name*='email']",
        "input[id*='user']",   "input[id*='email']",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "input[placeholder*='email' i]",
        "input[placeholder*='user' i]",
    ]
    pass_selectors = [
        "input[type='password']",
    ]

    user_filled = False
    for sel in user_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.fill(username)
                user_filled = True
                break
        except Exception:
            continue

    if not user_filled:
        return False

    pass_filled = False
    for sel in pass_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.fill(password)
                pass_filled = True
                break
        except Exception:
            continue

    return pass_filled


def _submit_login(page) -> None:
    """Submit the login form."""
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Log in')",
        "button:has-text('Sign in')",
        "button:has-text('Login')",
        "button:has-text('Continue')",
        "button:has-text('Next')",
    ]
    for sel in submit_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.click()
                return
        except Exception:
            continue
    # Fallback: press Enter
    page.keyboard.press("Enter")


def submit_otp(page, otp_code: str) -> bool:
    """Submit OTP code on the OTP page."""
    # Sky-style: 6 separate single-digit inputs
    individual_inputs = page.locator("input[maxlength='1']")
    if individual_inputs.count() >= 4:
        digits = [d for d in otp_code if d.isdigit()]
        for i, digit in enumerate(digits):
            try:
                individual_inputs.nth(i).fill(digit)
                time.sleep(0.1)
            except Exception:
                pass
    else:
        # Single OTP input
        otp_selectors = [
            "input[name*='otp']", "input[name*='code']",
            "input[autocomplete='one-time-code']",
        ]
        for sel in otp_selectors:
            try:
                loc = page.locator(sel).first
                if loc.count():
                    loc.fill(otp_code)
                    break
            except Exception:
                continue

    # Submit
    confirm_selectors = [
        "button[type='submit']",
        "button:has-text('Confirm')",
        "button:has-text('Verify')",
        "button:has-text('Continue')",
        "button:has-text('Submit')",
    ]
    for sel in confirm_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.click()
                return True
        except Exception:
            continue
    page.keyboard.press("Enter")
    return True


def automated_login(
    login_url: str,
    username: str,
    password: str,
    target_url: str,
    timeout: int = 30_000,
) -> LoginResult:
    """
    Perform automated login using Playwright.
    Returns LoginResult with storage_state if successful.
    If OTP is required, returns LoginResult with needs_otp=True
    and an OTP screenshot — caller must provide the OTP code
    and call complete_otp_login().
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
            )
            context.set_default_timeout(timeout)
            page = context.new_page()

            # Navigate to login page
            try:
                page.goto(login_url, wait_until="domcontentloaded", timeout=timeout)
            except PlaywrightTimeoutError:
                browser.close()
                return LoginResult(success=False, error="Login page timed out.")

            # Wait for form
            try:
                page.wait_for_selector("input[type='password'], input[type='email']", timeout=10_000)
            except Exception:
                pass

            # Fill credentials
            filled = _fill_login_form(page, username, password)
            if not filled:
                browser.close()
                return LoginResult(success=False, error="Could not find login form fields.")

            page.wait_for_timeout(500)
            _submit_login(page)

            # Wait for navigation
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass

            page.wait_for_timeout(2_000)

            # Check for OTP
            if detect_otp_page(page):
                # Capture OTP page screenshot
                try:
                    import base64
                    shot = page.screenshot()
                    shot_b64 = base64.b64encode(shot).decode("utf-8")
                except Exception:
                    shot_b64 = None

                # Save partial state
                partial_state = context.storage_state()
                browser.close()
                return LoginResult(
                    success=False,
                    needs_otp=True,
                    storage_state=partial_state,
                    otp_screenshot=shot_b64,
                    error="OTP required — enter code to continue.",
                )

            # Check if still on login page (failed login)
            if detect_login_page(page):
                browser.close()
                return LoginResult(
                    success=False,
                    error="Login failed — credentials may be incorrect."
                )

            # Navigate to target URL to confirm session
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout)
                page.wait_for_timeout(2_000)
            except Exception:
                pass

            if detect_login_page(page):
                browser.close()
                return LoginResult(
                    success=False,
                    error="Login appeared to succeed but session does not reach target URL."
                )

            storage_state = context.storage_state()
            browser.close()

            return LoginResult(success=True, storage_state=storage_state)

    except Exception as e:
        return LoginResult(success=False, error=f"Login automation crashed: {str(e)}")


def complete_otp_login(
    partial_storage_state: dict,
    login_url: str,
    username: str,
    password: str,
    otp_code: str,
    target_url: str,
    timeout: int = 30_000,
) -> LoginResult:
    """
    Re-run login + submit OTP code. Called when automated_login returns needs_otp=True.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True,
                storage_state=partial_storage_state,
            )
            context.set_default_timeout(timeout)
            page = context.new_page()

            page.goto(login_url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(1000)

            if not detect_otp_page(page):
                # Need to re-login first
                _fill_login_form(page, username, password)
                page.wait_for_timeout(500)
                _submit_login(page)
                try:
                    page.wait_for_load_state("networkidle", timeout=12_000)
                except Exception:
                    pass
                page.wait_for_timeout(2_000)

            if detect_otp_page(page):
                submit_otp(page, otp_code)
                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception:
                    pass
                page.wait_for_timeout(2_000)

            if detect_login_page(page) or detect_otp_page(page):
                browser.close()
                return LoginResult(success=False, error="OTP verification failed.")

            page.goto(target_url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(1_500)

            if detect_login_page(page):
                browser.close()
                return LoginResult(success=False, error="OTP succeeded but cannot reach target URL.")

            storage_state = context.storage_state()
            browser.close()
            return LoginResult(success=True, storage_state=storage_state)

    except Exception as e:
        return LoginResult(success=False, error=f"OTP completion crashed: {str(e)}")
