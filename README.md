# 🧠 Psychiatric Disorders SRA Dashboard

An interactive, web-based metadata exploration and pipeline-tracking dashboard for RNA-seq studies related to Psychiatric Disorders — Schizophrenia, Bipolar Disorder, MDD, and Depression.

Built for the **AbbVie Bioinformatics team** to monitor pipeline status, explore study metadata, track flagged studies, and interrogate a large-scale all-studies dataset — all synced live from Google Sheets.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Secure Auth** | Login with bcrypt-hashed credentials via `users.yaml` |
| 🔄 **Live Google Sheets Sync** | 3-tier fallback: Google Sheets API → SQLite cache → local Excel/CSV |
| 📊 **Overview & Analytics** | Live pipeline status, Big Data landscape, disease distribution charts |
| 🔍 **Study Explorer** | Filter 82+ studies; view sample sheets, slides links, and full metadata |
| ⚠️ **Issue Tracker** | Severity-coded flagged studies synced from Google Sheets |
| 📂 **Big Data Explorer** | Browse and filter 5,249+ samples with one-click CSV export |
| 🔃 **Refresh Live Data** | Sidebar button clears cache and re-fetches all Google Sheets instantly |

---

## 🚀 Quick Start — Run with Docker (Recommended)

> **No Python or pip setup needed.** Docker handles everything.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) installed
- A `secrets.toml` file with Google Sheets service account credentials *(get this from your team admin)*

### Step 1 — Clone the repository
```bash
git clone https://github.com/surajkumarsharma-bxEn/Psychiatric-Disorders-SRA-Dashboard.git
cd Psychiatric-Disorders-SRA-Dashboard
```

### Step 2 — Add your secrets file
Create `.streamlit/secrets.toml` with the Google Sheets credentials provided by your team admin:

```bash
mkdir -p .streamlit
```

```toml
# .streamlit/secrets.toml
[connections.gsheets]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "sra-dashboard-bot@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
token_uri = "https://oauth2.googleapis.com/token"
```

### Step 3 — Build and run
```bash
docker compose up --build
```

Open **http://localhost:8080** in your browser. ✅

> **Login credentials** — contact your team admin for the username and password.

### Stop the container
```bash
docker compose down
```

---

## 🐳 Docker — Manual Commands (without docker compose)

```bash
# Build the image
docker build -t sra-dashboard .

# Run the container
docker run -p 8080:8080 \
  -v ./. streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro \
  sra-dashboard

# Open http://localhost:8080
```

---

## 💻 Local Development (Without Docker)

### Option A — Using Pixi
```bash
pixi run streamlit run app.py
```

### Option B — Using pip
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Streamlit Community Cloud Deployment

1. Push repo to GitHub (`prod` branch).
2. Connect at [share.streamlit.io](https://share.streamlit.io).
3. Set **Secrets** in the Streamlit Cloud dashboard (paste contents of `.streamlit/secrets.toml`).
4. Any push to `prod` triggers an automatic redeployment.

---

## 📂 Project Structure

```
Psychiatric-Disorders-SRA-Dashboard/
├── app.py                        # Main Streamlit application (all 4 views)
├── sra_db.py                     # SQLite DB initialiser & seeder
├── googlesheetlink.csv           # Maps sheet keys → Google Sheet URLs & worksheets
├── users.yaml                    # Auth credentials (bcrypt hashed)
├── requirements.txt              # pip dependencies
├── Dockerfile                    # Production multi-stage Docker build
├── docker-compose.yml            # One-command Docker run with secrets mount
├── .dockerignore                 # Excludes secrets, DB, cache from Docker build
├── pixi.toml                     # Pixi env spec for local development
├── Summary-tracker.xlsx          # Local Excel fallback for Google Sheets data
├── all_studies_fallback.csv      # Local CSV fallback for Big Data sheet
├── .streamlit/
│   ├── config.toml               # Streamlit theme & server config
│   └── secrets.toml              # GCP service account keys ← NOT in git
└── local_scripts/
    ├── build_master_metadata.py  # Compile local TSVs → SQLite sample_metadata
    ├── fetch_srp_metadata.py     # Fetch NCBI E-Utils XML metadata
    └── parse_local_metadata.py   # Parse a single local metadata TSV
```

---

## 🔄 Google Sheets Configuration

Controlled by `googlesheetlink.csv` — edit this to point to different sheets:

| sheet_name | worksheet_name | Purpose |
|---|---|---|
| `summary_tracker` | `Summary tracker` | Pipeline status, analyst info, slides links |
| `pipeline_info` | `Study info` | Publication links, ARTEMIS run IDs |
| `issue_studies` | `Issue_tracker` | Flagged studies with severity & comments |
| `all_studies_bigdata` | `Big_data` | 5,249 samples with tissue, cell type, read length |

---

## 🗄️ Database Seeding (Local Only)

The SQLite DB is auto-generated and **not committed** to Git. Seed it locally once:

```bash
python sra_db.py
```

This creates `sra_metadata.db` with studies, sample sheets, and issue records.

---

## 👥 Adding New Users

```bash
python generate_hashes.py   # generates a bcrypt hash for a new password
```

Add the hash to `users.yaml`:
```yaml
credentials:
  usernames:
    newuser:
      name: New User
      email: newuser@abbvie.com
      password: "$2b$12$<hash_from_generate_hashes.py>"
```

---

## 📦 Do I Need Docker Hub?

**No.** The `Dockerfile` is in this repo — anyone with Docker can build the image themselves using the steps above. Docker Hub is only needed if you want to distribute a pre-built image without requiring others to build it.

---

## 📝 Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2024 | Initial dashboard with SQLite + local Excel |
| 1.5 | 2025-05 | Google Sheets 3-tier fallback, Refresh button |
| 1.6 | 2025-06 | Big Data explorer (5,249 samples), Issue tracker sync |
| 1.7 | 2026-06 | Enhanced Overview charts, live pipeline banner, Docker support |
