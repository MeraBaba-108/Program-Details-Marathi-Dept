"""
utils/helpers.py
Pure data-transformation helpers — no Streamlit dependencies.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from collections import OrderedDict

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


# ── Date helpers ────────────────────────────────────────────────

def format_date(d) -> str:
    """Return DD/MM/YYYY string, or '' if not parseable."""
    if pd.isna(d) or d is None:
        return ""
    if isinstance(d, (datetime, date)):
        return d.strftime("%d/%m/%Y")
    try:
        return pd.to_datetime(d, dayfirst=True).strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def month_year_label(d) -> str:
    """Return 'April 2026' style label from a date-like value."""
    if pd.isna(d) or d is None:
        return "Unknown"
    try:
        dt = pd.to_datetime(d)
        return dt.strftime("%B %Y")
    except Exception:
        return "Unknown"


def episodes_this_month(df: pd.DataFrame) -> int:
    """Sum No_of_Episodes where Date is current month/year."""
    if df.empty or "Date" not in df.columns:
        return 0
    now = datetime.now()
    mask = (
        df["Date"].dt.month == now.month
    ) & (
        df["Date"].dt.year == now.year
    )
    return int(df.loc[mask, "No_of_Episodes"].sum())


# ── Episode helpers ──────────────────────────────────────────────

def make_episode_range(ep_from: int, ep_to: int) -> str:
    """Build '20551-20558' style string."""
    return f"{ep_from}-{ep_to}"


def next_sr_no(df: pd.DataFrame) -> int:
    """Return max(Sr_No) + 1, or 1 if empty."""
    if df.empty or "Sr_No" not in df.columns:
        return 1
    try:
        return int(df["Sr_No"].max()) + 1
    except Exception:
        return 1


# ── Month grouping ───────────────────────────────────────────────

def group_by_month(df: pd.DataFrame) -> OrderedDict[str, pd.DataFrame]:
    """
    Split df into ordered dict keyed by 'April 2026' labels.
    Sorted chronologically (ascending).
    """
    if df.empty or "Date" not in df.columns:
        return OrderedDict()

    df = df.copy()
    df["_month_label"] = df["Date"].apply(month_year_label)
    df["_sort_key"] = pd.to_datetime(df["Date"], errors="coerce").dt.to_period("M")

    groups = OrderedDict()
    sorted_df = df.sort_values("_sort_key")

    for label in sorted_df["_month_label"].unique():
        groups[label] = sorted_df[sorted_df["_month_label"] == label].drop(
            columns=["_month_label", "_sort_key"]
        )

    return groups


# ── Aggregation helpers ──────────────────────────────────────────

def build_shows_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns aggregated show summary:
    Show Name | Language | Content Types Used | Subjects | Total Batches | Total Episodes | Last Recorded
    """
    if df.empty:
        return pd.DataFrame()

    # Use No_of_Episodes for batch count (count of non-null rows) — avoids Sr_No dependency
    count_col = "No_of_Episodes" if "No_of_Episodes" in df.columns else df.columns[0]

    agg_kwargs = dict(
        Language=("Language", lambda x: ", ".join(sorted(x.dropna().astype(str).unique()))) if "Language" in df.columns else None,
        Content_Types_Used=("Content_Type", lambda x: ", ".join(sorted(x.dropna().astype(str).unique()))) if "Content_Type" in df.columns else None,
        Subjects=("Subject", lambda x: ", ".join(sorted(x.dropna().astype(str).unique()))) if "Subject" in df.columns else None,
        Total_Batches=(count_col, "count"),
        Total_Episodes=("No_of_Episodes", "sum") if "No_of_Episodes" in df.columns else None,
        Last_Recorded=("Date", "max") if "Date" in df.columns else None,
    )
    # Drop any None entries (missing optional columns)
    agg_kwargs = {k: v for k, v in agg_kwargs.items() if v is not None}

    agg = (
        df.groupby("Show_Name")
        .agg(**agg_kwargs)
        .reset_index()
        .rename(columns={
            "Show_Name": "Show Name",
            "Content_Types_Used": "Content Types Used",
            "Total_Batches": "Total Batches",
            "Total_Episodes": "Total Episodes",
            "Last_Recorded": "Last Recorded",
        })
    )
    if "Last Recorded" in agg.columns:
        agg["Last Recorded"] = agg["Last Recorded"].apply(format_date)
    sort_col = "Total Episodes" if "Total Episodes" in agg.columns else "Total Batches"
    agg = agg.sort_values(sort_col, ascending=False).reset_index(drop=True)
    return agg


def build_subjects_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns: Subject | Shows Using It | Total Batches | Total Episodes
    """
    if df.empty or "Subject" not in df.columns:
        return pd.DataFrame()

    # Use No_of_Episodes for batch count — avoids Sr_No dependency
    count_col = "No_of_Episodes" if "No_of_Episodes" in df.columns else df.columns[0]

    shows_per_subject = (
        df.groupby("Subject")["Show_Name"]
        .nunique()
        .rename("Shows Using It")
    )
    batches  = df.groupby("Subject")[count_col].count().rename("Total Batches")
    episodes = df.groupby("Subject")["No_of_Episodes"].sum().rename("Total Episodes") if "No_of_Episodes" in df.columns else pd.Series(dtype=int, name="Total Episodes")

    result = pd.concat([shows_per_subject, batches, episodes], axis=1).reset_index()
    result = result.rename(columns={"Subject": "Subject"})
    result = result.sort_values("Total Episodes", ascending=False).reset_index(drop=True)
    return result


def build_content_types_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns: Content Type | Total Batches | Total Episodes | % Share
    """
    if df.empty or "Content_Type" not in df.columns:
        return pd.DataFrame()

    # Use No_of_Episodes for batch count — avoids Sr_No dependency
    count_col = "No_of_Episodes" if "No_of_Episodes" in df.columns else df.columns[0]

    batches  = df.groupby("Content_Type")[count_col].count().rename("Total Batches")
    episodes = df.groupby("Content_Type")["No_of_Episodes"].sum().rename("Total Episodes") if "No_of_Episodes" in df.columns else pd.Series(dtype=int, name="Total Episodes")

    result = pd.concat([batches, episodes], axis=1).reset_index()
    result = result.rename(columns={"Content_Type": "Content Type"})
    total = result["Total Episodes"].sum() if "Total Episodes" in result.columns else 1
    result["% Share"] = (
        (result["Total Episodes"] / total * 100).round(1).astype(str) + "%"
        if total > 0 else "0%"
    )
    result = result.sort_values("Total Episodes", ascending=False).reset_index(drop=True)
    return result


# ── Excel export helpers ─────────────────────────────────────────

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Simple DataFrame → .xlsx bytes for st.download_button."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Export")
    return buf.getvalue()


def production_sheet_to_excel(
    grouped: "OrderedDict[str, pd.DataFrame]",
    display_cols: list[str],
) -> bytes:
    """
    Builds a formatted Excel file with:
    - Month group headers (purple)
    - Monthly subtotal rows (light purple, bold)
    - Grand total row (dark purple, white bold)
    """
    buf = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Production Sheet"

    PURPLE_HEADER = PatternFill("solid", fgColor="6C63FF")
    PURPLE_MONTH  = PatternFill("solid", fgColor="EEF2FF")
    PURPLE_SUB    = PatternFill("solid", fgColor="DDD6FE")
    PURPLE_GRAND  = PatternFill("solid", fgColor="1A1A2E")
    WHITE_FONT    = Font(color="FFFFFF", bold=True)
    BOLD_FONT     = Font(bold=True)
    DARK_FONT     = Font(color="1A1A2E", bold=True)
    CENTER        = Alignment(horizontal="center")

    thin_side = Side(style="thin", color="C4B5FD")
    thin_border = Border(top=thin_side, bottom=thin_side)

    # Write column headers
    header_row = display_cols
    ws.append(header_row)
    for cell in ws[1]:
        cell.font = WHITE_FONT
        cell.fill = PURPLE_HEADER
        cell.alignment = CENTER

    grand_total_eps = 0

    for month_label, sub_df in grouped.items():
        # Month header row (merged label)
        ws.append([""] * len(display_cols))
        row_idx = ws.max_row
        ws.cell(row=row_idx, column=1, value=f"📅  {month_label}")
        ws.cell(row=row_idx, column=1).font = BOLD_FONT
        ws.cell(row=row_idx, column=1).fill = PURPLE_MONTH
        ws.merge_cells(start_row=row_idx, start_column=1,
                       end_row=row_idx, end_column=len(display_cols))

        month_eps = 0
        for _, row in sub_df.iterrows():
            data_row = []
            for col in display_cols:
                # Map display col → DataFrame col
                col_map = {
                    "Sr No": "Sr_No",
                    "Date": "Date",
                    "Show Name": "Show_Name",
                    "Content Type": "Content_Type",
                    "Subject": "Subject",
                    "Language": "Language",
                    "Episode Range": "Episode_Range",
                    "No. of Episodes": "No_of_Episodes",
                }
                df_col = col_map.get(col, col)
                val = row.get(df_col, "")
                if col == "Date" and not pd.isna(val):
                    val = format_date(val)
                data_row.append(val)
            ws.append(data_row)
            month_eps += int(row.get("No_of_Episodes", 0))

        grand_total_eps += month_eps

        # Monthly subtotal row
        sub_row = [""] * len(display_cols)
        sub_row[-2] = "Monthly Total"
        sub_row[-1] = month_eps
        ws.append(sub_row)
        sub_row_idx = ws.max_row
        for c in range(1, len(display_cols) + 1):
            ws.cell(row=sub_row_idx, column=c).font = DARK_FONT
            ws.cell(row=sub_row_idx, column=c).fill = PURPLE_SUB
            ws.cell(row=sub_row_idx, column=c).border = thin_border

    # Grand total row
    gt_row = [""] * len(display_cols)
    gt_row[-2] = "GRAND TOTAL"
    gt_row[-1] = grand_total_eps
    ws.append(gt_row)
    gt_row_idx = ws.max_row
    for c in range(1, len(display_cols) + 1):
        ws.cell(row=gt_row_idx, column=c).font = WHITE_FONT
        ws.cell(row=gt_row_idx, column=c).fill = PURPLE_GRAND

    # Column widths
    col_widths = [8, 14, 28, 20, 22, 14, 18, 18]
    for i, width in enumerate(col_widths[:len(display_cols)], 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width

    wb.save(buf)
    return buf.getvalue()
