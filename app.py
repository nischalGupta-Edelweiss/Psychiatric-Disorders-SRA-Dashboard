import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import streamlit_authenticator as stauth

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Psychiatric Disorders SRA Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Authentication ─────────────────────────────────────────────────────────────
_auth_file = os.path.join(os.path.dirname(__file__), "users.yaml")
with open(_auth_file) as _f:
    _cfg = yaml.load(_f, Loader=SafeLoader)

_authenticator = stauth.Authenticate(
    _cfg["credentials"], _cfg["cookie"]["name"],
    _cfg["cookie"]["key"], _cfg["cookie"]["expiry_days"]
)
_authenticator.login("main")
_name = st.session_state.get("name")
_auth_status = st.session_state.get("authentication_status")
_username = st.session_state.get("username")

if _auth_status is False:
    st.error("❌ Incorrect username or password. Please try again.")
    st.stop()
elif _auth_status is None:
    st.info("👆 Please enter your credentials above to access the dashboard.")
    st.stop()

# Logged in — show user info and logout in sidebar
_authenticator.logout("🚪 Logout", "sidebar")
st.sidebar.markdown(f"👤 **{_name}**")
if st.sidebar.button("🔄 Refresh Live Data"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")

DB_FILE  = os.path.join(os.path.dirname(__file__), "sra_metadata.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
def get_sheet_config(sheet_key, default_fallback):
    config_file = os.path.join(os.path.dirname(__file__), "googlesheetlink.csv")
    url = None
    ws_name = None
    fallback = os.path.join(os.path.dirname(__file__), default_fallback)
    if os.path.exists(config_file):
        try:
            df = pd.read_csv(config_file)
            row = df[df['sheet_name'] == sheet_key]
            if not row.empty:
                _url = str(row.iloc[0]['url']).strip()
                if _url and _url.lower() != 'nan':
                    url = _url
                if 'worksheet_name' in df.columns:
                    _ws = str(row.iloc[0]['worksheet_name']).strip()
                    if _ws and _ws.lower() != 'nan':
                        ws_name = _ws
                _fb = str(row.iloc[0]['local_fallback']).strip()
                if _fb and _fb.lower() != 'nan':
                    fallback = os.path.join(os.path.dirname(__file__), _fb)
        except Exception:
            pass
    # Returns: (primary_source, worksheet_name, local_fallback_path)
    return url or fallback, ws_name, fallback

SUMMARY_CSV, SUMMARY_WS, SUMMARY_FB = get_sheet_config("summary_tracker", "Summary-tracker.xlsx")
PIPELINE_CSV, PIPELINE_WS, PIPELINE_FB = get_sheet_config("pipeline_info", "Summary-tracker.xlsx")
ISSUE_CSV,   ISSUE_WS,   ISSUE_FB   = get_sheet_config("issue_studies",  "Summary-tracker.xlsx")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
}
h1,h2,h3,h4,h5,h6 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

/* Banner */
.banner {
    background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #831843 100%);
    padding: 2.5rem 3rem;
    border-radius: 20px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 10px 40px rgba(76,29,149,0.4);
    position: relative;
    overflow: hidden;
}
.banner::before {
    content: '';
    position: absolute;
    top: -60%; left: -60%;
    width: 220%; height: 220%;
    background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
    animation: spin 15s infinite linear;
}
@keyframes spin { from {transform:rotate(0deg)} to {transform:rotate(360deg)} }
.banner-title  { font-size:2.4rem; margin:0; font-weight:700; }
.banner-sub    { font-size:1.05rem; opacity:.85; margin-top:.4rem; font-weight:300; }

/* Metric cards */
.cards { display:flex; gap:1.2rem; margin-bottom:2rem; flex-wrap:wrap; }
.card {
    flex:1; min-width:180px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius:14px; padding:1.3rem;
    transition: all .3s ease;
}
.card:hover { transform:translateY(-4px); border-color:rgba(139,92,246,.45); }
.card-label { font-size:.75rem; color:#9ca3af; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
.card-val {
    font-size:2rem; font-weight:700;
    background: linear-gradient(90deg,#e9d5ff,#fbcfe8);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.card-sub { font-size:.75rem; color:#10b981; margin-top:.15rem; }

/* Glass containers */
.glass {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius:16px; padding:1.8rem;
    margin-bottom:1.8rem;
    backdrop-filter:blur(10px);
}

/* Disease badges */
.badge {
    display:inline-block;
    padding:.25rem .65rem;
    border-radius:999px;
    font-size:.72rem;
    font-weight:600;
    margin:.15rem;
}
.badge-sz  { background:rgba(139,92,246,.25); color:#c4b5fd; border:1px solid rgba(139,92,246,.4); }
.badge-bd  { background:rgba(59,130,246,.25); color:#93c5fd; border:1px solid rgba(59,130,246,.4); }
.badge-dep { background:rgba(16,185,129,.25); color:#6ee7b7; border:1px solid rgba(16,185,129,.4); }
.badge-mdd { background:rgba(249,115,22,.25); color:#fdba74; border:1px solid rgba(249,115,22,.4); }

/* Sidebar */
section[data-testid="stSidebar"] { background:#0f0f1a; }
.stButton>button {
    border-radius:10px !important;
    font-weight:600 !important;
    transition: all .2s ease !important;
}
</style>
""", unsafe_allow_html=True)

import hashlib

# ── Caching & DB Helpers ──────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_tracker_csv(path_or_url, worksheet_name=None, local_fallback=None):
    """Load data via Google Sheets API with a 3-tier fallback:
    1. Google Sheets API (live)
    2. SQLite cache (last successful fetch)
    3. Local Excel/CSV file (offline safety net)
    """
    import re

    def _read_local(fb_path, ws):
        """Read local Excel or CSV file."""
        if not fb_path or not os.path.exists(fb_path):
            return None
        try:
            if str(fb_path).lower().endswith(('.xlsx', '.xls')):
                # Try the specific worksheet tab first, then sheet index 0
                try:
                    df = pd.read_excel(fb_path, sheet_name=ws)
                    print(f"📂 Loaded '{ws}' tab from local Excel: {os.path.basename(fb_path)}")
                    return df
                except Exception:
                    df = pd.read_excel(fb_path, sheet_name=0)
                    print(f"📂 Loaded first tab from local Excel: {os.path.basename(fb_path)}")
                    return df
            return pd.read_csv(fb_path)
        except Exception as e:
            print(f"⚠️ Local fallback read failed ({fb_path}): {e}")
            return None

    if str(path_or_url).startswith("http"):
        # Strip ?gid=...#gid=... from URL — let worksheet= param handle tab selection
        clean_url = re.sub(r'[?#].*$', '', str(path_or_url)).rstrip('/')
        clean_url = clean_url + "/export?format=csv" if False else clean_url  # keep as sheets URL

        # Unique SQLite table name (keyed on original URL + worksheet)
        hash_str   = f"{path_or_url}_{worksheet_name}" if worksheet_name else path_or_url
        url_hash   = hashlib.md5(hash_str.encode()).hexdigest()
        table_name = f"cache_{url_hash}"

        # ── Tier 1: Google Sheets API ────────────────────────────────────────
        try:
            from streamlit_gsheets import GSheetsConnection
            conn_gs = st.connection("gsheets", type=GSheetsConnection)
            if worksheet_name:
                df = conn_gs.read(spreadsheet=clean_url, worksheet=worksheet_name)
            else:
                df = conn_gs.read(spreadsheet=clean_url)
            # Persist successful fetch to SQLite
            with sqlite3.connect(DB_FILE) as sql_conn:
                df.to_sql(table_name, sql_conn, if_exists='replace', index=False)
            print(f"✅ Loaded '{worksheet_name}' from Google Sheets")
            return df
        except Exception as e:
            print(f"⚠️ Google Sheets API failed: {e}")

        # ── Tier 2: SQLite cache ─────────────────────────────────────────────
        try:
            with sqlite3.connect(DB_FILE) as sql_conn:
                df = pd.read_sql(f"SELECT * FROM {table_name}", sql_conn)
                print(f"🔄 Loaded '{worksheet_name}' from SQLite cache")
                return df
        except Exception as sql_e:
            print(f"⚠️ SQLite cache not found: {sql_e}")

        # ── Tier 3: Local Excel / CSV fallback ───────────────────────────────
        print(f"📂 Trying local fallback for '{worksheet_name}'...")
        return _read_local(local_fallback, worksheet_name)

    else:
        # Direct local file path
        return _read_local(path_or_url, worksheet_name)

# ── DB Helpers ────────────────────────────────────────────────────────────────
def db():
    return sqlite3.connect(DB_FILE)

def metrics():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM studies")
    n_studies = c.fetchone()[0]
    c.execute("SELECT SUM(sample_size) FROM studies")
    n_samples = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT keyword) FROM studies WHERE keyword IS NOT NULL AND keyword!=''")
    n_kw = c.fetchone()[0]
    conn.close()
    return n_studies, n_samples, n_kw

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
  <h1 class="banner-title">🧠 Psychiatric Disorders SRA Study Hub</h1>
  <p class="banner-sub">82 curated RNA-seq studies · Schizophrenia · Bipolar Disorder · Depression · MDD</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar Nav ───────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🧭 Navigation")
mode = st.sidebar.radio("", ["📊 Overview & Analytics", "🔍 Study Explorer", "⚠️ Issue Studies"])

n_st, n_sa, n_kw = metrics()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**🧬 Total Studies** `{n_st}`")
st.sidebar.markdown(f"**🔬 Total Samples** `{n_sa:,}`")
st.sidebar.markdown(f"**🏷️ Disease Categories** `{n_kw}`")

# ─────────────────────────────────────────────────────────────────────────────
#  MODE 1 — OVERVIEW & ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
if mode == "📊 Overview & Analytics":
    st.markdown("## 📈 Overview & Analytics")

    # Top-level processing summary
    st.markdown("""
    <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1.8rem;padding:1.2rem 1.5rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;">
      <div style="flex:1;border-right:1px solid rgba(255,255,255,0.05);">
        <span style="font-size:.8rem;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;">Total Datasets</span><br>
        <strong style="font-size:1.8rem;color:#f1f5f9;">82</strong>
      </div>
      <div style="flex:1;border-right:1px solid rgba(255,255,255,0.05);">
        <span style="font-size:.8rem;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;">BE Complete</span><br>
        <strong style="font-size:1.8rem;color:#6ee7b7;">42</strong>
      </div>
      <div style="flex:1;">
        <span style="font-size:.8rem;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;">Artemis Complete</span><br>
        <strong style="font-size:1.8rem;color:#a5b4fc;">34</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Metric cards
    st.markdown(f"""
    <div class="cards">
      <div class="card">
        <div class="card-label">Curated Studies</div>
        <div class="card-val">{n_st}</div>
        <div class="card-sub">▲ 82 unique SRP/ERP IDs</div>
      </div>
      <div class="card">
        <div class="card-label">Total Samples</div>
        <div class="card-val">{n_sa:,}</div>
        <div class="card-sub">▲ Across all studies</div>
      </div>
      <div class="card">
        <div class="card-label">Disease Keywords</div>
        <div class="card-val">{n_kw}</div>
        <div class="card-sub">▲ SCZ · BD · DEP · MDD</div>
      </div>
      <div class="card">
        <div class="card-sub">▲ Presentations linked</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    conn = db()

    # Row 1: Disease distribution + Database source
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("🏷️ Studies by Disease Keyword")
        df_kw = pd.read_sql("SELECT keyword, COUNT(*) as n, SUM(sample_size) as samples FROM studies GROUP BY keyword ORDER BY n DESC", conn)
        if not df_kw.empty:
            fig = px.bar(df_kw, x='keyword', y='n',
                         color='keyword',
                         color_discrete_sequence=['#8b5cf6','#3b82f6','#10b981','#f97316','#ec4899'],
                         text='n',
                         labels={'keyword':'Disease','n':'Studies'})
            fig.update_traces(textposition='outside')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#e2e8f0', showlegend=False,
                              xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.06)'),
                              margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("🗄️ Database Source Distribution")
        df_db = pd.read_sql("SELECT database_source, COUNT(*) as n FROM studies WHERE database_source!='' GROUP BY database_source", conn)
        if not df_db.empty:
            fig2 = px.pie(df_db, values='n', names='database_source', hole=0.45,
                          color_discrete_sequence=['#8b5cf6','#3b82f6','#10b981'])
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0',
                               margin=dict(t=10,b=10),
                               legend=dict(orientation="h", y=-0.15, x=0.5, xanchor='center'))
            st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: Sample size distribution + Disease flag heatmap
    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("📦 Sample Size Distribution by Disease")
        df_sz = pd.read_sql("SELECT study_id, keyword, sample_size FROM studies WHERE sample_size > 0 ORDER BY sample_size DESC", conn)
        if not df_sz.empty:
            fig3 = px.box(df_sz, x='keyword', y='sample_size',
                          color='keyword',
                          color_discrete_sequence=['#8b5cf6','#3b82f6','#10b981','#f97316'],
                          labels={'keyword':'Disease','sample_size':'# Samples'},
                          points='all')
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               font_color='#e2e8f0', showlegend=False,
                               xaxis=dict(showgrid=False), yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                               margin=dict(t=10,b=10))
            st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("🔥 Disease Flag Coverage")
        df_flags = pd.read_sql("""
            SELECT
                SUM(CASE WHEN has_schizophrenia='Yes' THEN 1 ELSE 0 END) as Schizophrenia,
                SUM(CASE WHEN has_bipolar='Yes' THEN 1 ELSE 0 END) as 'Bipolar Disorder',
                SUM(CASE WHEN has_depression='Yes' THEN 1 ELSE 0 END) as Depression,
                SUM(CASE WHEN has_mdd='Yes' THEN 1 ELSE 0 END) as MDD,
                SUM(CASE WHEN has_bipolar_dep='Yes' THEN 1 ELSE 0 END) as 'Bipolar Depression',
                SUM(CASE WHEN treatment='Yes' THEN 1 ELSE 0 END) as 'Treatment Studies'
            FROM studies
        """, conn)
        flags_long = df_flags.T.reset_index()
        flags_long.columns = ['Flag','Count']
        fig4 = px.bar(flags_long, x='Count', y='Flag', orientation='h',
                      color='Count',
                      color_continuous_scale=['#1e1b4b','#8b5cf6','#ec4899'],
                      text='Count',
                      labels={'Flag':'','Count':'Studies'})
        fig4.update_traces(textposition='outside')
        fig4.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                           font_color='#e2e8f0', coloraxis_showscale=False,
                           xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.06)'),
                           yaxis=dict(showgrid=False),
                           margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Top studies by sample size
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("🏆 Top 15 Studies by Sample Size")
    df_top = pd.read_sql("SELECT study_id, title, keyword, sample_size, geo_id FROM studies ORDER BY sample_size DESC LIMIT 15", conn)
    if not df_top.empty:
        fig5 = px.bar(df_top, x='sample_size', y='study_id', orientation='h',
                      color='keyword',
                      color_discrete_sequence=['#8b5cf6','#3b82f6','#10b981','#f97316'],
                      hover_data={'title':True, 'geo_id':True},
                      labels={'sample_size':'Sample Count','study_id':'Study ID','keyword':'Disease'})
        fig5.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                           font_color='#e2e8f0', height=420,
                           yaxis=dict(showgrid=False, autorange='reversed'),
                           xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.06)'),
                           margin=dict(t=10,b=10),
                           legend=dict(orientation='h', y=-0.15, x=.5, xanchor='center'))
        st.plotly_chart(fig5, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    conn.close()

# ─────────────────────────────────────────────────────────────────────────────
#  MODE 2 — STUDY EXPLORER
# ─────────────────────────────────────────────────────────────────────────────
elif mode == "🔍 Study Explorer":
    st.markdown("## 🔍 Study Explorer")
    conn = db()

    # ── Sidebar filters ──
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Filters")

    search_kw = st.sidebar.text_input("🔍 Search (ID / Title / Abstract)")

    keywords   = ["All"] + sorted(pd.read_sql("SELECT DISTINCT keyword FROM studies WHERE keyword!=''", conn)['keyword'].tolist())
    databases  = ["All"] + sorted(pd.read_sql("SELECT DISTINCT database_source FROM studies WHERE database_source!=''", conn)['database_source'].tolist())

    sel_kw  = st.sidebar.selectbox("Disease Category", keywords)
    sel_db  = st.sidebar.selectbox("Database Source", databases)

    st.sidebar.markdown("**Disease Flags**")
    fl_sz  = st.sidebar.checkbox("Schizophrenia")
    fl_bd  = st.sidebar.checkbox("Bipolar Disorder")
    fl_dep = st.sidebar.checkbox("Depression")
    fl_mdd = st.sidebar.checkbox("MDD")
    fl_tx  = st.sidebar.checkbox("Has Treatment")

    min_s, max_s = 0, int(pd.read_sql("SELECT MAX(sample_size) FROM studies", conn).iloc[0,0] or 0)
    sel_range = st.sidebar.slider("Sample Size Range", min_s, max(max_s,1), (min_s, max(max_s,1)))

    # ── Build query ──
    q = "SELECT * FROM studies WHERE 1=1"
    p = []
    if search_kw:
        q += " AND (study_id LIKE ? OR title LIKE ? OR abstract LIKE ?)"
        p += [f"%{search_kw}%"]*3
    if sel_kw != "All":
        q += " AND keyword=?"; p.append(sel_kw)
    if sel_db != "All":
        q += " AND database_source=?"; p.append(sel_db)
    if fl_sz:  q += " AND has_schizophrenia='Yes'"
    if fl_bd:  q += " AND has_bipolar='Yes'"
    if fl_dep: q += " AND has_depression='Yes'"
    if fl_mdd: q += " AND has_mdd='Yes'"
    if fl_tx:  q += " AND treatment='Yes'"
    q += " AND sample_size BETWEEN ? AND ?"; p += [sel_range[0], sel_range[1]]
    q += " ORDER BY sample_size DESC"

    df_res = pd.read_sql(q, conn, params=p)

    st.info(f"🔍 **{len(df_res)}** studies match your filters")

    if not df_res.empty:
        # Study selector
        study_opts = df_res['study_id'].tolist()
        sel_id = st.selectbox("📂 Select Study to Explore", study_opts,
                              format_func=lambda s: f"{s}  —  {df_res[df_res.study_id==s]['title'].values[0][:80]}...")

        row = df_res[df_res.study_id == sel_id].iloc[0]

        # Build disease badge HTML
        badges = ""
        if row['has_schizophrenia'] == 'Yes': badges += '<span class="badge badge-sz">Schizophrenia</span>'
        if row['has_bipolar']       == 'Yes': badges += '<span class="badge badge-bd">Bipolar Disorder</span>'
        if row['has_depression']    == 'Yes': badges += '<span class="badge badge-dep">Depression</span>'
        if row['has_mdd']           == 'Yes': badges += '<span class="badge badge-mdd">MDD</span>'
        if not badges: badges = '<span class="badge" style="background:rgba(255,255,255,.08);color:#94a3b8;">General</span>'

        st.markdown(f"""
        <div class="glass" style="border-top:4px solid #8b5cf6;">
          <div style="margin-bottom:.8rem;">{badges}</div>
          <h3 style="color:#f1f5f9;margin:0 0 .6rem 0;">{row['title']}</h3>
          <p style="color:#cbd5e1;font-size:.9rem;line-height:1.65;">{row['abstract'][:600]}{'...' if len(str(row['abstract']))>600 else ''}</p>
          <div style="display:flex;gap:2rem;flex-wrap:wrap;margin-top:1.2rem;font-size:.9rem;">
            <div><strong>🔑 Study ID</strong><br><code style="color:#f472b6;">{row['study_id']}</code></div>
            <div><strong>🗂️ GEO ID</strong><br><code style="color:#60a5fa;">{row['geo_id'] or 'N/A'}</code></div>
            <div><strong>🧬 Organism</strong><br>{row['organism']}</div>
            <div><strong>🔬 Samples</strong><br><code>{row['sample_size']}</code></div>
            <div><strong>🗄️ Database</strong><br>{row['database_source']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # -- Sample metadata chips (source_name / tissue / cell_type / cell_line) --
        chip_fields = [
            ("🔬 Source Name", row.get('source_name'), "Biological source of the sample (e.g. brain region, cell culture, organism part)."),
            ("🧫 Tissue",      row.get('tissue'),      "Tissue type profiled (e.g. prefrontal cortex, hippocampus, dorsolateral PFC)."),
            ("🧬 Cell Type",   row.get('cell_type'),   "Specific cell type profiled (e.g. neurons, astrocytes, oligodendrocytes, PBMCs)."),
            ("🔭 Cell Line",   row.get('cell_line'),   "Cell line used if applicable (e.g. iPSC-derived lines, immortalised cell lines)."),
        ]
        chips_html = ""
        for label, val, desc in chip_fields:
            v = str(val or "").strip()
            if v and v not in ("nan", "N/A", ""):
                chips_html += (f'<div style="margin:.35rem 0"><span style="color:#a78bfa;font-weight:600">{label}:</span> '
                               f'<span style="color:#e2e8f0">{v}</span> '
                               f'<span style="font-size:.72rem;color:#475569"> — {desc}</span></div>')
        if chips_html:
            st.markdown(f'<div class="glass" style="padding:.9rem 1.4rem;margin-top:.4rem">{chips_html}</div>', unsafe_allow_html=True)
        if row['treatment'] == 'Yes':
            st.markdown(f'<div style="font-size:.85rem;color:#6ee7b7;margin:.4rem 0"><strong>💊 Treatment:</strong> Yes — {row["treatment_notes"] or ""}</div>', unsafe_allow_html=True)
        if row['comments'] and str(row['comments']) not in ('nan', ''):
            st.markdown(f'<div style="font-size:.85rem;color:#fbbf24;margin:.2rem 0"><strong>📝 Comments:</strong> {row["comments"]}</div>', unsafe_allow_html=True)

        # -- External Links --
        ncbi_url = f"https://www.ncbi.nlm.nih.gov/Traces/study/?acc={sel_id}&o=acc_s%3Aa"
        geo_id   = row['geo_id']
        geo_link = ""
        if geo_id and str(geo_id) not in ("", "nan", "N/A"):
            geo_link = f'&nbsp;&nbsp;<a href="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={geo_id}" target="_blank" style="background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.4);border-radius:8px;padding:.45rem 1rem;color:#6ee7b7;font-size:.85rem;font-weight:600;text-decoration:none;">🧬 GEO: {geo_id}</a>'
        st.markdown(f"""
        <div style="margin-bottom:1.2rem;">
            <a href="{ncbi_url}" target="_blank"
               style="background:rgba(99,102,241,.2);border:1px solid rgba(99,102,241,.5);
                      border-radius:8px;padding:.45rem 1rem;color:#a5b4fc;
                      font-size:.85rem;font-weight:600;text-decoration:none;">
              🔗 NCBI Run Selector Metadata
            </a>
            {geo_link}
        </div>
        """, unsafe_allow_html=True)

        # Tabs
        tab1, tab_samp, tab2, tab3, tab4, tab5 = st.tabs(["📝 Sample Sheet", "👥 Sample Info", "🖥️ Slides", "📋 Full Metadata", "📊 Execution Stats", "🔧 Analysis Info"])

        with tab1:
            df_ss = pd.read_sql("SELECT sample_id, fastq_1, fastq_2, strandedness FROM sample_sheets WHERE study_id=?",
                                conn, params=[sel_id])
            if not df_ss.empty:
                # Detect sequencing end type
                has_fq1 = df_ss['fastq_1'].str.strip().ne('')
                has_fq2 = df_ss['fastq_2'].str.strip().ne('')
                n_paired = (has_fq1 & has_fq2).sum()
                n_single = (has_fq1 & ~has_fq2).sum()
                if n_paired > 0 and n_single > 0:
                    end_type = "⚡ Mixed (single & paired-end)"
                    end_color = "#f97316"
                elif n_paired > 0:
                    end_type = "🔗 Paired-end"
                    end_color = "#10b981"
                else:
                    end_type = "➡️ Single-end"
                    end_color = "#60a5fa"

                # Study-level sample metadata
                st.markdown(f"""
                <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1rem;">
                  <div><span style="font-size:.75rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em">FASTQ Entries</span><br><strong style="font-size:1.4rem">{len(df_ss)}</strong></div>
                  <div><span style="font-size:.75rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em">Sequencing Type</span><br><strong style="color:{end_color}">{end_type}</strong></div>
                  <div><span style="font-size:.75rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em">Paired Samples</span><br><strong>{n_paired}</strong></div>
                  <div><span style="font-size:.75rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em">Single Samples</span><br><strong>{n_single}</strong></div>
                </div>
                """, unsafe_allow_html=True)

                # Field descriptions
                st.markdown("""
                <div style="font-size:.78rem;color:#64748b;margin-bottom:.8rem">
                  <strong style="color:#94a3b8">Column guide:</strong>
                  <span style="margin-left:.5rem"><code>sample_id</code> — SRA run accession (SRR…)</span> ·
                  <span><code>fastq_1</code> — S3 path to R1 (or single-end) FASTQ</span> ·
                  <span><code>fastq_2</code> — S3 path to R2 FASTQ (empty = single-end)</span> ·
                  <span><code>strandedness</code> — Library strandedness used in pipeline</span>
                </div>
                """, unsafe_allow_html=True)

                s_search = st.text_input("🔍 Search samples")
                disp = df_ss[df_ss['sample_id'].str.contains(s_search, case=False)] if s_search else df_ss
                st.dataframe(disp, use_container_width=True)
                st.download_button("📥 Download Sample Sheet (.csv)",
                                   df_ss.to_csv(index=False).encode(),
                                   file_name=f"{sel_id}_samplesheet.csv",
                                   mime="text/csv")
            else:
                st.warning(f"No sample sheet loaded for {sel_id}.")

        with tab_samp:
            st.markdown("### 👥 Sample Demographics & Info")
            try:
                df_samp = pd.read_sql("SELECT run_accession, sample_title, organism_name, disease_status, gender, tissue, cell_type, cell_line, source_name, age, treatment FROM sample_metadata WHERE study_accession=?", conn, params=[sel_id])
                
                if not df_samp.empty:
                    # Clean up empty strings with None
                    df_samp = df_samp.replace('', pd.NA).dropna(axis=1, how='all')
                    
                    # Show charts if disease_status exists
                    if 'disease_status' in df_samp.columns and not df_samp['disease_status'].isna().all():
                        c1, c2 = st.columns(2)
                        with c1:
                            fig = px.pie(df_samp, names='disease_status', title='Disease Status', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig.update_traces(textposition='inside', textinfo='label+value+percent')
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0', margin=dict(t=30,b=10), showlegend=True)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        if 'gender' in df_samp.columns and not df_samp['gender'].isna().all():
                            with c2:
                                # Normalize gender to lowercase for colors
                                df_samp['gender'] = df_samp['gender'].astype(str).str.lower()
                                fig2 = px.pie(df_samp, names='gender', title='Gender', hole=0.4, color_discrete_sequence=['#60a5fa', '#f472b6', '#a78bfa', '#cbd5e1'])
                                fig2.update_traces(textposition='inside', textinfo='label+value')
                                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0', margin=dict(t=30,b=10), showlegend=True)
                                st.plotly_chart(fig2, use_container_width=True)
                    
                    s_samp = st.text_input("🔍 Search Sample Info", key="search_samp")
                    disp_samp = df_samp[df_samp.astype(str).apply(lambda x: x.str.contains(s_samp, case=False, na=False)).any(axis=1)] if s_samp else df_samp
                    st.dataframe(disp_samp, use_container_width=True)
                    
                    st.download_button("📥 Download Sample Info (.csv)",
                                       df_samp.to_csv(index=False).encode(),
                                       file_name=f"{sel_id}_sample_metadata.csv",
                                       mime="text/csv")
                else:
                    st.info("⚠️ No detailed sample metadata available for this study in the database.")
            except Exception as e:
                st.error(f"Could not load sample metadata: {e}")

        with tab2:
            st.markdown("#### 🖥️ Presentations & Summary Slides")
            st.caption("Slide links are pulled from the Summary Tracker CSV for this study.")
            # Pull slide link from Summary CSV
            _slide_link = None
            _df_sv = load_tracker_csv(SUMMARY_CSV, SUMMARY_WS, local_fallback=SUMMARY_FB)
            if _df_sv is not None:
                try:
                    _df_sv.columns = [c.strip() for c in _df_sv.columns]
                    _id_col = next((c for c in _df_sv.columns if "dataset" in c.lower() or "name" in c.lower()), _df_sv.columns[0])
                    _slide_col = next((c for c in _df_sv.columns if "slide" in c.lower() or "ppt" in c.lower()), None)
                    if _slide_col:
                        _match = _df_sv[_df_sv[_id_col].astype(str).str.strip() == sel_id]
                        if not _match.empty:
                            _slide_link = str(_match.iloc[0][_slide_col]).strip()
                            if _slide_link in ("nan", ""):
                                _slide_link = None
                except Exception:
                    pass
            if _slide_link:
                st.markdown(
                    f'<div style="margin:1.2rem 0">'  
                    f'<a href="{_slide_link}" target="_blank" '
                    f'style="background:linear-gradient(135deg,#4c1d95,#831843);color:white;border-radius:12px;'
                    f'padding:.8rem 1.6rem;font-size:1rem;font-weight:700;text-decoration:none;'
                    f'box-shadow:0 4px 20px rgba(139,92,246,.35);display:inline-block;">'
                    f'📊 Open Summary Slides'
                    f'</a></div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div style="font-size:.8rem;color:#64748b;word-break:break-all;margin-top:.4rem">'
                    f'🔗 <a href="{_slide_link}" target="_blank" style="color:#60a5fa">{_slide_link}</a></div>',
                    unsafe_allow_html=True
                )
            else:
                st.info(f"No summary slide link found for **{sel_id}** in the Summary Tracker CSV.")

        with tab3:
            meta = {
                "Study ID": row['study_id'],
                "GEO ID": row['geo_id'],
                "Title": row['title'],
                "Abstract": row['abstract'],
                "Organism": row['organism'],
                "Sample Size": row['sample_size'],
                "Library Strategy": row['library_strategy'],
                "Database": row['database_source'],
                "Disease Keyword": row['keyword'],
                "Schizophrenia": row['has_schizophrenia'],
                "Bipolar Disorder": row['has_bipolar'],
                "Depression": row['has_depression'],
                "MDD": row['has_mdd'],
                "Bipolar Depression": row['has_bipolar_dep'],
                "Treatment": row['treatment'],
                "Treatment Notes": row['treatment_notes'],
                "Cell Line": row['cell_line'],
                "Cell Type": row['cell_type'],
                "Source Name": row['source_name'],
                "Comments": row['comments'],
            }
            df_meta = pd.DataFrame(meta.items(), columns=["Field", "Value"])
            st.dataframe(df_meta, use_container_width=True, hide_index=True)

        with tab4:
            st.markdown("#### 📊 Summary Tracker")
            st.caption("Live view from the Summary Tracker CSV. Columns: Dataset Name · Start/End Dates · Status · QC Overview · Counts QC · Done By · Summary Slides link · Comments.")

            # Column descriptions
            SUMMARY_COL_DESC = {
                "Dataset Name":       "SRA/ERP study accession ID.",
                "Start Date":         "Date the BE pipeline was kicked off for this study.",
                "Status":             "Current pipeline/analysis status (e.g. Artemis completed, BE error).",
                "End Date (BE)":      "Date the BE pipeline finished processing.",
                "QC Overview":        "High-level sample QC observations from the analyst.",
                "Counts QC overview": "QC notes specific to read counts / mapping metrics.",
                "Done by":            "Analyst who ran the pipeline for this study.",
                "Summary slides":     "Google Slides link containing QC summary for this study.",
                "Comments":           "Additional notes or caveats about this study's run.",
            }

            df_sum_all = load_tracker_csv(SUMMARY_CSV, SUMMARY_WS, local_fallback=SUMMARY_FB)
            if df_sum_all is not None:
                try:
                    df_sum_all.columns = [c.strip() for c in df_sum_all.columns]
                    # Try matching on 'Dataset Name' column
                    id_col = next((c for c in df_sum_all.columns if 'dataset' in c.lower() or 'name' in c.lower()), df_sum_all.columns[0])
                    df_sum = df_sum_all[df_sum_all[id_col].astype(str).str.strip() == sel_id]

                    if not df_sum.empty:
                        for _, sr in df_sum.iterrows():
                            for col in df_sum.columns:
                                val = str(sr[col]).strip()
                                if val and val not in ('nan', ''):
                                    desc = SUMMARY_COL_DESC.get(col, "")
                                    is_link = val.startswith('http')
                                    val_html = f'<a href="{val}" target="_blank" style="color:#60a5fa">🔗 Open Slides</a>' if is_link else f'<span style="color:#e2e8f0">{val}</span>'
                                    st.markdown(
                                        f'<div style="border-left:3px solid #8b5cf6;padding:.5rem 1rem;margin:.3rem 0;background:rgba(139,92,246,.06);border-radius:0 8px 8px 0">'
                                        f'<span style="font-size:.75rem;color:#a78bfa;font-weight:600;text-transform:uppercase">{col}</span>'
                                        f'<span style="font-size:.72rem;color:#475569;margin-left:.5rem">— {desc}</span><br>'
                                        f'{val_html}</div>',
                                        unsafe_allow_html=True
                                    )
                    else:
                        st.info(f"No summary tracker entry found for **{sel_id}** in the CSV.")

                    st.markdown("---")
                    st.markdown("##### 📋 All Entries in Summary Tracker")
                    st.dataframe(df_sum_all, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Could not load summary tracker CSV: {e}")
            else:
                st.warning(f"Summary tracker CSV not found at: `{SUMMARY_CSV}`")

        with tab5:
            st.markdown("#### 🔧 Pipeline Info")
            st.caption("Live view from the Pipeline Info CSV. Columns: Study ID · Publication · Comparisons · Covariates · ARTEMIS Run ID · Results.")

            PIPE_COL_DESC = {
                "Study_id":                  "SRA study accession ID.",
                "publication_link":          "PubMed or journal link for the associated publication.",
                "publication_comparision":   "The main comparison as defined in the original publication.",
                "publication_covariates":    "Covariates reported in the publication's statistical model.",
                "ARTEMIS_Run_ID":            "Unique identifier for the Artemis analysis run.",
                "ARTEMIS_Main_comparision":  "The comparison actually run in the Artemis pipeline.",
                "Covarites_used":            "Covariates used in the Artemis differential expression model.",
            }

            df_pi_all = load_tracker_csv(PIPELINE_CSV, PIPELINE_WS, local_fallback=PIPELINE_FB)
            if df_pi_all is not None:
                try:
                    df_pi_all.columns = [c.strip() for c in df_pi_all.columns]
                    id_col_pi = next((c for c in df_pi_all.columns if 'study' in c.lower() or 'id' in c.lower()), df_pi_all.columns[0])
                    df_pi = df_pi_all[df_pi_all[id_col_pi].astype(str).str.strip() == sel_id]

                    if not df_pi.empty:
                        for _, pr in df_pi.iterrows():
                            for col in df_pi.columns:
                                val = str(pr[col]).strip()
                                if val and val not in ('nan', ''):
                                    desc = PIPE_COL_DESC.get(col, "")
                                    is_link = val.startswith('http')
                                    val_html = f'<a href="{val}" target="_blank" style="color:#60a5fa">🔗 Open Publication</a>' if is_link else f'<span style="color:#e2e8f0">{val}</span>'
                                    st.markdown(
                                        f'<div style="border-left:3px solid #10b981;padding:.5rem 1rem;margin:.3rem 0;background:rgba(16,185,129,.06);border-radius:0 8px 8px 0">'
                                        f'<span style="font-size:.75rem;color:#6ee7b7;font-weight:600;text-transform:uppercase">{col}</span>'
                                        f'<span style="font-size:.72rem;color:#475569;margin-left:.5rem">— {desc}</span><br>'
                                        f'{val_html}</div>',
                                        unsafe_allow_html=True
                                    )
                    else:
                        st.info(f"No pipeline info entry found for **{sel_id}** in the CSV.")

                    st.markdown("---")
                    st.markdown("##### 📋 All Entries in Pipeline Info")
                    st.dataframe(df_pi_all, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Could not load pipeline info CSV: {e}")
            else:
                st.warning(f"Pipeline info CSV not found at: `{PIPELINE_CSV}`")

        # Results table below
        st.markdown("### 📋 All Matching Studies")
        display_cols = ['study_id','title','keyword','sample_size','geo_id','database_source','treatment']
        st.dataframe(df_res[display_cols].reset_index(drop=True), use_container_width=True)
        st.download_button("📥 Export Filtered List",
                           df_res[display_cols].to_csv(index=False).encode(),
                           file_name="filtered_studies.csv", mime="text/csv")
    else:
        st.warning("No studies match the current filters.")

    conn.close()

# ─────────────────────────────────────────────────────────────────────────────
#  MODE 3 — ISSUE STUDIES
# ─────────────────────────────────────────────────────────────────────────────
elif mode == "⚠️ Issue Studies":
    st.markdown("## ⚠️ Issue Studies Tracker")
    st.markdown(
        '<p style="color:#94a3b8;margin-top:-.8rem;margin-bottom:1.5rem;">'
        'Studies flagged as unprocessable — tracking root causes, priority, and resolution status.'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Load data ────────────────────────────────────────────────────────────
    df_issues = load_tracker_csv(ISSUE_CSV, ISSUE_WS, local_fallback=ISSUE_FB)

    if df_issues is None or df_issues.empty:
        st.warning(
            "No issue studies data found. "
            "Please add an **'Issue Studies'** worksheet to your Google Sheet "
            "or populate `issue_studies_fallback.csv`."
        )
        st.markdown(
            "**Expected columns:** `Study_ID · Disease_Category · Issue_Type · "
            "Issue_Description · Date_Flagged · Flagged_By · Priority · Resolution_Status · Notes`"
        )
    else:
        df_issues.columns = [c.strip() for c in df_issues.columns]

        # ── Normalise key column names (flexible header matching) ─────────────
        col_map = {}
        for c in df_issues.columns:
            cl = c.lower().replace(" ", "_")
            if "study" in cl or "id" in cl:       col_map.setdefault("Study_ID", c)
            if "disease" in cl or "category" in cl: col_map.setdefault("Disease_Category", c)
            if "issue_type" in cl or ("type" in cl and "issue" in cl): col_map.setdefault("Issue_Type", c)
            if "description" in cl or "reason" in cl: col_map.setdefault("Issue_Description", c)
            if "date" in cl or "flagged" in cl:   col_map.setdefault("Date_Flagged", c)
            if "by" in cl or "analyst" in cl:     col_map.setdefault("Flagged_By", c)
            if "priority" in cl:                  col_map.setdefault("Priority", c)
            if "status" in cl or "resolution" in cl: col_map.setdefault("Resolution_Status", c)
            if "note" in cl or "comment" in cl:   col_map.setdefault("Notes", c)

        def gc(key):
            """Get actual column name from normalised key, or None."""
            return col_map.get(key)

        # ── Summary metric cards ──────────────────────────────────────────────
        total_issues = len(df_issues)
        open_issues  = 0
        resolved     = 0
        high_pri     = 0
        if gc("Resolution_Status"):
            open_issues = (df_issues[gc("Resolution_Status")].astype(str).str.lower().str.contains("open")).sum()
            resolved    = (df_issues[gc("Resolution_Status")].astype(str).str.lower().str.contains("resolved|closed|done")).sum()
        if gc("Priority"):
            high_pri = (df_issues[gc("Priority")].astype(str).str.lower() == "high").sum()

        st.markdown(f"""
        <div class="cards">
          <div class="card">
            <div class="card-label">Total Flagged</div>
            <div class="card-val" style="background:linear-gradient(90deg,#fde68a,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{total_issues}</div>
            <div class="card-sub">Studies with issues</div>
          </div>
          <div class="card">
            <div class="card-label">Open Issues</div>
            <div class="card-val" style="background:linear-gradient(90deg,#fca5a5,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{open_issues}</div>
            <div class="card-sub">Pending resolution</div>
          </div>
          <div class="card">
            <div class="card-label">High Priority</div>
            <div class="card-val" style="background:linear-gradient(90deg,#fdba74,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{high_pri}</div>
            <div class="card-sub">Needs urgent action</div>
          </div>
          <div class="card">
            <div class="card-label">Resolved</div>
            <div class="card-val" style="background:linear-gradient(90deg,#6ee7b7,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{resolved}</div>
            <div class="card-sub">Completed / closed</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Issue Type breakdown chart ────────────────────────────────────────
        if gc("Issue_Type"):
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.subheader("📊 Issues by Type")
            df_type_count = df_issues[gc("Issue_Type")].value_counts().reset_index()
            df_type_count.columns = ["Issue Type", "Count"]
            fig_iss = px.bar(
                df_type_count, x="Count", y="Issue Type", orientation="h",
                color="Issue Type",
                color_discrete_sequence=["#f97316", "#ef4444", "#eab308", "#8b5cf6", "#3b82f6", "#10b981"],
                text="Count",
                labels={"Count": "Number of Studies"},
            )
            fig_iss.update_traces(textposition="outside")
            fig_iss.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0", showlegend=False,
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(showgrid=False), margin=dict(t=10, b=10),
            )
            st.plotly_chart(fig_iss, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Sidebar filters ───────────────────────────────────────────────────
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Filters")

        search_iss = st.sidebar.text_input("🔍 Search Study ID / Description")

        if gc("Issue_Type"):
            issue_types = ["All"] + sorted(df_issues[gc("Issue_Type")].dropna().unique().tolist())
            sel_type = st.sidebar.selectbox("Issue Type", issue_types)
        else:
            sel_type = "All"

        if gc("Priority"):
            priorities = ["All"] + sorted(df_issues[gc("Priority")].dropna().unique().tolist())
            sel_pri = st.sidebar.selectbox("Priority", priorities)
        else:
            sel_pri = "All"

        if gc("Resolution_Status"):
            statuses = ["All"] + sorted(df_issues[gc("Resolution_Status")].dropna().unique().tolist())
            sel_status = st.sidebar.selectbox("Resolution Status", statuses)
        else:
            sel_status = "All"

        # ── Apply filters ─────────────────────────────────────────────────────
        df_filt = df_issues.copy()
        if search_iss:
            mask = df_filt.astype(str).apply(
                lambda col: col.str.contains(search_iss, case=False, na=False)
            ).any(axis=1)
            df_filt = df_filt[mask]
        if sel_type   != "All" and gc("Issue_Type"):        df_filt = df_filt[df_filt[gc("Issue_Type")] == sel_type]
        if sel_pri    != "All" and gc("Priority"):          df_filt = df_filt[df_filt[gc("Priority")] == sel_pri]
        if sel_status != "All" and gc("Resolution_Status"): df_filt = df_filt[df_filt[gc("Resolution_Status")] == sel_status]

        st.info(f"⚠️ **{len(df_filt)}** issue studies match your filters")

        # ── Per-study detail cards ────────────────────────────────────────────
        PRIORITY_COLORS = {"high": "#ef4444", "medium": "#f97316", "low": "#eab308"}
        STATUS_COLORS   = {"open": "#ef4444", "in progress": "#f97316",
                           "resolved": "#10b981", "closed": "#10b981", "done": "#10b981"}

        for _, row_i in df_filt.iterrows():
            study_id_val = str(row_i.get(gc("Study_ID"), "Unknown")).strip() if gc("Study_ID") else "Unknown"
            issue_type   = str(row_i.get(gc("Issue_Type"), "")).strip()          if gc("Issue_Type") else ""
            description  = str(row_i.get(gc("Issue_Description"), "")).strip()   if gc("Issue_Description") else ""
            disease_cat  = str(row_i.get(gc("Disease_Category"), "")).strip()    if gc("Disease_Category") else ""
            date_flag    = str(row_i.get(gc("Date_Flagged"), "")).strip()         if gc("Date_Flagged") else ""
            flagged_by   = str(row_i.get(gc("Flagged_By"), "")).strip()           if gc("Flagged_By") else ""
            priority_val = str(row_i.get(gc("Priority"), "")).strip()             if gc("Priority") else ""
            status_val   = str(row_i.get(gc("Resolution_Status"), "")).strip()    if gc("Resolution_Status") else ""
            notes_val    = str(row_i.get(gc("Notes"), "")).strip()                if gc("Notes") else ""

            pri_color = PRIORITY_COLORS.get(priority_val.lower(), "#64748b")
            sts_color = STATUS_COLORS.get(status_val.lower(), "#64748b")

            clean = lambda v: "" if v in ("nan", "N/A", "None") else v
            description = clean(description)
            notes_val   = clean(notes_val)
            disease_cat = clean(disease_cat)

            st.markdown(f"""
            <div class="glass" style="border-left:4px solid {pri_color};margin-bottom:1rem;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.5rem;">
                <div>
                  <code style="font-size:1.05rem;color:#f472b6;font-weight:700;">{study_id_val}</code>
                  {'<span style="margin-left:.7rem;font-size:.8rem;color:#94a3b8;">' + disease_cat + '</span>' if disease_cat else ''}
                </div>
                <div style="display:flex;gap:.5rem;flex-wrap:wrap;">
                  {'<span style="background:rgba(239,68,68,.15);border:1px solid ' + pri_color + ';border-radius:999px;padding:.2rem .75rem;font-size:.72rem;font-weight:600;color:' + pri_color + ';">' + priority_val + ' Priority</span>' if priority_val else ''}
                  {'<span style="background:rgba(16,185,129,.1);border:1px solid ' + sts_color + ';border-radius:999px;padding:.2rem .75rem;font-size:.72rem;font-weight:600;color:' + sts_color + ';">' + status_val + '</span>' if status_val else ''}
                </div>
              </div>
              {'<div style="margin-top:.6rem;"><span style="font-size:.75rem;color:#a78bfa;font-weight:600;text-transform:uppercase;">Issue Type</span><br><span style="color:#e2e8f0;">' + issue_type + '</span></div>' if issue_type else ''}
              {'<div style="margin-top:.5rem;"><span style="font-size:.75rem;color:#a78bfa;font-weight:600;text-transform:uppercase;">Description</span><br><span style="color:#cbd5e1;font-size:.9rem;line-height:1.6;">' + description + '</span></div>' if description else ''}
              {'<div style="margin-top:.5rem;"><span style="font-size:.75rem;color:#a78bfa;font-weight:600;text-transform:uppercase;">Notes</span><br><span style="color:#94a3b8;font-size:.85rem;font-style:italic;">' + notes_val + '</span></div>' if notes_val else ''}
              <div style="margin-top:.8rem;display:flex;gap:2rem;flex-wrap:wrap;font-size:.8rem;color:#64748b;">
                {'<span>📅 Flagged: <strong>' + date_flag + '</strong></span>' if date_flag else ''}
                {'<span>👤 By: <strong>' + flagged_by + '</strong></span>' if flagged_by else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Full table + download ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 📋 All Issue Studies (Tabular View)")
        st.dataframe(df_filt.reset_index(drop=True), use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Export Issue Studies (.csv)",
            df_filt.to_csv(index=False).encode(),
            file_name="issue_studies_export.csv",
            mime="text/csv",
        )
