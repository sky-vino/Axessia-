# ======================================================
# AXESSIA – ROOT APPLICATION (WSC + MSA ANDROID + MSA iOS)
# ======================================================

import streamlit as st
import os

# ------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------
st.set_page_config(
    page_title="Axessia – Accessibility Intelligence",
    layout="wide",
)

# ------------------------------------------------------
# GLOBAL SESSION STATE (SAFE, SHARED)
# ------------------------------------------------------
if "history" not in st.session_state:
    # Unified scan history across surfaces
    st.session_state.history = {
        "WSC": {},          # { url: result }
        "MSA_ANDROID": {},  # { app_package: result }
        "MSA_IOS": {},      # { app_name: result }
    }

# ------------------------------------------------------
# SIDEBAR – NAVIGATION
# ------------------------------------------------------
st.sidebar.title("Axessia")

surface = st.sidebar.radio(
    "Select Surface",
    [
        "WSC",
        "MSA (Android)",
        "MSA (iOS – Assisted)",
    ],
    key="surface_selector"
)

st.sidebar.divider()

# ------------------------------------------------------
# SIDEBAR – HISTORY (READ-ONLY SELECTOR)
# ------------------------------------------------------
st.sidebar.subheader("Scan History")

selected_history_item = None

if surface == "WSC" and st.session_state.history["WSC"]:
    selected_history_item = st.sidebar.selectbox(
        "Web Scans",
        list(st.session_state.history["WSC"].keys()),
        key="wsc_history_select"
    )

elif surface == "MSA (Android)" and st.session_state.history["MSA_ANDROID"]:
    selected_history_item = st.sidebar.selectbox(
        "Android Apps",
        list(st.session_state.history["MSA_ANDROID"].keys()),
        key="msa_android_history_select"
    )

elif surface == "MSA (iOS – Assisted)" and st.session_state.history["MSA_IOS"]:
    selected_history_item = st.sidebar.selectbox(
        "iOS Apps",
        list(st.session_state.history["MSA_IOS"].keys()),
        key="msa_ios_history_select"
    )

st.sidebar.divider()

# ------------------------------------------------------
# ROUTING LOGIC (CRITICAL PART)
# ------------------------------------------------------
# ⚠️ IMPORTANT:
# - We DO NOT wrap WSC / MSA code internally
# - Each surface is executed as an independent app
# - This preserves Streamlit execution semantics
# ------------------------------------------------------

if surface == "WSC":
    # --------------------------------------------------
    # WEB SCAN CONSOLE
    # --------------------------------------------------
    if not os.path.exists("app_wsc.py"):
        st.error("app_wsc.py not found. Please ensure WSC file exists.")
        st.stop()

    # Expose unified history (read/write)
    globals()["AXESSIA_HISTORY"] = st.session_state.history

    exec(
        open("app_wsc.py", encoding="utf-8").read(),
        globals()
    )

elif surface == "MSA (Android)":
    # --------------------------------------------------
    # MOBILE SCAN ASSISTANT – ANDROID
    # --------------------------------------------------
    if not os.path.exists("app_msa.py"):
        st.error("app_msa.py not found. Please ensure Android MSA file exists.")
        st.stop()

    globals()["AXESSIA_HISTORY"] = st.session_state.history

    exec(
        open("app_msa.py", encoding="utf-8").read(),
        globals()
    )

else:
    # --------------------------------------------------
    # MOBILE SCAN ASSISTANT – iOS (ASSISTED)
    # --------------------------------------------------
    if not os.path.exists("app_msa_ios.py"):
        st.error("app_msa_ios.py not found. Please ensure iOS MSA file exists.")
        st.stop()

    globals()["AXESSIA_HISTORY"] = st.session_state.history

    exec(
        open("app_msa_ios.py", encoding="utf-8").read(),
        globals()
    )
