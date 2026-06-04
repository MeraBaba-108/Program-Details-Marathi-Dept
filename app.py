"""
app.py — Content Production Dashboard (Single-Page Streamlit App)
All six sections live here as render_X() functions.
Navigation via st.session_state["active_section"] + pill-shaped top buttons.
"""

from __future__ import annotations

import io
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.style import get_css
from utils.gsheets import get_production_log, get_masters, append_entry
from utils.helpers import (
    format_date, next_sr_no, make_episode_range, episodes_this_month,
    group_by_month, build_shows_table, build_subjects_table,
    build_content_types_table, df_to_excel_bytes, production_sheet_to_excel,
)

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    layout="wide",
    page_title="Production Dashboard",
    page_icon="🎬",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
# INJECT CSS
# ══════════════════════════════════════════════════════════════════
st.markdown(get_css(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════
if "active_section" not in st.session_state:
    st.session_state["active_section"] = "dashboard"
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = datetime.now()
if "sheet_status" not in st.session_state:
    st.session_state["sheet_status"] = "unknown"


def set_section(name: str) -> None:
    st.session_state["active_section"] = name


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════
def load_data(force: bool = False) -> tuple[pd.DataFrame, str]:
    if force:
        get_production_log.clear()
    df, err = get_production_log()
    if err:
        st.session_state["sheet_status"] = "disconnected"
        st.warning(f"⚠️ Could not reach Google Sheets. `{err}`")
        return pd.DataFrame(), "disconnected"
    st.session_state["sheet_status"] = "connected"
    if not force:
        # Only update refresh time on first load each minute (cache handles the rest)
        pass
    return df, "connected"


def load_masters(force: bool = False) -> dict:
    if force:
        get_masters.clear()
    masters, _ = get_masters()
    return masters if masters else {"show_names": [], "content_types": [], "subjects": [], "languages": []}


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🎬 Production Dashboard")
        st.markdown("---")

        # Last refresh time
        last = st.session_state.get("last_refresh", datetime.now())
        delta = datetime.now() - last
        mins = int(delta.total_seconds() // 60)
        secs = int(delta.total_seconds() % 60)
        if mins == 0:
            refresh_label = f"{secs}s ago"
        else:
            refresh_label = f"{mins}m {secs}s ago"
        st.markdown(f"🕐 **Last refreshed:** {refresh_label}")

        if st.button("🔄 Refresh Data", use_container_width=True):
            get_production_log.clear()
            get_masters.clear()
            st.session_state["last_refresh"] = datetime.now()
            st.rerun()

        st.markdown("---")

        status = st.session_state.get("sheet_status", "unknown")
        if status == "connected":
            st.markdown('<span class="status-dot-green"></span> **Sheet: Connected**', unsafe_allow_html=True)
        elif status == "disconnected":
            st.markdown('<span class="status-dot-red"></span> **Sheet: Disconnected**', unsafe_allow_html=True)
        else:
            st.markdown("⚪ Sheet: Checking…")


# ══════════════════════════════════════════════════════════════════
# TOP NAVIGATION BAR
# ══════════════════════════════════════════════════════════════════
def render_nav() -> None:
    sections = [
        ("🏠", "Dashboard",        "dashboard"),
        ("📺", "Shows",            "shows"),
        ("🎬", "Episodes",         "episodes"),
        ("📚", "Subjects",         "subjects"),
        ("🎭", "Content Types",    "content_types"),
        ("📅", "Production Sheet", "production_sheet"),
    ]
    cols = st.columns(len(sections))
    for col, (icon, label, key) in zip(cols, sections):
        is_active = st.session_state["active_section"] == key
        with col:
            if st.button(
                f"{icon} {label}",
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                set_section(key)
                st.rerun()

    # Purple gradient divider
    st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# SECTION 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════
def render_dashboard(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">🏠 Dashboard</div>', unsafe_allow_html=True)

    # ── KPI Cards ────────────────────────────────────────────────
    if df.empty:
        total_shows = total_episodes = total_subjects = total_content_types = 0
        eps_this_month = latest_date = "—"
    else:
        total_shows         = df["Show_Name"].nunique()
        total_episodes      = int(df["No_of_Episodes"].sum())
        total_subjects      = df["Subject"].nunique()
        total_content_types = df["Content_Type"].nunique()
        eps_this_month      = episodes_this_month(df)
        latest_date         = format_date(df["Date"].max())

    kpis = [
        ("📺", "Total Shows",         total_shows),
        ("🎬", "Total Episodes",      total_episodes),
        ("📚", "Total Subjects",      total_subjects),
        ("🎭", "Content Types",       total_content_types),
        ("📆", "Episodes This Month", eps_this_month),
        ("🗓️", "Latest Recording",   latest_date),
    ]

    kpi_html = '<div class="kpi-row">'
    for icon, label, value in kpis:
        kpi_html += f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>"""
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── Charts ───────────────────────────────────────────────────
    if not df.empty:
        col1, col2, col3 = st.columns(3)

        # Bar: Total Episodes per Show
        with col1:
            eps_by_show = (
                df.groupby("Show_Name")["No_of_Episodes"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            bar_height = max(340, len(eps_by_show) * 30)
            fig1 = px.bar(
                eps_by_show,
                x="No_of_Episodes", y="Show_Name",
                orientation="h",
                title="Episodes per Show",
                color_discrete_sequence=["#6C63FF"],
                labels={"No_of_Episodes": "Episodes", "Show_Name": ""},
            )
            fig1.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=bar_height,
                margin=dict(l=0, r=10, t=40, b=10),
                yaxis=dict(autorange="reversed"),
                title_font=dict(size=14, color="#0F0E2A"),
                font=dict(color="#0F0E2A"),
            )
            fig1.update_xaxes(showgrid=True, gridcolor="#EEF2FF")
            st.plotly_chart(fig1, use_container_width=True)

        # Donut: Episodes by Content Type
        with col2:
            eps_by_ct = (
                df.groupby("Content_Type")["No_of_Episodes"]
                .sum()
                .reset_index()
            )
            fig2 = px.pie(
                eps_by_ct,
                names="Content_Type", values="No_of_Episodes",
                hole=0.52,
                title="Episodes by Content Type",
                color_discrete_sequence=px.colors.sequential.Purples_r,
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=max(340, bar_height),
                margin=dict(l=0, r=0, t=40, b=10),
                title_font=dict(size=14, color="#0F0E2A"),
                font=dict(color="#0F0E2A"),
                legend=dict(orientation="h", y=-0.15),
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True)

        # Bar: Monthly Episode Trend
        with col3:
            df_trend = df.copy()
            df_trend["Month"] = df_trend["Date"].dt.to_period("M").astype(str)
            monthly = (
                df_trend.groupby("Month")["No_of_Episodes"]
                .sum()
                .reset_index()
                .sort_values("Month")
            )
            fig3 = px.bar(
                monthly,
                x="Month", y="No_of_Episodes",
                title="Monthly Episode Trend",
                color_discrete_sequence=["#A78BFA"],
                labels={"No_of_Episodes": "Episodes", "Month": ""},
            )
            fig3.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=max(340, bar_height),
                margin=dict(l=0, r=10, t=40, b=10),
                title_font=dict(size=14, color="#0F0E2A"),
                font=dict(color="#0F0E2A"),
            )
            fig3.update_yaxes(showgrid=True, gridcolor="#EEF2FF")
            fig3.update_xaxes(tickangle=-35)
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No data available. Add entries via the Episodes section or run seed_data.py.")

    # ── Recent Entries ───────────────────────────────────────────
    st.markdown("#### 🕐 Recent Entries")
    if not df.empty:
        recent = (
            df.sort_values("Date", ascending=False)
            [["Date", "Show_Name", "Episode_Range", "No_of_Episodes",
              "Content_Type", "Subject", "Language"]]
            .copy()
        )
        recent["Date"] = recent["Date"].apply(format_date)
        recent.columns = ["Date", "Show Name", "Episode Range",
                          "Episodes", "Content Type", "Subject", "Language"]
        st.markdown(
            f'<span class="result-badge">All {len(recent)} entries</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No recent entries.")


# ══════════════════════════════════════════════════════════════════
# SECTION 2 — SHOWS
# ══════════════════════════════════════════════════════════════════
def render_shows(df: pd.DataFrame, masters: dict) -> None:
    st.markdown('<div class="section-title">📺 Shows</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No data yet. Add entries in the Episodes section.")
        return

    # ── Filters ──────────────────────────────────────────────────
    fcol1, fcol2, fcol3 = st.columns([2, 2, 3])
    with fcol1:
        lang_opts = sorted(df["Language"].dropna().unique().tolist())
        lang_filter = st.multiselect("Language", lang_opts, key="shows_lang")
    with fcol2:
        ct_opts = sorted(df["Content_Type"].dropna().unique().tolist())
        ct_filter = st.multiselect("Content Type", ct_opts, key="shows_ct")
    with fcol3:
        search = st.text_input("🔍 Search Show Name", key="shows_search", placeholder="Type to filter…")

    # ── Apply Filters ─────────────────────────────────────────────
    filtered = df.copy()
    if lang_filter:
        filtered = filtered[filtered["Language"].isin(lang_filter)]
    if ct_filter:
        filtered = filtered[filtered["Content_Type"].isin(ct_filter)]
    if search.strip():
        filtered = filtered[
            filtered["Show_Name"].str.contains(search.strip(), case=False, na=False)
        ]

    shows_table = build_shows_table(filtered)

    if shows_table.empty:
        st.warning("No shows match the current filters.")
        return

    st.markdown(
        f'<span class="result-badge">Showing {len(shows_table)} shows</span>',
        unsafe_allow_html=True,
    )
    st.dataframe(shows_table, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# SECTION 3 — EPISODES
# ══════════════════════════════════════════════════════════════════
def render_episodes(df: pd.DataFrame, masters: dict) -> None:
    st.markdown('<div class="section-title">🎬 Episodes</div>', unsafe_allow_html=True)

    # ── Filters Row 1 ─────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    show_opts = sorted(df["Show_Name"].dropna().unique().tolist()) if not df.empty else []
    ct_opts   = sorted(df["Content_Type"].dropna().unique().tolist()) if not df.empty else []
    subj_opts = sorted(df["Subject"].dropna().unique().tolist()) if not df.empty else []
    lang_opts = sorted(df["Language"].dropna().unique().tolist()) if not df.empty else []

    with fc1:
        show_filter = st.multiselect("Show Name", show_opts, key="ep_show")
    with fc2:
        ct_filter   = st.multiselect("Content Type", ct_opts, key="ep_ct")
    with fc3:
        subj_filter = st.multiselect("Subject", subj_opts, key="ep_subj")
    with fc4:
        lang_filter = st.multiselect("Language", lang_opts, key="ep_lang")

    # ── Filters Row 2 ─────────────────────────────────────────────
    dr_col, search_col = st.columns([2, 3])
    with dr_col:
        today = date.today()
        # Default: show ALL data from earliest date in the sheet
        earliest = df["Date"].dropna().min().date() if not df.empty else date(2019, 1, 1)
        date_range = st.date_input(
            "Date Range",
            value=(earliest, today),
            key="ep_date_range",
        )
    with search_col:
        text_search = st.text_input(
            "🔍 Search (Show / Episode Range / Subject)",
            key="ep_text",
            placeholder="Type to search…",
        )

    # ── Apply Filters ─────────────────────────────────────────────
    filtered = df.copy() if not df.empty else pd.DataFrame()

    if not filtered.empty:
        if show_filter:
            filtered = filtered[filtered["Show_Name"].isin(show_filter)]
        if ct_filter:
            filtered = filtered[filtered["Content_Type"].isin(ct_filter)]
        if subj_filter:
            filtered = filtered[filtered["Subject"].isin(subj_filter)]
        if lang_filter:
            filtered = filtered[filtered["Language"].isin(lang_filter)]

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            d_from = pd.Timestamp(date_range[0])
            d_to   = pd.Timestamp(date_range[1])
            filtered = filtered[
                (filtered["Date"] >= d_from) & (filtered["Date"] <= d_to)
            ]

        if text_search.strip():
            q = text_search.strip()
            mask = (
                filtered["Show_Name"].str.contains(q, case=False, na=False) |
                filtered["Episode_Range"].str.contains(q, case=False, na=False) |
                filtered["Subject"].str.contains(q, case=False, na=False)
            )
            filtered = filtered[mask]

    # ── Result badge ──────────────────────────────────────────────
    total_rows  = len(df) if not df.empty else 0
    shown_rows  = len(filtered) if not filtered.empty else 0
    st.markdown(
        f'<span class="result-badge">Showing {shown_rows} of {total_rows} records</span>',
        unsafe_allow_html=True,
    )

    # ── Display Table ─────────────────────────────────────────────
    if not filtered.empty:
        display = filtered.copy()
        display["Date"] = display["Date"].apply(format_date)
        display = display.rename(columns={
            "Sr_No": "Sr No", "Show_Name": "Show Name",
            "Content_Type": "Content Type", "Episode_Range": "Episode Range",
            "No_of_Episodes": "No. of Episodes",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

        # Export
        excel_bytes = df_to_excel_bytes(display)
        st.download_button(
            label="📥 Export to Excel",
            data=excel_bytes,
            file_name=f"episodes_export_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("No records match the current filters.")

    # ── Add New Entry ─────────────────────────────────────────────
    st.markdown("---")
    with st.expander("➕ Add New Entry", expanded=False):
        _render_add_entry_form(df, masters)


def _render_add_entry_form(df: pd.DataFrame, masters: dict) -> None:
    """Form inside Episodes section to add a new production log entry."""
    show_names    = masters.get("show_names", [])
    content_types = masters.get("content_types", [])
    subjects      = masters.get("subjects", [])
    languages     = masters.get("languages", [])

    # Fallback to free text if masters empty
    def _select_or_text(label: str, options: list, key: str):
        if options:
            return st.selectbox(label, options, key=key)
        else:
            return st.text_input(f"{label} (masters empty — type manually)", key=key)

    r1c1, r1c2 = st.columns(2)
    with r1c1:
        show_name = _select_or_text("Show Name", show_names, "add_show")
    with r1c2:
        content_type = _select_or_text("Content Type", content_types, "add_ct")

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        subject = _select_or_text("Subject", subjects, "add_subj")
    with r2c2:
        language = _select_or_text("Language", languages, "add_lang")

    r3c1, r3c2, r3c3, r3c4 = st.columns(4)
    with r3c1:
        ep_from = st.number_input("Episode From", min_value=1, value=1, step=1, key="add_from")
    with r3c2:
        ep_to = st.number_input("Episode To", min_value=1, value=1, step=1, key="add_to")
    with r3c3:
        ep_range_display = make_episode_range(int(ep_from), int(ep_to))
        st.text_input("Episode Range (auto)", value=ep_range_display, disabled=True, key="add_range_disp")
    with r3c4:
        no_of_eps = max(0, int(ep_to) - int(ep_from) + 1)
        st.text_input("No. of Episodes (auto)", value=str(no_of_eps), disabled=True, key="add_eps_disp")

    entry_date = st.date_input("Recording Date", value=date.today(), key="add_date")

    if st.button("✅ Submit Entry", type="primary", key="add_submit"):
        # Validation
        errors = []
        if int(ep_to) < int(ep_from):
            errors.append("Episode To must be ≥ Episode From.")
        if not str(show_name).strip():
            errors.append("Show Name is required.")
        if not str(content_type).strip():
            errors.append("Content Type is required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            sr_no = next_sr_no(df)
            row = {
                "Sr_No":         sr_no,
                "Show_Name":     show_name,
                "Content_Type":  content_type,
                "Subject":       subject,
                "Language":      language,
                "Episode_From":  int(ep_from),
                "Episode_To":    int(ep_to),
                "Episode_Range": make_episode_range(int(ep_from), int(ep_to)),
                "No_of_Episodes": no_of_eps,
                "Date":          entry_date.strftime("%d/%m/%Y"),
            }
            ok, err = append_entry(row)
            if ok:
                get_production_log.clear()
                st.session_state["last_refresh"] = datetime.now()
                st.toast("✅ Entry added successfully!", icon="🎬")
                st.rerun()
            else:
                st.error(f"Failed to save: {err}")


# ══════════════════════════════════════════════════════════════════
# SECTION 4 — SUBJECTS
# ══════════════════════════════════════════════════════════════════
def render_subjects(df: pd.DataFrame, masters: dict) -> None:
    st.markdown('<div class="section-title">📚 Subjects</div>', unsafe_allow_html=True)

    subjects_table = build_subjects_table(df)

    if subjects_table.empty:
        st.info("No subject data available yet.")
    else:
        st.markdown(
            f'<span class="result-badge">{len(subjects_table)} subjects found</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(subjects_table, use_container_width=True, hide_index=True)

        # Horizontal bar chart — top subjects
        chart_data = subjects_table
        fig = px.bar(
            chart_data,
            x="Total Episodes",
            y="Subject",
            orientation="h",
            title="Top Subjects by Total Episodes",
            color="Total Episodes",
            color_continuous_scale=["#C4B5FD", "#6C63FF", "#1A1A2E"],
            labels={"Total Episodes": "Episodes", "Subject": ""},
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(300, len(chart_data) * 32),
            margin=dict(l=0, r=20, t=40, b=10),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            title_font=dict(size=14, color="#0F0E2A"),
            font=dict(color="#0F0E2A"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Manage Subjects ───────────────────────────────────────────
    with st.expander("⚙️ Manage Subjects", expanded=False):
        current = sorted(df["Subject"].dropna().unique().tolist()) if not df.empty else []
        if current:
            st.markdown(f"**{len(current)} subjects currently in your data:**")
            cols = st.columns(3)
            for i, s in enumerate(current):
                cols[i % 3].markdown(f"• {s}")
        else:
            st.info("No subjects found in Sheet1 yet.")
        st.info("💡 New subjects appear automatically in dropdowns when you add an entry with a new Subject value.")


# ══════════════════════════════════════════════════════════════════
# SECTION 5 — CONTENT TYPES
# ══════════════════════════════════════════════════════════════════
def render_content_types(df: pd.DataFrame, masters: dict) -> None:
    st.markdown('<div class="section-title">🎭 Content Types</div>', unsafe_allow_html=True)

    ct_table = build_content_types_table(df)

    col_table, col_chart = st.columns([1, 1])

    with col_table:
        if ct_table.empty:
            st.info("No content type data available yet.")
        else:
            st.markdown(
                f'<span class="result-badge">{len(ct_table)} content types</span>',
                unsafe_allow_html=True,
            )
            st.dataframe(ct_table, use_container_width=True, hide_index=True)

    with col_chart:
        if not ct_table.empty:
            fig = px.pie(
                ct_table,
                names="Content Type",
                values="Total Episodes",
                hole=0.52,
                title="Episode Share by Content Type",
                color_discrete_sequence=["#6C63FF", "#A78BFA", "#C4B5FD",
                                         "#7C3AED", "#DDD6FE", "#4C1D95"],
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=380,
                margin=dict(l=0, r=0, t=40, b=10),
                title_font=dict(size=14, color="#0F0E2A"),
                font=dict(color="#0F0E2A"),
                legend=dict(orientation="h", y=-0.2),
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    # ── Manage Content Types ──────────────────────────────────────
    with st.expander("⚙️ Manage Content Types", expanded=False):
        current = sorted(df["Content_Type"].dropna().unique().tolist()) if not df.empty else []
        if current:
            st.markdown(f"**{len(current)} content types currently in your data:**")
            cols = st.columns(3)
            for i, c in enumerate(current):
                cols[i % 3].markdown(f"• {c}")
        else:
            st.info("No content types found in Sheet1 yet.")
        st.info("💡 New content types appear automatically in dropdowns when you add an entry with a new Content Type value.")


# ══════════════════════════════════════════════════════════════════
# SECTION 6 — PRODUCTION SHEET
# ══════════════════════════════════════════════════════════════════
PROD_DISPLAY_COLS = [
    "Sr No", "Date", "Show Name", "Content Type",
    "Subject", "Language", "Episode Range", "No. of Episodes"
]

COL_MAP = {
    "Sr No":           "Sr_No",
    "Date":            "Date",
    "Show Name":       "Show_Name",
    "Content Type":    "Content_Type",
    "Subject":         "Subject",
    "Language":        "Language",
    "Episode Range":   "Episode_Range",
    "No. of Episodes": "No_of_Episodes",
}


def render_production_sheet(df: pd.DataFrame, masters: dict) -> None:
    st.markdown('<div class="section-title">📅 Production Sheet</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No production data yet.")
        return

    # ── Compact Filter Row ────────────────────────────────────────
    fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 2, 2])
    today    = date.today()
    # Default: show ALL data from earliest date in the sheet
    earliest = df["Date"].dropna().min().date() if not df.empty else date(2019, 1, 1)

    with fc1:
        date_range = st.date_input("Date Range", value=(earliest, today), key="ps_date")
    with fc2:
        show_filter = st.multiselect(
            "Show", sorted(df["Show_Name"].dropna().unique()), key="ps_show"
        )
    with fc3:
        ct_filter = st.multiselect(
            "Content Type", sorted(df["Content_Type"].dropna().unique()), key="ps_ct"
        )
    with fc4:
        lang_filter = st.multiselect(
            "Language", sorted(df["Language"].dropna().unique()), key="ps_lang"
        )
    with fc5:
        subj_filter = st.multiselect(
            "Subject", sorted(df["Subject"].dropna().unique()), key="ps_subj"
        )

    # ── Apply Filters ─────────────────────────────────────────────
    filtered = df.copy()
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        filtered = filtered[
            (filtered["Date"] >= pd.Timestamp(date_range[0])) &
            (filtered["Date"] <= pd.Timestamp(date_range[1]))
        ]
    if show_filter:
        filtered = filtered[filtered["Show_Name"].isin(show_filter)]
    if ct_filter:
        filtered = filtered[filtered["Content_Type"].isin(ct_filter)]
    if lang_filter:
        filtered = filtered[filtered["Language"].isin(lang_filter)]
    if subj_filter:
        filtered = filtered[filtered["Subject"].isin(subj_filter)]

    filtered = filtered.sort_values("Date", ascending=True).reset_index(drop=True)

    if filtered.empty:
        st.warning("No records match the selected filters.")
        return

    total_shown = len(filtered)
    grand_total_eps = int(filtered["No_of_Episodes"].sum())

    # Export button (top-right style via columns)
    badge_col, _, export_col = st.columns([3, 5, 2])
    with badge_col:
        st.markdown(
            f'<span class="result-badge">Showing {total_shown} records</span>',
            unsafe_allow_html=True,
        )
    with export_col:
        grouped_for_export = group_by_month(filtered)
        excel_data = production_sheet_to_excel(grouped_for_export, PROD_DISPLAY_COLS)
        st.download_button(
            label="📥 Export Production Sheet",
            data=excel_data,
            file_name=f"production_sheet_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="ps_export",
        )

    # ── Grouped Month Display ─────────────────────────────────────
    grouped = group_by_month(filtered)

    for month_label, month_df in grouped.items():
        month_eps = int(month_df["No_of_Episodes"].sum())
        month_count = len(month_df)

        # Month header
        st.markdown(
            f'<div class="month-header">📅 {month_label} &nbsp;&nbsp;'
            f'<span class="ep-count">{month_eps} episodes · {month_count} batches</span></div>',
            unsafe_allow_html=True,
        )

        # Build display dataframe
        display = month_df.copy()
        display["Date"] = display["Date"].apply(format_date)
        display = display.rename(columns={v: k for k, v in COL_MAP.items()})

        # Keep only the display columns that exist
        cols_present = [c for c in PROD_DISPLAY_COLS if c in display.columns]
        display = display[cols_present]

        st.dataframe(display, use_container_width=True, hide_index=True)

        # Monthly subtotal row (styled HTML)
        st.markdown(
            f'<div class="subtotal-row">'
            f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
            f'Monthly Total &nbsp;→&nbsp; <strong>{month_eps}</strong> episodes '
            f'across <strong>{month_count}</strong> batches</div>',
            unsafe_allow_html=True,
        )

    # Grand Total
    st.markdown(
        f'<div class="grand-total-row" style="margin-top:16px; padding:10px 16px;">'
        f'🎬 &nbsp; GRAND TOTAL &nbsp;→&nbsp; <strong>{grand_total_eps}</strong> total episodes'
        f' &nbsp;|&nbsp; <strong>{total_shown}</strong> total batches</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    render_sidebar()
    render_nav()

    df, _ = load_data()
    masters = load_masters()

    active = st.session_state["active_section"]

    if active == "dashboard":
        render_dashboard(df)
    elif active == "shows":
        render_shows(df, masters)
    elif active == "episodes":
        render_episodes(df, masters)
    elif active == "subjects":
        render_subjects(df, masters)
    elif active == "content_types":
        render_content_types(df, masters)
    elif active == "production_sheet":
        render_production_sheet(df, masters)
    else:
        render_dashboard(df)


if __name__ == "__main__":
    main()
