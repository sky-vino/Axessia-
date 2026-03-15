# focus_engine.py

from playwright.sync_api import sync_playwright


class FocusEngine:
    def __init__(self, timeout: int = 15000, max_tabs: int = 100):
        self.timeout = timeout
        self.max_tabs = max_tabs

    def analyze_focus(self, url: str) -> dict:
        """
        Simulates TAB navigation and tracks focus movement.
        Detects focus trap and missing focus scenarios.
        """

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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

            focused_elements = []
            visited = set()

            page.keyboard.press("Tab")

            for _ in range(self.max_tabs):

                element = page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el) return null;

                        return {
                            tag: el.tagName,
                            id: el.id,
                            className: el.className,
                            outerHTML: el.outerHTML.substring(0, 300)
                        };
                    }
                """)

                if not element:
                    break

                signature = element["outerHTML"]

                if signature in visited:
                    # Focus trap detected
                    browser.close()
                    return {
                        "success": True,
                        "focus_trap": True,
                        "focus_sequence": focused_elements
                    }

                visited.add(signature)
                focused_elements.append(element)

                page.keyboard.press("Tab")

            browser.close()

            return {
                "success": True,
                "focus_trap": False,
                "focus_sequence": focused_elements
            }
