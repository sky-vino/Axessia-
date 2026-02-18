from reportlab.platypus import SimpleDocTemplate, Paragraph

def export_pdf(scan):
    doc = SimpleDocTemplate("axessia_report.pdf")
    content = [Paragraph(f"WCAG Score: {scan['summary']['wcag_score']}%")]
    doc.build(content)
