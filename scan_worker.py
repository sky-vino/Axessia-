# scan_worker.py
from scanner import scan_url


def scan(url: str):
    axe_results = scan_url(url)

    if "violations" not in axe_results:
        return {
            "rules": [],
            "violations": [],
            "warning": "No rules returned from scan"
        }

    return axe_results
