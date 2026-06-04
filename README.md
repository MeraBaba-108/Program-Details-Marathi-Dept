# Marathi Content Production Dashboard

A **Streamlit-based production tracking dashboard** for Marathi content, connected live to Google Sheets. Built for the Marathi Department to track programs, episodes, subjects, and content types — with charts, filters, and Excel export.

---

## Features

- 📊 **Live Dashboard** — KPI cards, episode trends, content type breakdown
- 📺 **Shows Tab** — Aggregated view of all shows with total episodes and last recorded date
- 🎬 **Episodes Tab** — Full filterable log with date range, show, subject, and text search
- 📚 **Subjects Tab** — Subject-wise episode distribution with bar chart
- 🎭 **Content Types Tab** — Donut chart + table of content type breakdown
- 📅 **Production Sheet** — Month-wise grouped view with subtotals and Excel export
- ➕ **Add New Entry** — Form to append new entries directly to Google Sheet
- 🔄 **Auto Refresh** — Data refreshes from Google Sheets every 60 seconds automatically

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io) |
| Data Source | Google Sheets via [gspread](https://gspread.readthedocs.io) |
| Auth | GCP Service Account (JSON key) |
| Charts | [Plotly Express](https://plotly.com/python/plotly-express/) |
| Excel Export | [openpyxl](https://openpyxl.readthedocs.io) |
| Language | Python 3.12 |

---

## Project Structure

```
Program Details Marathi Dept/
├── app.py                   ← Single-page Streamlit app (all sections)
├── utils/
│   ├── gsheets.py           ← Google Sheets integration (read/write)
│   ├── helpers.py           ← Data aggregation & Excel export helpers
│   └── style.py             ← CSS styling
├── .streamlit/
│   └── secrets.toml         ← GCP credentials (NOT committed — add manually)
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/MeraBaba-108/marathi-production-dashboard.git
cd marathi-production-dashboard
```

### 2. Create a Virtual Environment & Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Configure Google Sheets Access

Create `.streamlit/secrets.toml` with your GCP service account credentials:

```toml
SHEET_ID = "your_google_sheet_id_here"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

> ⚠️ **Never commit `secrets.toml` to GitHub.** It is excluded via `.gitignore`.

### 4. Share Your Google Sheet

Share your Google Sheet with the **service account email** (e.g. `your-service-account@project.iam.gserviceaccount.com`) giving it **Editor** access.

### 5. Google Sheet Format (Sheet1)

Your `Sheet1` must have these exact column headers in row 1:

| Sr. No | Program Title | Content Type | Subject | Language | Log No. | No. Of Eps | Shooting Date |
|---|---|---|---|---|---|---|---|
| 1 | Aarogyam Dhansampada | Single | Health | Marathi | 20551-20558 | 8 | 13/04/2026 |

> ℹ️ A **Total row** at the bottom (where Program Title = "Total") is automatically ignored by the app.

### 6. Run the App

```bash
.venv\Scripts\streamlit.exe run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## GCP Setup (One-Time)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **APIs & Services → Credentials → Create Credentials → Service Account**
5. Download the JSON key
6. Copy values from the JSON into `.streamlit/secrets.toml`

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Could not reach Google Sheets` | Check `secrets.toml`, ensure sheet is shared with service account email |
| `gspread.exceptions.APIError` | Enable Google Sheets API + Google Drive API in GCP |
| Dashboard shows wrong episode count | Check if your sheet has a "Total" row at the bottom — the app skips it automatically |
| Empty dashboard | Ensure `Sheet1` tab exists with correct column headers |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |

---

## License

MIT License — free to use and modify.
