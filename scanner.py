# scanner.py

from bs4 import BeautifulSoup
from rules_registry import RULES
from playwright_runner import BrowserEngine
from focus_engine import FocusEngine
from scoring import calculate_wcag_scores
from ai_explainer import generate_fix_explanation


def run_scan(url: str, progress_cb=None):

    # ---- DEBUG: Confirm correct rules file is loaded ----
    print("Loaded rule IDs from RULES:")
    for r in RULES:
        print("-", r["id"])
    print("--------------------------------------------------")

    browser = BrowserEngine()
    render_result = browser.render(url)

    if not render_result["success"]:
        return {
            "error": f"Unable to load page: {render_result.get('error')}",
            "rules": []
        }

    html = render_result["html"]
    soup = BeautifulSoup(html, "html.parser")

    results = []
    total = len(RULES)

    for idx, rule in enumerate(RULES, start=1):

        if progress_cb:
            progress_cb(idx, total, rule["name"])

        instances = []

        # ==================================================
        # IMAGE ALT RULE
        # ==================================================
        if rule["id"] == "image-alt":
            for img in soup.find_all("img"):
                alt = img.get("alt")

                if not alt or alt.strip() == "":
                    instances.append({
                        "tag": "img",
                        "snippet": str(img)[:300],
                        "reason": "Missing or empty alt attribute"
                    })

        # ==================================================
        # KEYBOARD FOCUS RULE
        # ==================================================
        if rule["id"] == "keyboard-focus":

            focus_engine = FocusEngine()
            focus_result = focus_engine.analyze_focus(url)

            if focus_result["success"]:

                if focus_result["focus_trap"]:
                    instances.append({
                        "tag": "focus",
                        "snippet": "Focus trap detected during TAB navigation",
                        "reason": "Keyboard focus is trapped in a loop"
                    })

                if len(focus_result["focus_sequence"]) == 0:
                    instances.append({
                        "tag": "focus",
                        "snippet": "No focusable elements detected",
                        "reason": "No elements reachable via keyboard"
                    })

        # ==================================================
        # AI EXPLANATION PER INSTANCE
        # ==================================================
        for inst in instances:
            try:
                inst["ai_fix"] = generate_fix_explanation(
                    rule["name"], inst
                )
            except Exception:
                inst["ai_fix"] = "AI explanation unavailable."

        # ==================================================
        # STATUS CALCULATION
        # ==================================================
        if instances:
            status = "fail"
        elif rule["test_type"] == "automated":
            status = "pass"
        else:
            status = "manual"

        results.append({
            "id": rule["id"],
            "name": rule["name"],
            "wcag": rule["wcag"],
            "level": rule["level"],
            "type": rule["test_type"],
            "severity": rule["severity"],
            "status": status,
            "instances": instances,
            "instance_count": len(instances)
        })

    return {
        "rules": results,
        "wcag_scores": calculate_wcag_scores(results),
        "metadata": {
            "page_title": render_result["title"],
            "final_url": render_result["final_url"]
        }
    }
