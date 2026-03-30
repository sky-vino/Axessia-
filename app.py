# ======================================================
# AXESSIA – Root Application (Sky Branded)
# WSC + MSA Android + MSA iOS
# ======================================================

import streamlit as st
import os
import base64

st.set_page_config(
    page_title="Axessia – Accessibility Intelligence",
    layout="wide",
    page_icon="🌐",
    initial_sidebar_state="expanded",
)

# ── Encode Sky logo for inline use ─────────────────────
def get_logo_b64():
    logo_path = "sky.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_b64 = get_logo_b64()

# ── Dark/Light mode toggle ──────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ── Sky brand colors ────────────────────────────────────
# From logo gradient: Orange → Red → Magenta → Purple → Blue
SKY_ORANGE  = "#FF6219"
SKY_RED     = "#E8192C"
SKY_MAGENTA = "#C8196E"
SKY_PURPLE  = "#8B2FC9"
SKY_BLUE    = "#1C6FD4"
SKY_CYAN    = "#00A8E8"

GRADIENT = f"linear-gradient(135deg, {SKY_ORANGE}, {SKY_RED}, {SKY_MAGENTA}, {SKY_PURPLE}, {SKY_BLUE})"

# ── Theme variables ──────────────────────────────────────
if st.session_state.dark_mode:
    BG_PRIMARY    = "#0D0D14"
    BG_SECONDARY  = "#16161F"
    BG_CARD       = "#1E1E2A"
    TEXT_PRIMARY  = "#F0F0F8"
    TEXT_SECONDARY= "#A0A0B8"
    BORDER        = "#2E2E3E"
    SIDEBAR_BG    = "#11111A"
    INPUT_BG      = "#1E1E2A"
    TOGGLE_ICON   = "☀️"
    TOGGLE_LABEL  = "Light Mode"
else:
    BG_PRIMARY    = "#F5F5FA"
    BG_SECONDARY  = "#EBEBF5"
    BG_CARD       = "#FFFFFF"
    TEXT_PRIMARY  = "#0D0D14"
    TEXT_SECONDARY= "#555570"
    BORDER        = "#DDDDE8"
    SIDEBAR_BG    = "#EBEBF5"
    INPUT_BG      = "#FFFFFF"
    TOGGLE_ICON   = "🌙"
    TOGGLE_LABEL  = "Dark Mode"

# ── Inject CSS ──────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  /* ── Global reset ── */
  html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
    background-color: {BG_PRIMARY} !important;
    color: {TEXT_PRIMARY} !important;
  }}

  /* ── Main container ── */
  .main .block-container {{
    background-color: {BG_PRIMARY} !important;
    padding-top: 1rem !important;
    max-width: 1400px !important;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
    background-color: {SIDEBAR_BG} !important;
    border-right: 1px solid {BORDER} !important;
  }}
  [data-testid="stSidebar"] * {{
    color: {TEXT_PRIMARY} !important;
  }}

  /* ── Sky gradient header bar ── */
  .sky-header {{
    background: {GRADIENT};
    padding: 16px 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 24px rgba(200, 25, 110, 0.25);
  }}
  .sky-header img {{
    height: 40px;
    width: auto;
    filter: brightness(0) invert(1);
  }}
  .sky-header-text {{
    color: white !important;
  }}
  .sky-header-title {{
    font-size: 1.4rem;
    font-weight: 800;
    color: white !important;
    letter-spacing: -0.3px;
    margin: 0;
    line-height: 1.2;
  }}
  .sky-header-sub {{
    font-size: 0.8rem;
    color: rgba(255,255,255,0.8) !important;
    margin: 0;
  }}

  /* ── Cards / containers ── */
  [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
  }}

  /* ── Buttons ── */
  .stButton > button {{
    background: {GRADIENT} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: opacity 0.2s, transform 0.1s !important;
    box-shadow: 0 2px 12px rgba(200, 25, 110, 0.3) !important;
  }}
  .stButton > button:hover {{
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
  }}
  .stButton > button[kind="secondary"] {{
    background: {BG_CARD} !important;
    color: {SKY_MAGENTA} !important;
    border: 1.5px solid {SKY_MAGENTA} !important;
    box-shadow: none !important;
  }}

  /* ── Metrics ── */
  [data-testid="stMetric"] {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
  }}
  [data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
  }}
  [data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
  }}

  /* ── Inputs ── */
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea,
  .stNumberInput > div > div > input,
  .stSelectbox > div > div {{
    background-color: {INPUT_BG} !important;
    color: {TEXT_PRIMARY} !important;
    border: 1.5px solid {BORDER} !important;
    border-radius: 8px !important;
  }}
  .stTextInput > div > div > input:focus,
  .stTextArea > div > div > textarea:focus {{
    border-color: {SKY_MAGENTA} !important;
    box-shadow: 0 0 0 3px rgba(200, 25, 110, 0.12) !important;
  }}

  /* ── Labels ── */
  .stTextInput label, .stTextArea label,
  .stNumberInput label, .stSelectbox label,
  .stRadio label, .stCheckbox label {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 500 !important;
  }}

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_SECONDARY} !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 2px !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {TEXT_SECONDARY} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    border: none !important;
  }}
  .stTabs [aria-selected="true"] {{
    background: {GRADIENT} !important;
    color: white !important;
    font-weight: 600 !important;
  }}

  /* ── Expanders ── */
  [data-testid="stExpander"] {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
  }}
  [data-testid="stExpander"] summary {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 600 !important;
  }}

  /* ── Info / Warning / Success / Error ── */
  .stAlert {{
    border-radius: 8px !important;
    border-left-width: 4px !important;
  }}

  /* ── Sidebar radio buttons ── */
  .stRadio [data-testid="stMarkdownContainer"] p {{
    font-size: 0.9rem !important;
    font-weight: 500 !important;
  }}

  /* ── Sky gradient text util class ── */
  .sky-gradient-text {{
    background: {GRADIENT};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800;
  }}

  /* ── Divider ── */
  hr {{
    border-color: {BORDER} !important;
    margin: 16px 0 !important;
  }}

  /* ── Download buttons ── */
  .stDownloadButton > button {{
    background: {BG_CARD} !important;
    color: {SKY_PURPLE} !important;
    border: 1.5px solid {SKY_PURPLE} !important;
    box-shadow: none !important;
  }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {BG_SECONDARY}; }}
  ::-webkit-scrollbar-thumb {{
    background: {GRADIENT};
    border-radius: 3px;
  }}

  /* ── Table / dataframe ── */
  .stDataFrame {{
    border-radius: 10px !important;
    overflow: hidden !important;
  }}

  /* ── Progress bar ── */
  .stProgress > div > div {{
    background: {GRADIENT} !important;
    border-radius: 4px !important;
  }}

  /* ── Spinner ── */
  .stSpinner > div {{
    border-top-color: {SKY_MAGENTA} !important;
  }}

  /* ── Hide Streamlit default header/footer ── */
  #MainMenu {{ visibility: hidden; }}
  footer    {{ visibility: hidden; }}
  header    {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ── Sidebar — Sky logo + navigation ────────────────────
with st.sidebar:

    # Sky logo
    if logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:80px; margin-bottom:8px; display:block;" />',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="font-size:1.1rem;font-weight:800;margin:0;letter-spacing:-0.3px;">'
        'Axessia</p>'
        '<p style="font-size:0.72rem;color:#888;margin:2px 0 16px 0;">'
        'Accessibility Intelligence</p>',
        unsafe_allow_html=True,
    )

    # Dark/light toggle
    col_toggle, _ = st.columns([3, 1])
    with col_toggle:
        if st.button(
            f"{TOGGLE_ICON} {TOGGLE_LABEL}",
            key="theme_toggle",
            use_container_width=True,
        ):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.divider()

    surface = st.radio(
        "Select Surface",
        ["WSC", "MSA (Android)", "MSA (iOS – Assisted)"],
        key="surface_selector",
    )

    st.divider()

    # ── History ────────────────────────────────────────
    if "history" not in st.session_state:
        st.session_state.history = {
            "WSC":         {},
            "MSA_ANDROID": {},
            "MSA_IOS":     {},
        }

    st.markdown(
        '<p style="font-size:0.75rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.8px;margin-bottom:6px;">Scan History</p>',
        unsafe_allow_html=True,
    )

    if surface == "WSC" and st.session_state.history["WSC"]:
        st.selectbox("Web Scans", list(st.session_state.history["WSC"].keys()), key="wsc_history_select")
    elif surface == "MSA (Android)" and st.session_state.history["MSA_ANDROID"]:
        st.selectbox("Android Apps", list(st.session_state.history["MSA_ANDROID"].keys()), key="msa_android_history_select")
    elif surface == "MSA (iOS – Assisted)" and st.session_state.history["MSA_IOS"]:
        st.selectbox("iOS Apps", list(st.session_state.history["MSA_IOS"].keys()), key="msa_ios_history_select")
    else:
        st.caption("No scans yet.")

    st.divider()
    st.markdown(
        f'<p style="font-size:0.68rem;color:#888;text-align:center;">'
        f'{"🌙 Dark" if st.session_state.dark_mode else "☀️ Light"} mode</p>',
        unsafe_allow_html=True,
    )


# ── Sky gradient header ─────────────────────────────────
surface_labels = {
    "WSC":                "Web Scan Console",
    "MSA (Android)":      "Mobile Scan Assistant — Android",
    "MSA (iOS – Assisted)": "Mobile Scan Assistant — iOS",
}

surface_icons = {
    "WSC":                "🌐",
    "MSA (Android)":      "📱",
    "MSA (iOS – Assisted)": "🍎",
}

logo_img = f'<img src="data:image/png;base64,{logo_b64}" />' if logo_b64 else "⚡"

st.markdown(f"""
<div class="sky-header">
  {logo_img}
  <div class="sky-header-text">
    <p class="sky-header-title">Axessia — Accessibility Intelligence</p>
    <p class="sky-header-sub">{surface_icons.get(surface,'')} {surface_labels.get(surface,'')}</p>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Route to surface ────────────────────────────────────
globals()["AXESSIA_HISTORY"] = st.session_state.history

if surface == "WSC":
    exec(open("app_wsc.py", encoding="utf-8").read(), globals())
elif surface == "MSA (Android)":
    exec(open("app_msa.py", encoding="utf-8").read(), globals())
else:
    exec(open("app_msa_ios.py", encoding="utf-8").read(), globals())