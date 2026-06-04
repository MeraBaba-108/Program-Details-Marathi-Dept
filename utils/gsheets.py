"""
utils/gsheets.py
Google Sheets integration — reads from and writes to Sheet1 only.

Sheet1 column mapping:
  chatg          → Sr_No
  Program Title  → Show_Name
  Content Type   → Content_Type
  Subject        → Subject
  Language       → Language
  Log No.        → Episode_Range   (e.g. "20551-20558")
  No. Of Eps     → No_of_Episodes
  Shooting Date  → Date
"""

from __future__ import annotations

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Optional

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TAB_LOG = "Sheet1"

# Sheet1 header → internal name used throughout the app
# These match the EXACT column headers in your Google Sheet1
SHEET_TO_INTERNAL = {
    "Sr. No":        "Sr_No",        # first column (serial number)
    "Sr_No":         "Sr_No",        # fallback in case header changes
    "chatg":         "Sr_No",        # legacy fallback
    "Program Title": "Show_Name",
    "Content Type":  "Content_Type",
    "Subject":       "Subject",
    "Language":      "Language",
    "Log No.":       "Episode_Range",
    "No. Of Eps":    "No_of_Episodes",
    "Shooting Date": "Date",
}

# Internal name → Sheet1 header (used when writing new rows)
INTERNAL_TO_SHEET = {v: k for k, v in SHEET_TO_INTERNAL.items()}


# ── Cached auth client ─────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_client() -> tuple[Optional[gspread.Client], str]:
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES
        )
        return gspread.authorize(creds), ""
    except Exception as e:
        return None, str(e)


def _get_spreadsheet() -> tuple[Optional[gspread.Spreadsheet], str]:
    client, err = _get_client()
    if err:
        return None, f"Auth error: {err}"
    try:
        return client.open_by_key(st.secrets["SHEET_ID"]), ""
    except Exception as e:
        return None, f"Cannot open sheet: {e}"


# ── Read production log ────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def get_production_log() -> tuple[pd.DataFrame, str]:
    """
    Reads Sheet1 → DataFrame with internal column names.
    Cache TTL = 60 s — any direct edits in the sheet appear within 1 minute.
    """
    spreadsheet, err = _get_spreadsheet()
    if err:
        return pd.DataFrame(), err

    try:
        ws = spreadsheet.worksheet(TAB_LOG)
        all_values = ws.get_all_values()

        if len(all_values) < 2:
            return pd.DataFrame(), ""

        raw_headers = all_values[0]
        data_rows   = all_values[1:]

        df = pd.DataFrame(data_rows, columns=raw_headers)

        # Drop fully empty rows
        df = df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)].copy()

        # Rename to internal names; unknown columns are kept as-is
        df = df.rename(columns=SHEET_TO_INTERNAL)

        # Numeric coercions
        for col in ("Sr_No", "No_of_Episodes"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Date parsing — your sheet uses DD/MM/YYYY
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

        # Skip summary/totals rows — these are never real production entries:
        #   1. Show_Name is literally "Total" / "TOTAL" / "total"
        #   2. Show_Name is blank AND No_of_Episodes >= 100 (old-style total row)
        if "Show_Name" in df.columns:
            show_clean = df["Show_Name"].astype(str).str.strip().str.lower()
            is_named_total  = show_clean.isin(["total", "totals", "grand total"])
            is_blank        = show_clean.eq("")
            is_large        = df["No_of_Episodes"] >= 100 if "No_of_Episodes" in df.columns else False
            is_blank_total  = is_blank & is_large
            df = df[~(is_named_total | is_blank_total)].copy()

            # Fill any remaining blank Show_Names with a placeholder
            df["Show_Name"] = df["Show_Name"].astype(str).str.strip().replace("", "— Unknown —")

        df = df.reset_index(drop=True)
        return df, ""

    except Exception as e:
        return pd.DataFrame(), f"Read error: {e}"


# ── Derive master lists from Sheet1 live data ──────────────────
@st.cache_data(ttl=60, show_spinner=False)
def get_masters() -> tuple[dict[str, list[str]], str]:
    """
    Derives dropdown lists by reading unique values from Sheet1.
    No separate Masters tab required.
    """
    df, err = get_production_log()
    if err or df.empty:
        return {"show_names": [], "content_types": [], "subjects": [], "languages": []}, err

    def _unique(col: str) -> list[str]:
        if col not in df.columns:
            return []
        return sorted(df[col].dropna().astype(str).str.strip()
                      .replace("", pd.NA).dropna().unique().tolist())

    return {
        "show_names":    _unique("Show_Name"),
        "content_types": _unique("Content_Type"),
        "subjects":      _unique("Subject"),
        "languages":     _unique("Language"),
    }, ""


# ── Append a new row to Sheet1 ─────────────────────────────────
def append_entry(row_dict: dict) -> tuple[bool, str]:
    """
    Appends one row to Sheet1.
    row_dict uses internal keys; converted back to actual Sheet1 headers.
    """
    spreadsheet, err = _get_spreadsheet()
    if err:
        return False, err

    try:
        ws = spreadsheet.worksheet(TAB_LOG)
        sheet_headers = ws.row_values(1)   # actual Sheet1 header row

        row = []
        for h in sheet_headers:
            internal_key = SHEET_TO_INTERNAL.get(h, h)
            row.append(str(row_dict.get(internal_key, "")))

        ws.append_row(row, value_input_option="USER_ENTERED")

        # Bust caches immediately
        get_production_log.clear()
        get_masters.clear()
        return True, ""

    except Exception as e:
        return False, f"Append error: {e}"
