# report_json.py
# Layer 6 – JSON export (fully auditable)

import json
from datetime import datetime


def generate_json_report(scan_result: dict) -> dict:
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tool": "AccessiScope",
        "version": "Layer-6",
        "summary": {
            "score": scan_result.get("score"),
            "eaa": scan_result.get("eaa"),
        },
        "rules": scan_result.get("rules", []),
    }


def export_json(scan_result: dict) -> str:
    report = generate_json_report(scan_result)
    return json.dumps(report, indent=2)
