import os
import glob
import pandas as pd
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", "metadata"))
DB_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "sra_metadata.db"))
OUTPUT_CSV = os.path.abspath(os.path.join(BASE_DIR, "..", "master_sample_metadata.csv"))

def build_master_metadata():
    print(f"🔍 Scanning {METADATA_DIR} for metadata TSVs...")
    files = glob.glob(os.path.join(METADATA_DIR, "*_metadata.tsv"))
    print(f"📁 Found {len(files)} TSV files.")
    
    all_data = []
    
    for f in files:
        try:
            df = pd.read_csv(f, sep='\t', dtype=str)
            
            # Lowercase and strip column names
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Create a harmonized dictionary for each row
            for _, row in df.iterrows():
                # Core Identifiers
                record = {
                    'run_accession': row.get('run_accession', row.get('run', '')),
                    'study_accession': row.get('study_accession', row.get('study', '')),
                    'experiment_accession': row.get('experiment_accession', ''),
                    'sample_accession': row.get('sample_accession', ''),
                    'organism_name': row.get('organism_name', ''),
                    'sample_title': row.get('sample_title', ''),
                }
                
                # Health / Disease Status (Harmonized)
                disease_val = ""
                for col in ['diagnosis', 'disease state', 'disease', 'phenotype', 'condition', 'health_state']:
                    if col in df.columns and pd.notna(row[col]):
                        disease_val = row[col]
                        break
                record['disease_status'] = disease_val
                
                # Gender / Sex (Harmonized)
                gender_val = ""
                for col in ['gender', 'sex']:
                    if col in df.columns and pd.notna(row[col]):
                        gender_val = row[col]
                        break
                record['gender'] = gender_val
                
                # Tissue / Source / Cell Type
                record['tissue'] = row.get('tissue', '')
                record['cell_type'] = row.get('cell type', '')
                record['cell_line'] = row.get('cell line', '')
                record['source_name'] = row.get('source_name', '')
                record['age'] = row.get('age', '')
                record['treatment'] = row.get('treatment', '')
                
                all_data.append(record)
                
        except Exception as e:
            print(f"⚠️ Error processing {os.path.basename(f)}: {e}")

    # Create Master DataFrame
    master_df = pd.DataFrame(all_data)
    
    # Save to CSV
    master_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved Master CSV with {len(master_df)} total samples to: {OUTPUT_CSV}")
    
    # Save to SQLite Database
    try:
        conn = sqlite3.connect(DB_FILE)
        # Write to table 'sample_metadata', replace if exists
        master_df.to_sql('sample_metadata', conn, if_exists='replace', index=False)
        conn.close()
        print(f"✅ Successfully added 'sample_metadata' table to SQLite Database ({DB_FILE})")
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        
    return master_df

if __name__ == "__main__":
    df = build_master_metadata()
    print("\n📊 Preview of Master Metadata:")
    print(df.head(10).to_string())
