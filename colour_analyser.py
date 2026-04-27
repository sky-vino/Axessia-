# colour_analyser.py
# Site-wide colour palette extraction and contrast analysis
# Extracts all colours used on the page, checks all text/bg combinations

import logging
import re
from playwright.sync_api import Page

log = logging.getLogger(__name__)

WCAG_AA_NORMAL = 4.5
WCAG_AA_LARGE  = 3.0
WCAG_AAA_NORMAL= 7.0


def _hex_to_rgb(hex_color: str) -> tuple | None:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c*2 for c in hex_color)
    if len(hex_color) != 6:
        return None
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _rgb_str_to_tuple(rgb_str: str) -> tuple | None:
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' to (r, g, b)."""
    try:
        nums = [float(x.strip()) for x in re.findall(r"[\d.]+", rgb_str)]
        if len(nums) >= 3:
            return (int(nums[0]), int(nums[1]), int(nums[2]))
    except Exception:
        pass
    return None


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.x."""
    def c(val):
        v = val / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def _contrast_ratio(rgb1: tuple, rgb2: tuple) -> float:
    l1 = _relative_luminance(*rgb1)
    l2 = _relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker  = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}".upper()


def extract_colours(page: Page) -> dict:
    """
    Extract all colour combinations from the page.
    Returns palette + contrast analysis.
    """
    try:
        colour_data = page.evaluate("""
            () => {
                const elements = document.querySelectorAll(
                    'p, h1, h2, h3, h4, h5, h6, a, button, label, span, li, td, th, ' +
                    '[role="button"], [role="link"], input, select, textarea'
                );

                const combos = [];
                const palette = new Set();
                const seen = new Set();

                for (const el of elements) {
                    try {
                        const style = window.getComputedStyle(el);
                        const fg    = style.color;
                        const bg    = style.backgroundColor;
                        const size  = parseFloat(style.fontSize);
                        const bold  = parseInt(style.fontWeight) >= 700;
                        const tag   = el.tagName.toLowerCase();
                        const text  = (el.textContent || '').trim().substring(0, 30);

                        if (!fg || !bg || fg === 'transparent' || bg === 'transparent') continue;
                        if (bg === 'rgba(0, 0, 0, 0)') continue;

                        const key = fg + '|' + bg;
                        if (seen.has(key)) continue;
                        seen.add(key);

                        palette.add(fg);
                        palette.add(bg);

                        combos.push({ fg, bg, size, bold, tag, text });

                        if (combos.length >= 200) break;
                    } catch(e) { continue; }
                }

                return { combos, palette: Array.from(palette) };
            }
        """)
    except Exception as e:
        log.warning(f"Colour extraction failed: {e}")
        return {"combos": [], "palette": [], "failures": [], "passes": [], "summary": {}}

    combos  = colour_data.get("combos", [])
    palette_raw = colour_data.get("palette", [])

    # Parse colours
    failures = []
    passes   = []
    palette_hex = set()

    for combo in combos:
        fg_raw = combo.get("fg","")
        bg_raw = combo.get("bg","")

        fg_rgb = _rgb_str_to_tuple(fg_raw)
        bg_rgb = _rgb_str_to_tuple(bg_raw)

        if not fg_rgb or not bg_rgb:
            continue

        # Skip pure transparent
        if bg_raw.startswith("rgba") and "0)" in bg_raw:
            continue

        ratio    = _contrast_ratio(fg_rgb, bg_rgb)
        is_large = combo.get("size", 16) >= 18 or (combo.get("size", 16) >= 14 and combo.get("bold", False))
        required = WCAG_AA_LARGE if is_large else WCAG_AA_NORMAL
        passes_aa= ratio >= required

        fg_hex = _rgb_to_hex(*fg_rgb)
        bg_hex = _rgb_to_hex(*bg_rgb)
        palette_hex.add(fg_hex)
        palette_hex.add(bg_hex)

        entry = {
            "fg":         fg_hex,
            "bg":         bg_hex,
            "ratio":      ratio,
            "required":   required,
            "passes_aa":  passes_aa,
            "passes_aaa": ratio >= WCAG_AAA_NORMAL,
            "is_large":   is_large,
            "element":    combo.get("tag",""),
            "text":       combo.get("text",""),
        }

        if passes_aa:
            passes.append(entry)
        else:
            failures.append(entry)

    # Sort failures by worst ratio first
    failures.sort(key=lambda x: x["ratio"])

    return {
        "combos":       combos,
        "palette":      sorted(palette_hex),
        "failures":     failures,
        "passes":       passes[:20],  # limit passes shown
        "summary": {
            "total_combinations": len(combos),
            "failing":  len(failures),
            "passing":  len(passes),
            "pass_rate": round(len(passes) / max(len(combos), 1) * 100, 1),
        }
    }


def analyse_colours(page: Page) -> dict:
    """Public entry point for colour analysis."""
    return extract_colours(page)
