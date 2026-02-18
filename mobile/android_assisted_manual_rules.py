# android_assisted_manual_rules.py

def get_assisted_rules() -> list:
    return [
        {
            "id": "android-focus-order",
            "name": "Focus order must be logical",
            "wcag": "2.4.3",
            "level": "A",
            "test_type": "assisted",
            "severity": "serious",
            "status": "assisted",
            "instances": [],
            "automated_assist": (
                "Verified that focusable elements exist and accessibility nodes are present."
            ),
            "manual_remaining": (
                "Verify TalkBack reading order matches the visual and logical order "
                "using swipe navigation."
            )
        },
        {
            "id": "android-scroll-reachability",
            "name": "Scrollable content must be reachable",
            "wcag": "2.1.1",
            "level": "A",
            "test_type": "assisted",
            "severity": "moderate",
            "status": "assisted",
            "instances": [],
            "automated_assist": (
                "Detected presence of scrollable containers."
            ),
            "manual_remaining": (
                "Verify all content can be reached using TalkBack scroll gestures."
            )
        },
        {
            "id": "android-error-identification",
            "name": "Errors must be clearly identified",
            "wcag": "3.3.1",
            "level": "A",
            "test_type": "assisted",
            "severity": "serious",
            "status": "assisted",
            "instances": [],
            "automated_assist": (
                "Detected form fields and potential error containers."
            ),
            "manual_remaining": (
                "Verify error messages are meaningful and announced correctly by TalkBack."
            )
        }
    ]


def get_manual_rules() -> list:
    return [
        {
            "id": "android-gesture-alternatives",
            "name": "Complex gestures must have alternatives",
            "wcag": "2.5.1",
            "level": "A",
            "test_type": "manual",
            "severity": "critical",
            "status": "manual",
            "instances": [],
            "manual_remaining": (
                "Verify all multi-touch or custom gestures have accessible alternatives."
            )
        },
        {
            "id": "android-cognitive-load",
            "name": "Interface must not impose excessive cognitive load",
            "wcag": "3.3.2",
            "level": "AA",
            "test_type": "manual",
            "severity": "moderate",
            "status": "manual",
            "instances": [],
            "manual_remaining": (
                "Evaluate clarity, consistency, and simplicity of instructions and flows."
            )
        },
        {
            "id": "android-captcha-alternatives",
            "name": "CAPTCHAs must have accessible alternatives",
            "wcag": "1.1.1",
            "level": "A",
            "test_type": "manual",
            "severity": "critical",
            "status": "manual",
            "instances": [],
            "manual_remaining": (
                "Verify CAPTCHA challenges provide accessible alternatives for disabled users."
            )
        }
    ]
