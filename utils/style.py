"""
utils/style.py
All CSS for the Production Dashboard — injected via st.markdown at app startup.
"""


def get_css() -> str:
    return """
<style>
/* ─── Google Font ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #1A1A2E;
}

p, span, label, div {
    color: #1A1A2E;
}

/* Streamlit widget labels */
.stSelectbox label, .stMultiSelect label, .stTextInput label,
.stDateInput label, .stNumberInput label {
    font-weight: 600 !important;
    color: #1A1A2E !important;
    font-size: 0.85rem !important;
}

/* ─── App Background ──────────────────────────────────────── */
.stApp {
    background: #F7F8FC;
}

/* ─── Hide default Streamlit header/footer decorations ───── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ─── Top Navigation Buttons ─────────────────────────────── */
div[data-testid="stHorizontalBlock"] button {
    border-radius: 25px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    height: 42px !important;
    white-space: nowrap !important;
}

/* Secondary (inactive) nav buttons */
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    background: #ffffff !important;
    border: 2px solid #6C63FF !important;
    color: #6C63FF !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    background: #EEF2FF !important;
    border-color: #6C63FF !important;
}

/* Primary (active) nav buttons */
div[data-testid="stHorizontalBlock"] button[kind="primary"] {
    background: #6C63FF !important;
    border: 2px solid #6C63FF !important;
    color: #ffffff !important;
}

/* ─── Purple divider under nav ────────────────────────────── */
.nav-divider {
    height: 3px;
    background: linear-gradient(90deg, #6C63FF 0%, #A78BFA 100%);
    border-radius: 2px;
    margin: 10px 0 20px 0;
}

/* ─── KPI Cards ───────────────────────────────────────────── */
.kpi-row {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.kpi-card {
    background: #ffffff;
    border-left: 5px solid #6C63FF;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(108,99,255,0.08);
    flex: 1;
    min-width: 140px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(108,99,255,0.14);
}
.kpi-icon {
    font-size: 1.4rem;
    margin-bottom: 6px;
}
.kpi-value { font-size: 2rem; font-weight: 800; color: #0F0E2A; line-height: 1.1; }
.kpi-label { font-size: 0.78rem; color: #444; margin-top: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

/* ─── Section Title ───────────────────────────────────────── */
.section-title { font-size: 1.4rem; font-weight: 800; color: #0F0E2A; margin-bottom: 18px; display: flex; align-items: center; gap: 8px; border-bottom: 2px solid #EEF2FF; padding-bottom: 10px; }

/* ─── Month Header Dividers (Production Sheet) ────────────── */
.month-header { background: #E0E7FF; border-left: 4px solid #4F46E5; padding: 9px 16px; border-radius: 7px; font-weight: 800; font-size: 0.95rem; color: #0F0E2A; margin: 18px 0 4px 0; display: flex; align-items: center; gap: 8px; }
.ep-count { font-weight: 700; color: #3730A3; font-size: 0.82rem; background: #C4B5FD; border-radius: 20px; padding: 2px 10px; }

/* ─── Result Count Badge ──────────────────────────────────── */
.result-badge { display: inline-block; background: #EEF2FF; border: 1px solid #7C3AED; border-radius: 20px; padding: 4px 14px; font-size: 0.78rem; color: #3730A3; font-weight: 700; margin-bottom: 10px; }

/* ─── Subtotal Row (Production Sheet) ────────────────────── */
.subtotal-row {
    background: #F3F0FF;
    font-weight: 700;
    color: #1A1A2E;
    border-radius: 5px;
    padding: 5px 8px;
}

/* ─── Grand Total Row ─────────────────────────────────────── */
.grand-total-row {
    background: #6C63FF;
    color: #ffffff;
    font-weight: 700;
    border-radius: 7px;
    padding: 6px 8px;
}

/* ─── Expander styling ────────────────────────────────────── */
details summary {
    font-weight: 600;
    color: #6C63FF;
}

/* ─── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #1A1A2E;
    color: #ffffff;
}
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* ─── DataFrame table ─────────────────────────────────────── */
.stDataFrame tbody tr:hover {
    background: #EEF2FF !important;
}

/* ─── Status dot ──────────────────────────────────────────── */
.status-dot-green {
    display: inline-block;
    width: 10px; height: 10px;
    background: #22C55E;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-dot-red {
    display: inline-block;
    width: 10px; height: 10px;
    background: #EF4444;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}

/* ─── Toast override ──────────────────────────────────────── */
div[data-testid="stToast"] {
    background: #6C63FF !important;
    color: white !important;
    border-radius: 10px !important;
}
</style>
"""
