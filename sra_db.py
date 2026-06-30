import os
import sqlite3
import pandas as pd
import csv
from datetime import datetime

# Define database file path relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(BASE_DIR)
DB_FILE = os.path.join(BASE_DIR, "sra_metadata.db")
# External samplesheet dir — only exists in the original AbbVie workspace.
# Falls back gracefully to an empty scan so the app still works for others.
_ext_samplesheets = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "samplesheet"))

SAMPLESHEETS_DIR = _ext_samplesheets if os.path.isdir(_ext_samplesheets) else os.path.join(BASE_DIR, "samplesheet")
FINALLIST_CSV = os.path.join(BASE_DIR, "studies_82.csv")
_ext_pipeline = os.path.abspath(os.path.join(BASE_DIR, "..", "pipeline_info.csv"))
PIPELINE_CSV = _ext_pipeline if os.path.exists(_ext_pipeline) else os.path.join(BASE_DIR, "Summary-tracker.xlsx")

def init_db():
    """
    Initializes SQLite tables for SRA studies, sample sheets, and linked PPTs.
    """
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create studies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS studies (
            study_id TEXT PRIMARY KEY,
            title TEXT,
            abstract TEXT,
            organism TEXT,
            sample_size INTEGER,
            geo_id TEXT,
            library_strategy TEXT,
            library_source TEXT,
            database_source TEXT,
            keyword TEXT,
            has_schizophrenia TEXT,
            has_bipolar TEXT,
            has_depression TEXT,
            has_mdd TEXT,
            has_bipolar_dep TEXT,
            treatment TEXT,
            treatment_notes TEXT,
            cell_line TEXT,
            cell_type TEXT,
            source_name TEXT,
            tissue TEXT,
            comments TEXT
        )
    """)

    # Create sample_sheets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_sheets (
            sample_id TEXT PRIMARY KEY,
            study_id TEXT,
            fastq_1 TEXT,
            fastq_2 TEXT,
            strandedness TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        )
    """)

    # Create linked_ppts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS linked_ppts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT,
            ppt_name TEXT,
            ppt_path TEXT,
            description TEXT,
            added_date TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        )
    """)

    # Create pipeline_info table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_info (
            study_id TEXT PRIMARY KEY,
            be_start_date TEXT,
            be_end_date TEXT,
            artemis_start_date TEXT,
            artemis_end_date TEXT,
            samples_analyzed INTEGER,
            remove_sample TEXT,
            region TEXT,
            main_comparison TEXT,
            covariates TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        )
    """)

    # Create pipeline_tracker table (editable per study)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_tracker (
            study_id TEXT PRIMARY KEY,
            be_start_date TEXT,
            be_end_date TEXT,
            artemis_start_date TEXT,
            artemis_end_date TEXT,
            samples_analyzed INTEGER,
            remove_sample TEXT,
            region TEXT,
            main_comparison TEXT,
            covariates TEXT,
            pipeline_status TEXT,
            notes TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        )
    """)

    # Create summary_tracker table (editable per study)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summary_tracker (
            study_id TEXT PRIMARY KEY,
            analysis_lead TEXT,
            data_qc_status TEXT,
            de_status TEXT,
            pathway_status TEXT,
            figures_status TEXT,
            report_status TEXT,
            key_findings TEXT,
            next_steps TEXT,
            last_updated TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        )
    """)

    # Create issue_studies table — tracks studies that cannot be processed
    cursor.execute("DROP TABLE IF EXISTS issue_studies")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issue_studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT,
            pubmed_id TEXT,
            geo_id TEXT,
            issue_type TEXT,
            severity TEXT,
            comments TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
        )
    """)

    # Create sample_metadata table — tracks sample-level metadata (demographics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_metadata (
            run_accession TEXT PRIMARY KEY,
            study_accession TEXT,
            experiment_accession TEXT,
            sample_accession TEXT,
            organism_name TEXT,
            sample_title TEXT,
            disease_status TEXT,
            gender TEXT,
            tissue TEXT,
            cell_type TEXT,
            cell_line TEXT,
            source_name TEXT,
            age TEXT,
            treatment TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Database tables initialized successfully.")


def populate_issue_studies(excel_path=None, worksheet="Issue_tracker"):
    """
    Seed the issue_studies table from a local Excel worksheet.
    Safe to call multiple times — uses INSERT OR IGNORE on study_id.
    """
    import os

    if excel_path is None:
        excel_path = os.path.join(
            os.path.dirname(__file__),
            "Summary-tracker.xlsx"
        )

    if not os.path.exists(excel_path):
        print(f"⚠️ Excel file not found: {excel_path}")
        return

    try:
        df = pd.read_excel(excel_path, sheet_name=worksheet)
    except Exception as e:
        print(f"⚠️ Could not read worksheet '{worksheet}' from {excel_path}: {e}")
        return

    df.columns = [c.strip() for c in df.columns]

    # Flexible column mapping
    def fc(df, *keywords):
        for kw in keywords:
            match = [c for c in df.columns if kw.lower() in c.lower()]
            if match:
                return match[0]
        return None

    col_study   = fc(df, "StudyId", "study", "id")
    col_pubmed  = fc(df, "pubmedId", "pubmed")
    col_geo     = fc(df, "GSE_id", "geo")
    col_type    = fc(df, "Issues", "issue_type", "type")
    col_severity = fc(df, "Severity", "severity")
    col_comments = fc(df, "Comments", "comment")

    if not col_study:
        print("⚠️ Could not find a Study ID column in the worksheet.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    records = []
    for _, row in df.iterrows():
        sid = str(row.get(col_study, "")).strip()
        if not sid or sid == "nan":
            continue
        records.append((
            sid,
            str(row.get(col_pubmed, "") if col_pubmed else ""),
            str(row.get(col_geo,    "") if col_geo    else ""),
            str(row.get(col_type,    "") if col_type    else ""),
            str(row.get(col_severity,"") if col_severity else ""),
            str(row.get(col_comments,"") if col_comments else ""),
        ))

    cursor.executemany("""
        INSERT INTO issue_studies (
            study_id, pubmed_id, geo_id, issue_type, severity, comments, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, records)
    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(records)} issue study records into the database.")

def populate_database():
    """
    Scans the local sample sheets directory and parses the finalList.csv metadata
    to populate the SQLite database.
    """
    if not os.path.exists(FINALLIST_CSV):
        print(f"Error: metadata file {FINALLIST_CSV} not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Parse and ingest studies from finalList.csv
    print(f"Loading study metadata from {FINALLIST_CSV}...")
    try:
        # Load with pandas to handle multi-line quotes and various encodings easily
        df_studies = pd.read_csv(FINALLIST_CSV)
        # Clean column names
        df_studies.columns = [c.strip() for c in df_studies.columns]
        
        # Insert or replace studies
        insert_study_stmt = """
            INSERT OR REPLACE INTO studies (
                study_id, title, abstract, organism, sample_size, geo_id, 
                library_strategy, library_source, database_source, keyword,
                has_schizophrenia, has_bipolar, has_depression, has_mdd,
                has_bipolar_dep, treatment, treatment_notes, cell_line,
                cell_type, source_name, tissue, comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        study_records = []
        for _, row in df_studies.iterrows():
            study_id = str(row.get('ENA/SRA ID', '')).strip()
            if not study_id or study_id == 'nan' or study_id == '':
                continue
            
            study_records.append((
                study_id,
                row.get('Title', row.get('title', '')),
                row.get('Abstract/Summary/Description', row.get('Abstract', row.get('abstract', ''))),
                row.get('Organism', row.get('organism', '')),
                int(row.get('Sample Size', row.get('sample_size', 0))) if pd.notna(row.get('Sample Size', row.get('sample_size'))) else 0,
                row.get('GEO ID', ''),
                row.get('Library Strategy', ''),
                row.get('Library Source', ''),
                row.get('Database', ''),
                row.get('Search Keyword', row.get('keyword', '')),
                row.get('Schizophrenia', ''),
                row.get('Bipolar disorder', ''),
                row.get('Depression', ''),
                row.get('Major Depressive Disorder', ''),
                row.get('Bipolar Depression', ''),
                row.get('Treatment', ''),
                row.get('Treatment Notes', ''),
                row.get('Cell Line', ''),
                row.get('Cell Type', ''),
                row.get('Source Name', ''),
                row.get('Tissue', ''),
                row.get('Comments', '')
            ))
            
        cursor.executemany(insert_study_stmt, study_records)
        conn.commit()
        print(f"Ingested {len(study_records)} studies into the database.")
    except Exception as e:
        print(f"Error loading studies metadata: {e}")

    # 2. Parse and ingest sample sheets (optional — not present on external machines)
    if not os.path.exists(SAMPLESHEETS_DIR):
        print(f"⚠️ Sample sheets folder not found — skipping sample ingestion. Studies will still load.")
        # Don't return — continue seeding the rest of the DB (issues, PPTs, etc.)
    else:
        sample_files = [f for f in os.listdir(SAMPLESHEETS_DIR) if f.endswith("_samplesheet.csv")]
        
        insert_sample_stmt = """
            INSERT OR REPLACE INTO sample_sheets (
                sample_id, study_id, fastq_1, fastq_2, strandedness
            ) VALUES (?, ?, ?, ?, ?)
        """
        
        total_samples = 0
        for filename in sample_files:
            # Extract study ID, e.g. SRP246389_samplesheet.csv -> SRP246389
            study_id = filename.split("_")[0]
            filepath = os.path.join(SAMPLESHEETS_DIR, filename)
            
            # Read the sample sheet CSV
            try:
                with open(filepath, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    sample_records = []
                    for row in reader:
                        sample_id = row.get('sample', '').strip()
                        if not sample_id:
                            continue
                        
                        sample_records.append((
                            sample_id,
                            study_id,
                            row.get('fastq_1', ''),
                            row.get('fastq_2', ''),
                            row.get('strandedness', 'auto')
                        ))
                    
                    if sample_records:
                        cursor.executemany(insert_sample_stmt, sample_records)
                        total_samples += len(sample_records)
                        
                        # Ensure the study exists in the 'studies' table even if not in finalList.csv
                        cursor.execute("SELECT 1 FROM studies WHERE study_id = ?", (study_id,))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO studies (
                                    study_id, title, abstract, organism, sample_size, 
                                    database_source, has_schizophrenia, has_bipolar, 
                                    has_depression, has_mdd, has_bipolar_dep, treatment
                                )
                                VALUES (?, ?, ?, ?, ?, ?, '', '', '', '', '', '')
                            """, (
                                study_id,
                                f"Study {study_id}",
                                "",
                                "Homo sapiens", # default
                                len(sample_records),
                                "Custom Ingest"
                            ))
            except Exception as e:
                print(f"Error parsing file {filename}: {e}")
                
        conn.commit()
        print(f"Ingested {total_samples} samples across {len(sample_files)} sample sheets.")

    
    # 3. Add initial default PPT presentation linking for test references
    cursor.execute("SELECT COUNT(*) FROM linked_ppts")
    if cursor.fetchone()[0] == 0:
        downloads_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "downloads"))
        default_ppts = [
            ("SRP246389", "Internship PPT (Schizophrenia hiPSC neurons)", os.path.join(downloads_dir, "Internship ppt.pptx"), "Slide presentation reviewing epigenetic forebrain schizophrenia results.", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("SRP115956", "Strand Template Presentation", os.path.join(downloads_dir, "Strand PPT Template.pdf"), "Generic template for presentation layouts.", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ]
        cursor.executemany("""
            INSERT INTO linked_ppts (study_id, ppt_name, ppt_path, description, added_date)
            VALUES (?, ?, ?, ?, ?)
        """, default_ppts)
        conn.commit()
        print("Default linked PPT files seeded successfully.")
        
    # 4. Parse and ingest pipeline info
    if os.path.exists(PIPELINE_CSV):
        print(f"Loading pipeline info from {PIPELINE_CSV}...")
        try:
            if str(PIPELINE_CSV).lower().endswith(('.xlsx', '.xls')):
                # Check sheets
                xls = pd.ExcelFile(PIPELINE_CSV)
                ws = "Study info" if "Study info" in xls.sheet_names else 0
                df_pipe = pd.read_excel(PIPELINE_CSV, sheet_name=ws)
            else:
                df_pipe = pd.read_csv(PIPELINE_CSV)
                
            df_pipe.columns = [str(c).strip() for c in df_pipe.columns]
            
            # Clean string values in cells
            for col in df_pipe.columns:
                try:
                    if df_pipe[col].dtype == 'object':
                        df_pipe[col] = df_pipe[col].apply(lambda val: str(val).strip() if pd.notna(val) and val is not None else val)
                except Exception:
                    pass

            insert_pipe_stmt = """
                INSERT OR REPLACE INTO pipeline_info (
                    study_id, be_start_date, be_end_date, artemis_start_date,
                    artemis_end_date, samples_analyzed, remove_sample, region,
                    main_comparison, covariates
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            pipe_records = []
            for _, row in df_pipe.iterrows():
                # Allow different naming variants (Study_id, study_id, SRPID)
                sid = next((str(row.get(col)).strip() for col in df_pipe.columns if col.lower() in ('study_id', 'study_id', 'srpid', 'study id')), '').strip()
                if not sid or sid.lower() == 'nan':
                    continue
                
                # Helper for int parsing
                try: 
                    samples_num = int(row.get('Number of sample analyzed', 0)) if pd.notna(row.get('Number of sample analyzed')) else 0
                except (ValueError, TypeError):
                    samples_num = 0
                    
                pipe_records.append((
                    sid,
                    str(row.get('BE Pipeline Start Date', '')),
                    str(row.get('BE Pipeline End Date', '')),
                    str(row.get('Artemis Start Date', '')),
                    str(row.get('Artemis End Date', '')),
                    samples_num,
                    str(row.get('Remove Sample', '')),
                    str(row.get('Region', '')),
                    str(row.get('Main Comparison', row.get('ARTEMIS_Main_comparision', row.get('publication_comparision', '')))),
                    str(row.get('Covariates', row.get('Covarites_used', row.get('publication_covariates', ''))))
                ))
            cursor.executemany(insert_pipe_stmt, pipe_records)
            conn.commit()
            print(f"Ingested {len(pipe_records)} pipeline info records.")
        except Exception as e:
            print(f"Error loading pipeline info: {e}")
            
    # 5. Parse and ingest master sample metadata (demographics)
    master_metadata_csv = os.path.join(BASE_DIR, "master_sample_metadata.csv")
    if os.path.exists(master_metadata_csv):
        print(f"Loading sample metadata from {master_metadata_csv}...")
        try:
            df_sm = pd.read_csv(master_metadata_csv)
            # Clean string values in cells
            for col in df_sm.columns:
                try:
                    if df_sm[col].dtype == 'object':
                        df_sm[col] = df_sm[col].apply(lambda val: str(val).strip() if pd.notna(val) and val is not None else val)
                except Exception:
                    pass
            # Write to SQLite
            df_sm.to_sql('sample_metadata', conn, if_exists='replace', index=False)
            print(f"Ingested {len(df_sm)} sample metadata records.")
        except Exception as e:
            print(f"Error loading sample metadata: {e}")

    conn.close()

if __name__ == "__main__":
    init_db()
    populate_database()
    populate_issue_studies()
