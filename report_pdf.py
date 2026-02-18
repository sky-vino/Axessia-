# report_pdf.py
# Layer 6 – PDF export (evidence-first)

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Preformatted,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime


def export_pdf(scan_result: dict, file_path: str):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    content = []

    content.append(Paragraph(
        "<b>AccessiScope – Accessibility Report</b>",
        styles["Title"],
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph(
        f"Generated at: {datetime.utcnow().isoformat()} UTC",
        styles["Normal"],
    ))
    content.append(Spacer(1, 12))

    # -------------------------
    # SCORE & EAA
    # -------------------------
    score = scan_result.get("score", {})
    eaa = scan_result.get("eaa", {})

    content.append(Paragraph(
        f"<b>Automated WCAG Score:</b> {score.get('score', 'N/A')}%",
        styles["Normal"],
    ))

    content.append(Paragraph(
        f"<b>EAA Ready:</b> {eaa.get('eaa_ready')}",
        styles["Normal"],
    ))

    content.append(Spacer(1, 16))

    # -------------------------
    # RULE DETAILS
    # -------------------------
    for rule in scan_result.get("rules", []):
        content.append(Paragraph(
            f"<b>{rule['name']}</b> "
            f"(WCAG {rule['wcag']} – {rule['level']}) "
            f"[{rule['status'].upper()}]",
            styles["Heading3"],
        ))

        content.append(Paragraph(
            f"Type: {rule['test_type']} | Severity: {rule['severity']}",
            styles["Normal"],
        ))

        for inst in rule.get("instances", []):
            content.append(Spacer(1, 6))
            content.append(Preformatted(
                inst.get("tag", ""),
                styles["Code"],
            ))
            content.append(Paragraph(
                inst.get("reason", ""),
                styles["Italic"],
            ))

            if inst.get("ai_explanation"):
                content.append(Paragraph(
                    "<b>AI explanation:</b>",
                    styles["Normal"],
                ))
                content.append(Paragraph(
                    inst["ai_explanation"],
                    styles["Normal"],
                ))

        content.append(Spacer(1, 16))

    doc.build(content)
