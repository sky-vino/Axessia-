# rules_registry.py
# Complete WCAG 2.1 AA + WCAG 2.2 AA rule registry
# Covers all axe-core automated rules + assisted + manual checks

RULES = [

    # ══════════════════════════════════════════════════
    # 1.1 TEXT ALTERNATIVES
    # ══════════════════════════════════════════════════
    {
        "id": "image-alt",
        "name": "Images must have alternative text",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "All <img> elements must have an alt attribute.",
        "eaa_critical": True,
    },
    {
        "id": "input-image-alt",
        "name": "Image buttons must have alternative text",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "<input type='image'> must have an alt attribute.",
        "eaa_critical": True,
    },
    {
        "id": "role-img-alt",
        "name": "ARIA image elements must have accessible names",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Elements with role=img must have an accessible name.",
        "eaa_critical": True,
    },
    {
        "id": "svg-img-alt",
        "name": "SVG images must have accessible text",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Inline SVG used as images must have accessible text.",
        "eaa_critical": True,
    },
    {
        "id": "object-alt",
        "name": "Object elements must have alternate text",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "<object> elements must have accessible alternatives.",
        "eaa_critical": True,
    },
    {
        "id": "image-redundant-alt",
        "name": "Image alt text must not be redundant",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "minor",
        "description": "Avoid repeating adjacent text in image alt attributes.",
        "eaa_critical": False,
    },
    {
        "id": "aria-meter-name",
        "name": "ARIA meter elements must have accessible names",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with role=meter must have accessible names.",
        "eaa_critical": False,
    },
    {
        "id": "aria-progressbar-name",
        "name": "ARIA progressbar elements must have accessible names",
        "wcag": "1.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with role=progressbar must have accessible names.",
        "eaa_critical": False,
    },

    # ══════════════════════════════════════════════════
    # 1.2 TIME-BASED MEDIA
    # ══════════════════════════════════════════════════
    {
        "id": "video-caption",
        "name": "Videos must have captions",
        "wcag": "1.2.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "<video> elements must have captions.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 1.3 ADAPTABLE
    # ══════════════════════════════════════════════════
    {
        "id": "label",
        "name": "Form inputs must have accessible labels",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Every form input must have a visible <label> or aria-label.",
        "eaa_critical": True,
    },
    {
        "id": "select-name",
        "name": "Select elements must have accessible names",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "<select> dropdowns must be labelled.",
        "eaa_critical": True,
    },
    {
        "id": "aria-required-children",
        "name": "ARIA elements must have required child roles",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "ARIA roles that require specific child roles must have them.",
        "eaa_critical": False,
    },
    {
        "id": "aria-required-parent",
        "name": "ARIA elements must be in correct parent context",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "ARIA child roles must be contained within correct parent roles.",
        "eaa_critical": False,
    },
    {
        "id": "heading-order",
        "name": "Heading levels must not be skipped",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Heading levels should only increase by one level at a time.",
        "eaa_critical": False,
    },
    {
        "id": "list",
        "name": "Lists must be structured correctly",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "<ul> and <ol> elements must only contain <li> items.",
        "eaa_critical": False,
    },
    {
        "id": "listitem",
        "name": "List items must be inside a list",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "<li> elements must be contained in <ul> or <ol>.",
        "eaa_critical": False,
    },
    {
        "id": "p-as-heading",
        "name": "Paragraphs must not be used as headings",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Bold <p> tags that look like headings should use actual heading elements.",
        "eaa_critical": False,
    },
    {
        "id": "td-headers-attr",
        "name": "Table cells must use valid header references",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Table data cells that use headers attribute must refer to existing th cells.",
        "eaa_critical": False,
    },
    {
        "id": "th-has-data-cells",
        "name": "Table headers must relate to data cells",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Each <th> element must have data cells it describes.",
        "eaa_critical": False,
    },
    {
        "id": "scope-attr-valid",
        "name": "Table scope attributes must be used correctly",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "The scope attribute must only be used on <th> elements with valid values.",
        "eaa_critical": False,
    },
    {
        "id": "table-fake-caption",
        "name": "Tables must not use cells for captions",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Table captions should use the <caption> element, not a merged cell.",
        "eaa_critical": False,
    },
    {
        "id": "form-field-multiple-labels",
        "name": "Form fields must not have multiple label elements",
        "wcag": "1.3.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "A form field with multiple <label> elements may cause confusion.",
        "eaa_critical": False,
    },
    {
        "id": "autocomplete-valid",
        "name": "Autocomplete attributes must be valid",
        "wcag": "1.3.5", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Autocomplete attribute values on personal data fields must use valid tokens.",
        "eaa_critical": True,
    },
    {
        "id": "css-orientation-lock",
        "name": "Content must not be locked to a specific orientation",
        "wcag": "1.3.4", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "CSS media queries must not restrict content to portrait or landscape only.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 1.4 DISTINGUISHABLE
    # ══════════════════════════════════════════════════
    {
        "id": "color-contrast",
        "name": "Text must have sufficient colour contrast (4.5:1)",
        "wcag": "1.4.3", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Normal text must have a contrast ratio of at least 4.5:1 against its background.",
        "eaa_critical": True,
    },
    {
        "id": "color-contrast-enhanced",
        "name": "Large text must have sufficient colour contrast (3:1)",
        "wcag": "1.4.3", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Large text (18pt or 14pt bold) must have at least 3:1 contrast ratio.",
        "eaa_critical": True,
    },
    {
        "id": "meta-viewport",
        "name": "Zoom must not be disabled",
        "wcag": "1.4.4", "level": "AA", "test_type": "automated", "severity": "critical",
        "description": "Meta viewport must not use user-scalable=no or maximum-scale less than 2.",
        "eaa_critical": True,
    },
    {
        "id": "meta-viewport-large",
        "name": "Users must be able to zoom in on content",
        "wcag": "1.4.4", "level": "AA", "test_type": "automated", "severity": "moderate",
        "description": "Meta viewport maximum-scale should be at least 5 for accessibility.",
        "eaa_critical": False,
    },
    {
        "id": "avoid-inline-spacing",
        "name": "Text spacing must not be overridden",
        "wcag": "1.4.12", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Inline CSS must not override letter-spacing, word-spacing, or line-height.",
        "eaa_critical": True,
    },
    {
        "id": "no-autoplay-audio",
        "name": "Audio must not autoplay for more than 3 seconds",
        "wcag": "1.4.2", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Autoplaying audio that lasts more than 3 seconds must have controls to stop it.",
        "eaa_critical": False,
    },
    {
        "id": "reflow",
        "name": "Content must reflow at 320px without horizontal scrolling",
        "wcag": "1.4.10", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "Content must not require horizontal scrolling when viewport width is 320px.",
        "automated_assist": "Page rendered at 320px viewport to detect horizontal overflow.",
        "manual_remaining": "Verify all content remains readable and usable without horizontal scrolling.",
        "eaa_critical": True,
    },
    {
        "id": "non-text-contrast",
        "name": "UI components and graphics must have 3:1 contrast",
        "wcag": "1.4.11", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "Graphical objects and active UI components must have 3:1 contrast against adjacent colours.",
        "automated_assist": "axe-core checks detectable non-text contrast failures.",
        "manual_remaining": "Verify icons, form borders, and interactive element boundaries meet 3:1 contrast.",
        "eaa_critical": True,
    },
    {
        "id": "text-spacing",
        "name": "Text spacing overrides must not break content",
        "wcag": "1.4.12", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "Content must remain readable when line height, letter and word spacing are increased.",
        "automated_assist": "Detected inline spacing CSS that may block overrides.",
        "manual_remaining": "Apply the text spacing bookmarklet and verify no content is lost or clipped.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 2.1 KEYBOARD ACCESSIBLE
    # ══════════════════════════════════════════════════
    {
        "id": "scrollable-region-focusable",
        "name": "Scrollable regions must be keyboard accessible",
        "wcag": "2.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Scrollable content must be reachable and operable via keyboard.",
        "eaa_critical": True,
    },
    {
        "id": "server-side-image-map",
        "name": "Server-side image maps must not be used",
        "wcag": "2.1.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Server-side image maps cannot be navigated without a mouse.",
        "eaa_critical": False,
    },
    {
        "id": "keyboard-operable",
        "name": "All functionality must be operable via keyboard",
        "wcag": "2.1.1", "level": "A", "test_type": "manual",
        "severity": "critical",
        "description": "Every feature of the page must be accessible using only a keyboard.",
        "manual_remaining": "Navigate entire page using Tab, Shift+Tab, Enter, Space, Arrow keys. Verify all features work.",
        "eaa_critical": True,
    },
    {
        "id": "focus-trap",
        "name": "Keyboard focus must not be trapped",
        "wcag": "2.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Users must be able to navigate away from any component using the keyboard.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 2.2 ENOUGH TIME
    # ══════════════════════════════════════════════════
    {
        "id": "meta-refresh",
        "name": "Pages must not auto-refresh without user control",
        "wcag": "2.2.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Meta refresh that causes a timed redirect is not allowed.",
        "eaa_critical": True,
    },
    {
        "id": "timeout-adjustable",
        "name": "Time limits must be adjustable or removable",
        "wcag": "2.2.1", "level": "A", "test_type": "manual",
        "severity": "serious",
        "description": "If a time limit exists, users must be able to turn off, adjust, or extend it.",
        "manual_remaining": "Check for session timeouts or auto-expiring forms. Verify users can extend the time.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 2.4 NAVIGABLE
    # ══════════════════════════════════════════════════
    {
        "id": "bypass",
        "name": "Mechanism to bypass repeated content must exist",
        "wcag": "2.4.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "A skip link or landmark structure must allow users to skip repeated content.",
        "eaa_critical": False,
    },
    {
        "id": "frame-title",
        "name": "Frames and iframes must have accessible names",
        "wcag": "2.4.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "<frame> and <iframe> elements must have a title attribute.",
        "eaa_critical": False,
    },
    {
        "id": "frame-focusable-content",
        "name": "Frames with focusable content must not be hidden",
        "wcag": "2.4.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Frames containing focusable elements must not use a tabindex of -1.",
        "eaa_critical": False,
    },
    {
        "id": "document-title",
        "name": "Pages must have a descriptive title",
        "wcag": "2.4.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Each HTML page must have a <title> element that describes its content.",
        "eaa_critical": True,
    },
    {
        "id": "tabindex",
        "name": "Tabindex values must not be positive",
        "wcag": "2.4.3", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Positive tabindex values disrupt the natural focus order and confuse keyboard users.",
        "eaa_critical": False,
    },
    {
        "id": "focus-order-semantics",
        "name": "Focus order must follow a logical reading sequence",
        "wcag": "2.4.3", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Elements with interactive roles must be in a logical DOM order.",
        "eaa_critical": True,
    },
    {
        "id": "link-name",
        "name": "Links must have discernible text",
        "wcag": "2.4.4", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Links must have text that describes their purpose. Avoid 'click here' or 'read more'.",
        "eaa_critical": True,
    },
    {
        "id": "page-has-heading-one",
        "name": "Pages must contain a level-one heading",
        "wcag": "2.4.6", "level": "AA", "test_type": "automated", "severity": "moderate",
        "description": "Each page should have at least one <h1> element to describe the main topic.",
        "eaa_critical": False,
    },
    {
        "id": "focus-visible",
        "name": "Keyboard focus must be clearly visible",
        "wcag": "2.4.7", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "Any keyboard-operable interface must have a visible focus indicator.",
        "automated_assist": "Verified focusable elements exist in keyboard tab sequence.",
        "manual_remaining": "Navigate with Tab key and visually confirm focus indicator is clearly visible on all interactive elements.",
        "eaa_critical": True,
    },
    {
        "id": "identical-links-same-purpose",
        "name": "Links with identical text must go to same destination",
        "wcag": "2.4.9", "level": "AAA", "test_type": "manual",
        "severity": "minor",
        "description": "Multiple links with the same text must have the same URL.",
        "manual_remaining": "Review all links with identical labels and verify they point to the same destination.",
        "eaa_critical": False,
    },
    {
        "id": "focus-not-obscured",
        "name": "Focused element must not be hidden by sticky headers",
        "wcag": "2.4.11", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "WCAG 2.2: A focused UI component must not be entirely hidden by sticky/fixed content.",
        "automated_assist": "Detected sticky or fixed header/footer elements that may overlap focused content.",
        "manual_remaining": "Navigate with Tab and verify focused elements are not completely covered by sticky headers or footers.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 2.5 INPUT MODALITIES (WCAG 2.1 + 2.2)
    # ══════════════════════════════════════════════════
    {
        "id": "label-content-name-mismatch",
        "name": "Visible label must be in accessible name",
        "wcag": "2.5.3", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "The accessible name of an element must contain the visible label text.",
        "eaa_critical": False,
    },
    {
        "id": "motion-actuation",
        "name": "Device motion must have accessible alternatives",
        "wcag": "2.5.4", "level": "A", "test_type": "manual",
        "severity": "serious",
        "description": "Functionality triggered by device motion must also be operable via UI components.",
        "manual_remaining": "Test if any features use device motion (shake, tilt) and verify there is a UI button alternative.",
        "eaa_critical": False,
    },
    {
        "id": "target-size",
        "name": "Touch targets must be at least 24x24px",
        "wcag": "2.5.8", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "WCAG 2.2: Interactive elements must have a minimum target size of 24x24 CSS pixels.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 3.1 READABLE
    # ══════════════════════════════════════════════════
    {
        "id": "html-has-lang",
        "name": "Page must have a language attribute",
        "wcag": "3.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "The <html> element must have a lang attribute to identify the page language.",
        "eaa_critical": True,
    },
    {
        "id": "html-lang-valid",
        "name": "Page language attribute must be valid",
        "wcag": "3.1.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "The lang attribute on <html> must use a valid BCP 47 language tag.",
        "eaa_critical": True,
    },
    {
        "id": "valid-lang",
        "name": "Language change attributes must be valid",
        "wcag": "3.1.2", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "lang attributes used on inline content must use valid BCP 47 language tags.",
        "eaa_critical": False,
    },

    # ══════════════════════════════════════════════════
    # 3.2 PREDICTABLE
    # ══════════════════════════════════════════════════
    {
        "id": "consistent-navigation",
        "name": "Navigation must be consistent across pages",
        "wcag": "3.2.3", "level": "AA", "test_type": "manual",
        "severity": "moderate",
        "description": "Navigation components repeated across pages must appear in the same relative order.",
        "manual_remaining": "Compare navigation structure across at least 3 pages and verify order is consistent.",
        "eaa_critical": False,
    },

    # ══════════════════════════════════════════════════
    # 3.3 INPUT ASSISTANCE
    # ══════════════════════════════════════════════════
    {
        "id": "form-errors",
        "name": "Form errors must be identified and described",
        "wcag": "3.3.1", "level": "A", "test_type": "assisted",
        "severity": "serious",
        "description": "If an input error is detected, the error must be identified and described to the user.",
        "automated_assist": "Detected form inputs and aria-invalid usage where present.",
        "manual_remaining": "Submit form with intentional errors. Confirm error messages are visible and announced by screen readers.",
        "eaa_critical": True,
    },
    {
        "id": "error-suggestion",
        "name": "Error messages must suggest corrections",
        "wcag": "3.3.3", "level": "AA", "test_type": "manual",
        "severity": "moderate",
        "description": "When input errors are detected, suggestions for correction must be provided unless it would jeopardise security.",
        "manual_remaining": "Trigger validation errors and verify the message tells the user how to fix the problem.",
        "eaa_critical": False,
    },
    {
        "id": "redundant-entry",
        "name": "Users must not be asked to re-enter information",
        "wcag": "3.3.7", "level": "A", "test_type": "manual",
        "severity": "moderate",
        "description": "WCAG 2.2: Information previously entered by the user must be auto-populated or available for selection.",
        "manual_remaining": "Test multi-step forms to verify previously entered data is not required again unnecessarily.",
        "eaa_critical": False,
    },
    {
        "id": "accessible-authentication",
        "name": "Authentication must not rely on cognitive function tests",
        "wcag": "3.3.8", "level": "AA", "test_type": "manual",
        "severity": "serious",
        "description": "WCAG 2.2: Login must not require solving a puzzle, memorising content, or transcribing characters unless alternatives exist.",
        "manual_remaining": "Review login and authentication flows. Verify users can authenticate without cognitive tests like CAPTCHAs that have no alternative.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # 4.1 COMPATIBLE
    # ══════════════════════════════════════════════════
    {
        "id": "duplicate-id-active",
        "name": "Active interactive elements must not share IDs",
        "wcag": "4.1.1", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "IDs of active focusable elements must be unique to prevent screen reader confusion.",
        "eaa_critical": False,
    },
    {
        "id": "duplicate-id-aria",
        "name": "IDs referenced by ARIA must be unique",
        "wcag": "4.1.1", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "IDs used in aria-labelledby or aria-describedby must be unique.",
        "eaa_critical": True,
    },
    {
        "id": "duplicate-id",
        "name": "IDs within a page must be unique",
        "wcag": "4.1.1", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Duplicate IDs can cause parsing failures and break assistive technology.",
        "eaa_critical": False,
    },
    {
        "id": "button-name",
        "name": "Buttons must have discernible text",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Buttons must have visible text or an accessible name via aria-label.",
        "eaa_critical": True,
    },
    {
        "id": "input-button-name",
        "name": "Input buttons must have discernible text",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "<input type='button'> must have a value attribute.",
        "eaa_critical": True,
    },
    {
        "id": "aria-required-attr",
        "name": "ARIA elements must have required attributes",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Elements with ARIA roles must have all required attributes for that role.",
        "eaa_critical": True,
    },
    {
        "id": "aria-roles",
        "name": "ARIA roles must be valid",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "ARIA role values must be valid WAI-ARIA role names.",
        "eaa_critical": True,
    },
    {
        "id": "aria-valid-attr",
        "name": "ARIA attributes must be valid",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Only valid ARIA attributes are used on elements.",
        "eaa_critical": True,
    },
    {
        "id": "aria-valid-attr-value",
        "name": "ARIA attribute values must be valid",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "ARIA attributes must have valid values as defined in the WAI-ARIA specification.",
        "eaa_critical": True,
    },
    {
        "id": "aria-prohibited-attr",
        "name": "ARIA attributes must not be prohibited",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Certain ARIA attributes are not allowed on elements with specific roles.",
        "eaa_critical": False,
    },
    {
        "id": "aria-hidden-body",
        "name": "aria-hidden must not be applied to the body",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "critical",
        "description": "Applying aria-hidden to <body> hides all content from screen readers.",
        "eaa_critical": True,
    },
    {
        "id": "aria-hidden-focus",
        "name": "aria-hidden elements must not contain focusable elements",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Focusable elements inside aria-hidden='true' containers create ghost tab stops.",
        "eaa_critical": True,
    },
    {
        "id": "aria-input-field-name",
        "name": "ARIA input fields must have accessible names",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with input roles (textbox, combobox, etc.) must have accessible names.",
        "eaa_critical": True,
    },
    {
        "id": "aria-toggle-field-name",
        "name": "ARIA toggle fields must have accessible names",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with toggle roles (checkbox, radio, switch) must have accessible names.",
        "eaa_critical": True,
    },
    {
        "id": "aria-command-name",
        "name": "ARIA command elements must have accessible names",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with command roles (button, link, menuitem) must have accessible names.",
        "eaa_critical": True,
    },
    {
        "id": "aria-tooltip-name",
        "name": "ARIA tooltip elements must have accessible names",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with role=tooltip must have accessible names.",
        "eaa_critical": False,
    },
    {
        "id": "aria-treeitem-name",
        "name": "ARIA tree items must have accessible names",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Elements with role=treeitem must have accessible names.",
        "eaa_critical": False,
    },
    {
        "id": "nested-interactive",
        "name": "Interactive controls must not be nested",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "Interactive elements must not be nested inside other interactive elements.",
        "eaa_critical": False,
    },
    {
        "id": "presentation-role-conflict",
        "name": "Presentation role elements must not have focusable children",
        "wcag": "4.1.2", "level": "A", "test_type": "automated", "severity": "minor",
        "description": "Elements with role=presentation or none must not contain focusable elements.",
        "eaa_critical": False,
    },
    {
        "id": "status-messages",
        "name": "Status messages must be programmatically determinable",
        "wcag": "4.1.3", "level": "AA", "test_type": "assisted",
        "severity": "serious",
        "description": "Status messages conveyed through colour or position must have an accessible text equivalent.",
        "automated_assist": "Detected dynamic content regions that may contain status messages.",
        "manual_remaining": "Trigger status messages (success/error) and verify they are announced by screen readers via aria-live regions.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # LANDMARK / STRUCTURE
    # ══════════════════════════════════════════════════
    {
        "id": "landmark-one-main",
        "name": "Page must have one main landmark",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Each page must have exactly one <main> element or role=main.",
        "eaa_critical": False,
    },
    {
        "id": "landmark-no-duplicate-banner",
        "name": "Page must not have more than one banner landmark",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Only one <header> or role=banner is allowed at the top level.",
        "eaa_critical": False,
    },
    {
        "id": "landmark-no-duplicate-contentinfo",
        "name": "Page must not have more than one contentinfo landmark",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Only one <footer> or role=contentinfo is allowed at the top level.",
        "eaa_critical": False,
    },
    {
        "id": "landmark-no-duplicate-main",
        "name": "Page must not have more than one main landmark",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Only one <main> or role=main is allowed per page.",
        "eaa_critical": False,
    },
    {
        "id": "region",
        "name": "All content must be contained in landmark regions",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "All page content should be inside landmark regions for navigation.",
        "eaa_critical": False,
    },
    {
        "id": "landmark-unique",
        "name": "Landmarks must be uniquely identifiable",
        "wcag": "1.3.6", "level": "A", "test_type": "automated", "severity": "moderate",
        "description": "Identical landmark roles must be differentiated with accessible labels.",
        "eaa_critical": False,
    },

    # ══════════════════════════════════════════════════
    # KEYBOARD / FOCUS SIMULATION (custom, not axe-core)
    # ══════════════════════════════════════════════════
    {
        "id": "keyboard-tab-order",
        "name": "Tab key order must be logical",
        "wcag": "2.4.3", "level": "A", "test_type": "automated", "severity": "serious",
        "description": "The keyboard tab sequence must follow a logical reading order.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # MOBILE VIEWPORT (custom)
    # ══════════════════════════════════════════════════
    {
        "id": "mobile-viewport-contrast",
        "name": "Colour contrast must pass on mobile viewport",
        "wcag": "1.4.3", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Contrast failures specific to mobile viewport (375px) must be resolved.",
        "eaa_critical": True,
    },
    {
        "id": "mobile-touch-targets",
        "name": "Touch targets must meet minimum size on mobile",
        "wcag": "2.5.8", "level": "AA", "test_type": "automated", "severity": "serious",
        "description": "Interactive elements on mobile viewport must be at least 24x24px.",
        "eaa_critical": True,
    },

    # ══════════════════════════════════════════════════
    # SCREEN READER (manual)
    # ══════════════════════════════════════════════════
    {
        "id": "screen-reader-name-role-value",
        "name": "All UI components must have accessible name, role and value",
        "wcag": "4.1.2", "level": "A", "test_type": "manual",
        "severity": "critical",
        "description": "Verify with a screen reader that all controls announce their name, role and state correctly.",
        "manual_remaining": "Use NVDA + Chrome or VoiceOver + Safari. Tab through the page and verify every interactive element announces its name, role and current value/state.",
        "eaa_critical": True,
    },
]
