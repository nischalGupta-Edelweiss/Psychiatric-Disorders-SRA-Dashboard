import os
import sqlite3
import pandas as pd
import csv
from datetime import datetime

# Define database file path
DB_FILE = "/home/surajkumar.sharma/Documents/AbbVie/sra_streamlit_app/sra_metadata.db"
SAMPLESHEETS_DIR = "/home/surajkumar.sharma/Documents/AbbVie/samplesheet"
FINALLIST_CSV = "/home/surajkumar.sharma/Documents/AbbVie/sra_streamlit_app/studies_82.csv"
PIPELINE_CSV = "/home/surajkumar.sharma/Documents/AbbVie/sra_streamlit_app/pipeline_info.csv"

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issue_studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            disease_category TEXT,
            issue_type TEXT,
            issue_description TEXT,
            date_flagged TEXT,
            flagged_by TEXT,
            priority TEXT,
            resolution_status TEXT,
            notes TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
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

    col_study   = fc(df, "study", "id")
    col_disease = fc(df, "disease", "category")
    col_type    = fc(df, "issue_type", "type")
    col_desc    = fc(df, "description", "reason")
    col_date    = fc(df, "date", "flagged")
    col_by      = fc(df, "flagged_by", "analyst", "by")
    col_pri     = fc(df, "priority")
    col_status  = fc(df, "status", "resolution")
    col_notes   = fc(df, "notes", "comment")

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
            str(row.get(col_disease, "") if col_disease else ""),
            str(row.get(col_type,    "") if col_type    else ""),
            str(row.get(col_desc,    "") if col_desc    else ""),
            str(row.get(col_date,    "") if col_date    else ""),
            str(row.get(col_by,      "") if col_by      else ""),
            str(row.get(col_pri,     "") if col_pri     else ""),
            str(row.get(col_status,  "") if col_status  else ""),
            str(row.get(col_notes,   "") if col_notes   else ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

    cursor.executemany("""
        INSERT INTO issue_studies (
            study_id, disease_category, issue_type, issue_description,
            date_flagged, flagged_by, priority, resolution_status, notes, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    # 2. Parse and ingest sample sheets
    if not os.path.exists(SAMPLESHEETS_DIR):
        print(f"Error: Sample sheets folder {SAMPLESHEETS_DIR} not found!")
        conn.close()
        return

    print(f"Scanning sample sheets inside {SAMPLESHEETS_DIR}...")
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
        default_ppts = [
            ("SRP246389", "Internship PPT (Schizophrenia hiPSC neurons)", "/home/surajkumar.sharma/Downloads/Internship ppt.pptx", "Slide presentation reviewing epigenetic forebrain schizophrenia results.", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("SRP115956", "Strand Template Presentation", "/home/surajkumar.sharma/Downloads/Strand PPT Template.pdf", "Generic template for presentation layouts.", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
            df_pipe = pd.read_csv(PIPELINE_CSV)
            df_pipe.columns = [c.strip() for c in df_pipe.columns]
            insert_pipe_stmt = """
                INSERT OR REPLACE INTO pipeline_info (
                    study_id, be_start_date, be_end_date, artemis_start_date,
                    artemis_end_date, samples_analyzed, remove_sample, region,
                    main_comparison, covariates
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            pipe_records = []
            for _, row in df_pipe.iterrows():
                sid = str(row.get('SRPID', row.get('study_id', ''))).strip()
                if not sid or sid == 'nan': continue
                
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
                    str(row.get('Main Comparison', '')),
                    str(row.get('Covariates', ''))
                ))
            cursor.executemany(insert_pipe_stmt, pipe_records)
            conn.commit()
            print(f"Ingested {len(pipe_records)} pipeline info records.")
        except Exception as e:
            print(f"Error loading pipeline info: {e}")
            
    conn.close()

if __name__ == "__main__":
    init_db()
    populate_database()
    populate_issue_studies()
