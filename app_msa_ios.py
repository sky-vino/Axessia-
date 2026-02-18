# app_msa_ios.py
import streamlit as st
import uuid
from datetime import datetime

from ios_rules_registry import get_ios_assisted_rules
from eaa_scoring_ios import compute_ios_eaa_score, compute_ios_risk
from pdf_report import generate_pdf_report


# =================================================
# SESSION STATE
# =================================================
if "ios_view" not in st.session_state:
    st.session_state.ios_view = "gate"   # gate | dashboard | verify_screen | screen_list | screen_detail

if "ios_app" not in st.session_state:
    st.session_state.ios_app = None

if "ios_active_screen" not in st.session_state:
    st.session_state.ios_active_screen = None

if "ios_tester" not in st.session_state:
    st.session_state.ios_tester = None


# =================================================
# DEVICE + TESTER CONFIRMATION (EVINCED STYLE)
# =================================================
if st.session_state.ios_view == "gate":

    st.subheader("🍎 iOS Assisted Verification")

    st.warning(
        "iOS accessibility verification requires a **physical iOS device** with "
        "**VoiceOver enabled**. Automated inspection is not possible on iOS."
    )

    c1 = st.checkbox("I am using a physical iOS device")
    c2 = st.checkbox("VoiceOver is enabled on the device")
    c3 = st.checkbox("I am performing live verification on the device")

    tester = st.text_input("Verifier name (required for audit trail)")

    if c1 and c2 and c3 and tester:
        if st.button("Proceed to Verification", type="primary"):
            st.session_state.ios_tester = tester
            st.session_state.ios_view = "dashboard"
            st.rerun()
    else:
        st.info("All confirmations and verifier name are required.")

# =================================================
# DASHBOARD
# =================================================
elif st.session_state.ios_view == "dashboard":

    st.subheader("MSA – iOS Assisted Verification")

    app_name = st.text_input("App Name")
    bundle_id = st.text_input("Bundle ID (optional)")
    expected = st.number_input("Expected Screens", min_value=1, value=1)

    if st.button("➕ Verify New Screen", type="primary") and app_name:
        st.session_state.ios_app = {
            "platform": "ios",
            "mode": "assisted_verification",
            "app_name": app_name,
            "bundle_id": bundle_id,
            "expected": expected,
            "verifier": st.session_state.ios_tester,
            "screens": [],
        }
        st.session_state.ios_view = "verify_screen"
        st.rerun()

# =================================================
# VERIFY SCREEN (EVINCED-LIKE, ONE-WAY)
# =================================================
elif st.session_state.ios_view == "verify_screen":

    st.subheader("Verify iOS Screen")

    st.info(
        "Navigate to the target screen on your iOS device with VoiceOver ON. "
        "Perform verification, capture evidence, then record outcomes below."
    )

    screen_name = st.text_input("Screen name")

    st.markdown("### Evidence (mandatory)")
    evidence = st.file_uploader(
        "Upload screenshot or short screen recording",
        type=["png", "jpg", "jpeg", "mp4", "mov"]
    )

    rules = get_ios_assisted_rules()

    st.markdown("### Verification Checklist")
    for r in rules:
        r["status"] = st.radio(
            f"{r['name']} ({r['wcag']})",
            ["pass", "fail", "not_verified"],
            horizontal=True,
            key=f"{screen_name}_{r['id']}",
        )

    if st.button("Complete Verification"):
        if not screen_name:
            st.error("Screen name is required.")
        elif not evidence:
            st.error("Evidence is required to complete verification.")
        else:
            screen = {
                "id": str(uuid.uuid4()),
                "name": screen_name,
                "rules": rules,
                "verifier": st.session_state.ios_tester,
                "verified_at": datetime.utcnow().isoformat(),
                "evidence_name": evidence.name,
                "verified": True,
            }

            screen["eaa_score"] = compute_ios_eaa_score(rules)
            screen["risk"] = compute_ios_risk(screen["eaa_score"])

            st.session_state.ios_app["screens"].append(screen)
            st.session_state.ios_view = "screen_list"
            st.rerun()

# =================================================
# SCREEN LIST (READ-ONLY, VERIFIED)
# =================================================
elif st.session_state.ios_view == "screen_list":

    app = st.session_state.ios_app

    st.subheader(f"Verified Results – {app['app_name']}")
    st.caption(
        f"Verification performed by **{app['verifier']}** | "
        "Evidence-backed iOS Assisted Verification"
    )

    for s in app["screens"]:
        with st.container(border=True):
            st.markdown(f"### {s['name']}")
            st.write(f"Status: **Verified**")
            st.write(f"Evidence: `{s['evidence_name']}`")

            st.metric("Verified EAA Score", f"{s['eaa_score']}%")
            st.metric("Risk", s["risk"].upper())

            c1, c2 = st.columns(2)
            if c1.button("View Verified Details", key=s["id"]):
                st.session_state.ios_active_screen = s
                st.session_state.ios_view = "screen_detail"
                st.rerun()

            c2.download_button(
                "Export Verified PDF",
                generate_pdf_report(
                    f"{app['app_name']} – {s['name']} (Verified)",
                    {
                        "rules": s["rules"],
                        "verifier": s["verifier"],
                        "verified_at": s["verified_at"],
                        "evidence": s["evidence_name"],
                    },
                ),
                file_name=f"axessia_ios_verified_{s['name']}.pdf",
            )

    if st.button("➕ Verify Another Screen"):
        st.session_state.ios_view = "verify_screen"
        st.rerun()

# =================================================
# SCREEN DETAIL (LOCKED / READ-ONLY)
# =================================================
else:
    s = st.session_state.ios_active_screen

    st.subheader(f"{s['name']} (Verified)")

    st.caption(
        f"Verified by **{s['verifier']}** on {s['verified_at']} | "
        f"Evidence: `{s['evidence_name']}`"
    )

    if st.button("← Back to Verified Screens"):
        st.session_state.ios_view = "screen_list"
        st.rerun()

    tabs = st.tabs(["Issues", "Manual & Assisted", "EAA Readiness"])

    with tabs[0]:
        for r in s["rules"]:
            if r["status"] == "fail":
                st.error(f"{r['name']} ({r['wcag']})")

    with tabs[1]:
        for r in s["rules"]:
            st.info(f"{r['name']} → {r['manual_remaining']}")

    with tabs[2]:
        st.metric("Verified EAA Score", f"{s['eaa_score']}%")
        st.metric("Risk", s["risk"].upper())
