# 🧠 Psychiatric Disorders SRA Dashboard

An interactive, web-based metadata exploration and pipeline-tracking dashboard for RNA-seq studies related to Psychiatric Disorders (Schizophrenia, Bipolar Disorder, Major Depressive Disorder, MDD).

Built for the AbbVie Bioinformatics team to monitor pipeline status, explore study metadata, track flagged studies, and interrogate a large-scale all-studies dataset — all live from Google Sheets.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔐 **Secure Auth** | `streamlit-authenticator` login with bcrypt-hashed credentials in `users.yaml` |
| 🔄 **Live Google Sheets Sync** | 3-tier fallback loader: Google Sheets API → SQLite cache → local Excel/CSV |
| 📊 **Overview & Analytics** | Live pipeline status, disease distributions, Big Data landscape charts |
| 🔍 **Study Explorer** | Filter 82+ studies by disease, sample size, or keyword; view sample sheets, slides, metadata |
| ⚠️ **Issue Tracker** | Flags and severity tracking for studies with known processing problems |
| 📂 **Big Data Explorer** | Browse and filter 5,249+ samples from the all-studies sheet with export |
| 🎛️ **Refresh Live Data** | One-click sidebar button clears cache and re-fetches all Google Sheets |

---

## 🏗️ Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    External Data Sources                     │
│                                                             │
│  Google Sheets API (gspread + service account)              │
│  ├── Summary tracker   (gid=967699804)  → Pipeline status   │
│  ├── Study info        (gid=1289743746) → Publication links  │
│  ├── Issue_tracker     (gid=617382454)  → Flagged studies   │
│  └── Big_data          (gid=411528296)  → 5,249 samples     │
└────────────────────┬────────────────────────────────────────┘
                     │ Tier 1: gspread fetch
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite Cache Layer                         │
│              sra_metadata.db                                │
│  ┌──────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────┐  │
│  │ studies  │ │sample_sheet│ │sample_metada│ │issue_stud│  │
│  │  (95)    │ │   s (4108) │ │     ta      │ │  ies(30) │  │
│  └──────────┘ └────────────┘ └─────────────┘ └──────────┘  │
│              + cache_<md5> tables per sheet URL             │
└────────────────────┬────────────────────────────────────────┘
                     │ Tier 2: SQLite / Tier 3: Local Excel
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                     │
│                                                             │
│  📊 Overview & Analytics                                    │
│     ├── Live total datasets (from Summary tracker)          │
│     ├── Study Status / Analyst breakdown charts             │
│     └── Big Data: tissues, sex, library strategy, read len  │
│                                                             │
│  🔍 Study Explorer                                          │
│     ├── Filters: disease, database, flags, sample size      │
│     └── Tabs: Sample Sheet · Sample Info · Slides ·         │
│               Full Metadata · Execution Stats · Analysis    │
│                                                             │
│  ⚠️  Issue Studies Tracker                                  │
│     └── Severity-coded cards + SQLite-synced table          │
│                                                             │
│  📂 All Studies (Big Data)                                  │
│     └── 5,249 rows, filterable, exportable as CSV           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| UI Framework | [Streamlit](https://streamlit.io/) ≥ 1.32 |
| Visualizations | [Plotly Express](https://plotly.com/python/plotly-express/) |
| Data Processing | Pandas ≥ 2.0, NumPy |
| Database | SQLite3 (`sra_metadata.db`) |
| Google Sheets | `gspread` + `google-auth` (service account) |
| Authentication | `streamlit-authenticator` ≥ 0.4.2, `bcrypt` |
| Excel fallback | `openpyxl` |
| Environment | [Pixi](https://prefix.dev/) / `pip` + `requirements.txt` |

---

## 🚀 Setup & Installation

### Option 1: Pixi (Recommended for local dev)
```bash
git clone https://github.com/Surajsharma95/Psychiatric-Disorders-SRA-Dashboard.git
cd Psychiatric-Disorders-SRA-Dashboard
pixi run streamlit run app.py
```

### Option 2: pip
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Streamlit Community Cloud Deployment

1. Push repo to GitHub (`main` branch).
2. Connect repo in [share.streamlit.io](https://share.streamlit.io).
3. Set **Secrets** in the Streamlit Cloud dashboard (paste the contents of `.streamlit/secrets.toml`):

```toml
[connections.gsheets]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "sra-dashboard-bot@your-project.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

> **Important:** Never commit `.streamlit/secrets.toml` — it is already in `.gitignore`.

---

## 📂 Project Structure

```
Psychiatric-Disorders-SRA-Dashboard/
├── app.py                        # Main Streamlit app (all 4 views)
├── sra_db.py                     # DB initialiser & seeder (run once locally)
├── sra_metadata.db               # SQLite cache (auto-generated, git-ignored)
├── googlesheetlink.csv           # Maps sheet keys → Google Sheet URLs + worksheets
├── studies_82.csv                # Master study list (seed data)
├── users.yaml                    # Auth credentials (hashed passwords)
├── requirements.txt              # pip dependencies for cloud deployment
├── pixi.toml                     # Pixi environment spec (local dev)
├── Summary-tracker.xlsx          # Local Excel fallback for Google Sheets data
├── all_studies_fallback.csv      # Local CSV fallback for Big Data sheet
├── .streamlit/
│   ├── config.toml               # Streamlit theme & server config
│   └── secrets.toml              # GCP service account keys (git-ignored)
├── local_scripts/
│   ├── build_master_metadata.py  # Compile local TSVs → SQLite sample_metadata
│   ├── fetch_srp_metadata.py     # Fetch NCBI E-Utils XML metadata
│   └── parse_local_metadata.py   # Parse a single local TSV
└── download_sra_metadata.py      # Download SRA metadata via pysradb CLI
```

---

## 🔄 Google Sheets Configuration (`googlesheetlink.csv`)

The app reads this CSV to know which Google Sheet tab to fetch for each data source:

| sheet_name | worksheet_name | purpose |
|---|---|---|
| `summary_tracker` | `Summary tracker` | Pipeline status, analyst assignment, slides links |
| `pipeline_info` | `Study info` | Publication links, ARTEMIS run IDs, covariates |
| `issue_studies` | `Issue_tracker` | Flagged studies with severity and comments |
| `all_studies_bigdata` | `Big_data` | 5,249 samples with tissue, cell type, read length |

To add a new sheet: add a row to `googlesheetlink.csv` and use `load_tracker_csv(url, worksheet, fallback)` in `app.py`.

---

## 🗄️ Database Seeding (Local Only)

The SQLite database is **not committed** to Git. Seed it locally before running:

```bash
python sra_db.py
```

This will:
- Create all tables (`studies`, `sample_sheets`, `sample_metadata`, `issue_studies`)
- Ingest 95 studies from `studies_82.csv`
- Scan `../../samplesheet/` for sample sheet TSVs (4,108 samples across 80 sheets)
- Seed 30 issue records from the local Excel fallback

---

## 👥 User Management

Credentials are stored in `users.yaml` as bcrypt hashes. To add a new user:

```bash
python generate_hashes.py
```

Then paste the generated hash into `users.yaml`:

```yaml
credentials:
  usernames:
    newuser:
      name: New User
      email: newuser@abbvie.com
      password: "$2b$12$<generated_hash>"
```

---

## 📝 Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2024 | Initial dashboard with SQLite + local Excel |
| 1.5 | 2025-05 | Google Sheets 3-tier fallback, Refresh button |
| 1.6 | 2025-06 | Big Data explorer (5,249 samples), Issue tracker sync |
| 1.7 | 2026-06 | Enhanced Overview with live pipeline & Big Data charts, dynamic summary banner, slides link from Summary tracker |
