# playwright_runner.py

from playwright.sync_api import sync_playwright


class BrowserEngine:
    def __init__(self, timeout: int = 15000):
        self.timeout = timeout

    def render(self, url: str) -> dict:
        """
        Launch headless Chromium,
        fully render JS,
        return rendered DOM + metadata.
        """

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"]
            )

            context = browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()
            page.set_default_timeout(self.timeout)

            try:
                page.goto(url, wait_until="networkidle")
            except Exception as e:
                browser.close()
                return {
                    "success": False,
                    "error": str(e)
                }

            html = page.content()

            result = {
                "success": True,
                "html": html,
                "title": page.title(),
                "final_url": page.url
            }

            browser.close()
            return result
