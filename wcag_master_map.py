# wcag_master_map.py
# Complete WCAG 2.1 + WCAG 2.2 criteria mapping
# Level A, AA, and selected AAA

WCAG_SC_LEVEL = {
    # ── 1.1 Text Alternatives ──
    "1.1.1": "A",

    # ── 1.2 Time-Based Media ──
    "1.2.1": "A",
    "1.2.2": "A",
    "1.2.3": "A",
    "1.2.4": "AA",
    "1.2.5": "AA",

    # ── 1.3 Adaptable ──
    "1.3.1": "A",
    "1.3.2": "A",
    "1.3.3": "A",
    "1.3.4": "AA",
    "1.3.5": "AA",
    "1.3.6": "AAA",

    # ── 1.4 Distinguishable ──
    "1.4.1": "A",
    "1.4.2": "A",
    "1.4.3": "AA",
    "1.4.4": "AA",
    "1.4.5": "AA",
    "1.4.6": "AAA",
    "1.4.10": "AA",
    "1.4.11": "AA",
    "1.4.12": "AA",
    "1.4.13": "AA",

    # ── 2.1 Keyboard Accessible ──
    "2.1.1": "A",
    "2.1.2": "A",
    "2.1.4": "A",

    # ── 2.2 Enough Time ──
    "2.2.1": "A",
    "2.2.2": "A",

    # ── 2.3 Seizures ──
    "2.3.1": "A",

    # ── 2.4 Navigable ──
    "2.4.1": "A",
    "2.4.2": "A",
    "2.4.3": "A",
    "2.4.4": "A",
    "2.4.5": "AA",
    "2.4.6": "AA",
    "2.4.7": "AA",
    "2.4.8": "AAA",
    "2.4.9": "AAA",
    "2.4.10": "AAA",
    "2.4.11": "AA",   # WCAG 2.2
    "2.4.12": "AAA",  # WCAG 2.2
    "2.4.13": "AAA",  # WCAG 2.2

    # ── 2.5 Input Modalities (WCAG 2.1+) ──
    "2.5.1": "A",
    "2.5.2": "A",
    "2.5.3": "A",
    "2.5.4": "A",
    "2.5.7": "AA",  # WCAG 2.2
    "2.5.8": "AA",  # WCAG 2.2

    # ── 3.1 Readable ──
    "3.1.1": "A",
    "3.1.2": "AA",

    # ── 3.2 Predictable ──
    "3.2.1": "A",
    "3.2.2": "A",
    "3.2.3": "AA",
    "3.2.4": "AA",
    "3.2.6": "A",   # WCAG 2.2

    # ── 3.3 Input Assistance ──
    "3.3.1": "A",
    "3.3.2": "A",
    "3.3.3": "AA",
    "3.3.4": "AA",
    "3.3.7": "A",   # WCAG 2.2
    "3.3.8": "AA",  # WCAG 2.2

    # ── 4.1 Compatible ──
    "4.1.1": "A",
    "4.1.2": "A",
    "4.1.3": "AA",
}

WCAG_SC_NAME = {
    "1.1.1":  "Non-text Content",
    "1.2.2":  "Captions (Prerecorded)",
    "1.3.1":  "Info and Relationships",
    "1.3.2":  "Meaningful Sequence",
    "1.3.3":  "Sensory Characteristics",
    "1.3.4":  "Orientation",
    "1.3.5":  "Identify Input Purpose",
    "1.4.1":  "Use of Colour",
    "1.4.2":  "Audio Control",
    "1.4.3":  "Contrast (Minimum)",
    "1.4.4":  "Resize Text",
    "1.4.10": "Reflow",
    "1.4.11": "Non-text Contrast",
    "1.4.12": "Text Spacing",
    "1.4.13": "Content on Hover or Focus",
    "2.1.1":  "Keyboard",
    "2.1.2":  "No Keyboard Trap",
    "2.2.1":  "Timing Adjustable",
    "2.4.1":  "Bypass Blocks",
    "2.4.2":  "Page Titled",
    "2.4.3":  "Focus Order",
    "2.4.4":  "Link Purpose (In Context)",
    "2.4.6":  "Headings and Labels",
    "2.4.7":  "Focus Visible",
    "2.4.11": "Focus Not Obscured (Minimum)",
    "2.5.3":  "Label in Name",
    "2.5.4":  "Motion Actuation",
    "2.5.8":  "Target Size (Minimum)",
    "3.1.1":  "Language of Page",
    "3.1.2":  "Language of Parts",
    "3.2.3":  "Consistent Navigation",
    "3.2.6":  "Consistent Help",
    "3.3.1":  "Error Identification",
    "3.3.2":  "Labels or Instructions",
    "3.3.3":  "Error Suggestion",
    "3.3.7":  "Redundant Entry",
    "3.3.8":  "Accessible Authentication (Minimum)",
    "4.1.1":  "Parsing",
    "4.1.2":  "Name, Role, Value",
    "4.1.3":  "Status Messages",
}
