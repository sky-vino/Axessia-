# pdf_accessibility.py
# Checks accessibility of PDF files linked from a scanned page
# Checks: tagged PDF, language, title, bookmarks, reading order indicators

import io
import logging
import requests
from urllib.parse import urljoin, urlparse

log = logging.getLogger(__name__)

PDF_CHECKS = {
    "pdf-tagged":       {"name": "PDF must be tagged",               "wcag": "1.3.1", "severity": "critical"},
    "pdf-title":        {"name": "PDF must have a document title",    "wcag": "2.4.2", "severity": "serious"},
    "pdf-language":     {"name": "PDF must declare a language",       "wcag": "3.1.1", "severity": "serious"},
    "pdf-bookmarks":    {"name": "PDF must have bookmarks (>10 pages)","wcag": "2.4.5","severity": "moderate"},
    "pdf-reading-order":{"name": "PDF reading order must be logical", "wcag": "1.3.2", "severity": "serious"},
}


def _find_pdf_links(page) -> list:
    """Find all PDF links on the current page."""
    try:
        links = page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href]');
                const pdfs = [];
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    if (href.toLowerCase().endsWith('.pdf') ||
                        href.toLowerCase().includes('.pdf?') ||
                        a.textContent.toLowerCase().includes('.pdf')) {
                        pdfs.push({
                            href: a.href,
                            text: (a.textContent || a.getAttribute('aria-label') || '').trim().substring(0, 80),
                        });
                    }
                }
                return pdfs.slice(0, 10);
            }
        """)
        return links or []
    except Exception:
        return []


def _check_pdf(pdf_url: str, page_base_url: str) -> dict:
    """
    Download and check a PDF for basic accessibility requirements.
    Uses pypdf if available, otherwise basic header checks.
    """
    result = {
        "url":   pdf_url,
        "rules": [],
        "error": None,
    }

    try:
        response = requests.get(pdf_url, timeout=15, headers={"User-Agent": "Axessia-Scanner/1.0"})
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not pdf_url.lower().endswith(".pdf"):
            result["error"] = "Not a PDF file"
            return result

        pdf_bytes = response.content

        # Try pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

            # Check: Tagged (accessibility)
            is_tagged = False
            try:
                catalog = reader.trailer.get("/Root", {})
                mark_info = catalog.get("/MarkInfo", {})
                if hasattr(mark_info, "get"):
                    is_tagged = bool(mark_info.get("/Marked"))
                # Also check metadata
                meta = reader.metadata
                if meta:
                    is_tagged = is_tagged or bool(meta.get("/Marked"))
            except Exception:
                pass

            result["rules"].append({
                "id":       "pdf-tagged",
                "status":   "pass" if is_tagged else "fail",
                **PDF_CHECKS["pdf-tagged"],
                "detail":   "PDF is tagged for accessibility" if is_tagged else "PDF is not tagged — screen readers cannot read it.",
            })

            # Check: Title
            meta = reader.metadata or {}
            has_title = bool(meta.get("/Title", "").strip())
            result["rules"].append({
                "id":     "pdf-title",
                "status": "pass" if has_title else "fail",
                **PDF_CHECKS["pdf-title"],
                "detail": f"Title: '{meta.get('/Title','')}'" if has_title else "PDF has no document title.",
            })

            # Check: Language
            has_lang = False
            try:
                catalog = reader.trailer.get("/Root", {})
                lang = catalog.get("/Lang", "")
                has_lang = bool(lang)
            except Exception:
                pass
            result["rules"].append({
                "id":     "pdf-language",
                "status": "pass" if has_lang else "fail",
                **PDF_CHECKS["pdf-language"],
                "detail": "PDF has a declared language." if has_lang else "PDF has no language declaration.",
            })

            # Check: Bookmarks for long documents
            num_pages = len(reader.pages)
            if num_pages >= 10:
                has_bookmarks = False
                try:
                    outlines = reader.outline
                    has_bookmarks = len(outlines) > 0
                except Exception:
                    pass
                result["rules"].append({
                    "id":     "pdf-bookmarks",
                    "status": "pass" if has_bookmarks else "fail",
                    **PDF_CHECKS["pdf-bookmarks"],
                    "detail": f"PDF has {num_pages} pages. {'Bookmarks found.' if has_bookmarks else 'No bookmarks — navigation is difficult.'}",
                })

            # Reading order — can only flag if not tagged
            result["rules"].append({
                "id":     "pdf-reading-order",
                "status": "pass" if is_tagged else "fail",
                **PDF_CHECKS["pdf-reading-order"],
                "detail": "Tagged PDF supports logical reading order." if is_tagged else "Untagged PDF — reading order cannot be verified by assistive technology.",
            })

            result["pages"]     = num_pages
            result["file_size"] = f"{len(pdf_bytes)//1024} KB"

        except ImportError:
            # pypdf not available — basic check only
            is_pdf_tagged = b"/MarkInfo" in pdf_bytes and b"/Marked true" in pdf_bytes
            result["rules"].append({
                "id":     "pdf-tagged",
                "status": "pass" if is_pdf_tagged else "fail",
                **PDF_CHECKS["pdf-tagged"],
                "detail": "Basic check only — install pypdf for full analysis.",
            })
            result["note"] = "Install pypdf for full PDF accessibility analysis: pip install pypdf"

    except requests.exceptions.Timeout:
        result["error"] = "PDF download timed out."
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP error: {e}"
    except Exception as e:
        result["error"] = f"PDF check failed: {str(e)}"

    return result


def check_pdf_accessibility(page, base_url: str) -> dict:
    """
    Find all linked PDFs on the page and check their accessibility.
    """
    pdf_links = _find_pdf_links(page)

    if not pdf_links:
        return {
            "pdf_count": 0,
            "pdfs":      [],
            "summary":   {"total": 0, "with_issues": 0, "checked": 0},
        }

    results = []
    for link in pdf_links[:8]:  # max 8 PDFs per page
        href = link.get("href", "")
        if not href.startswith("http"):
            href = urljoin(base_url, href)

        pdf_result = _check_pdf(href, base_url)
        pdf_result["link_text"] = link.get("text", "")
        results.append(pdf_result)

    with_issues = sum(
        1 for r in results
        if any(rule.get("status") == "fail" for rule in r.get("rules", []))
    )

    return {
        "pdf_count": len(pdf_links),
        "pdfs":      results,
        "summary":   {
            "total":       len(results),
            "with_issues": with_issues,
            "checked":     len(results),
        },
    }
