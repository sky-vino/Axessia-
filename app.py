# ======================================================
# AXESSIA – Web Scan Console (WSC)
# Azure App Service Entry Point
# ======================================================

import streamlit as st
import os

st.set_page_config(
    page_title="Axessia – Accessibility Intelligence",
    layout="wide",
    page_icon="⚡",
)

# ── Session state init ─────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = {"WSC": {}}

# ── Sidebar ────────────────────────────────────────────
st.sidebar.title("⚡ Axessia")
st.sidebar.caption("Web Accessibility Intelligence")
st.sidebar.divider()

if st.session_state.history["WSC"]:
    st.sidebar.subheader("Scan History")
    st.sidebar.selectbox(
        "Web Scans",
        list(st.session_state.history["WSC"].keys()),
        key="wsc_history_select",
    )

st.sidebar.divider()

# ── Load WSC surface ───────────────────────────────────
globals()["AXESSIA_HISTORY"] = st.session_state.history

exec(open("app_wsc.py", encoding="utf-8").read(), globals())
