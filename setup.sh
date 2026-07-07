#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh — Quick setup for Psychiatric Disorders SRA Dashboard
# Run this after cloning the repo: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
BOLD=$(tput bold 2>/dev/null || echo "")
RESET=$(tput sgr0 2>/dev/null || echo "")
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "${BOLD}🧠 Psychiatric Disorders SRA Dashboard — Setup${RESET}"
echo "────────────────────────────────────────────────"

# ── Step 1: Check Python ──────────────────────────────────────────────────────
echo ""
echo "${BOLD}[1/4] Checking Python version...${RESET}"
if command -v python3 &>/dev/null; then
    PY=$(python3 --version)
    echo -e "${GREEN}✅ Found: $PY${NC}"
    PY_CMD=python3
elif command -v python &>/dev/null; then
    PY=$(python --version)
    echo -e "${GREEN}✅ Found: $PY${NC}"
    PY_CMD=python
else
    echo -e "${RED}❌ Python not found. Install Python 3.9+ from https://python.org${NC}"
    exit 1
fi

# ── Step 2: Install dependencies ─────────────────────────────────────────────
echo ""
echo "${BOLD}[2/4] Installing Python dependencies...${RESET}"
$PY_CMD -m pip install -r requirements.txt --quiet && \
    echo -e "${GREEN}✅ All dependencies installed${NC}" || \
    { echo -e "${RED}❌ pip install failed. Try: pip install -r requirements.txt${NC}"; exit 1; }

# ── Step 3: Create secrets.toml ───────────────────────────────────────────────
echo ""
echo "${BOLD}[3/4] Setting up Streamlit secrets...${RESET}"
mkdir -p .streamlit

if [ -f ".streamlit/secrets.toml" ]; then
    echo -e "${YELLOW}⚠️  .streamlit/secrets.toml already exists — skipping.${NC}"
else
    cat > .streamlit/secrets.toml << 'EOF'
# ─────────────────────────────────────────────────────────────────────────────
# Google Sheets Service Account credentials
# Get this file from your team admin (Suraj)
# ─────────────────────────────────────────────────────────────────────────────
[connections.gsheets]
type = "service_account"
project_id = "YOUR_GCP_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"
EOF
    echo -e "${YELLOW}📝 Created .streamlit/secrets.toml — fill in your GCP credentials.${NC}"
    echo -e "${YELLOW}   (Without this, the app uses local Excel fallbacks — still works!)${NC}"
fi

# ── Step 4: Done ──────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}[4/4] Ready to launch!${RESET}"
echo ""
echo "────────────────────────────────────────────────"
echo -e "${GREEN}${BOLD}✅ Setup complete!${RESET}"
echo ""
echo "  Run the dashboard with:"
echo -e "  ${BOLD}streamlit run app.py${RESET}"
echo ""
echo "  Or with Docker (no Python setup needed):"
echo -e "  ${BOLD}docker compose up --build${RESET}"
echo ""
echo "  Login credentials: ask your team admin"
echo "────────────────────────────────────────────────"
