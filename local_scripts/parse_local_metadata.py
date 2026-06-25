import os
import sys
import pandas as pd
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", "metadata"))

def parse_local_metadata(srp_id):
    # Find the file in the metadata directory
    file_path = os.path.join(METADATA_DIR, f"{srp_id}_metadata.tsv")
    
    if not os.path.exists(file_path):
        print(f"❌ Could not find metadata file for {srp_id} at {file_path}")
        return None
        
    print(f"📂 Found local metadata file: {file_path}")
    
    # Read the TSV
    try:
        df = pd.read_csv(file_path, sep='\t')
    except Exception as e:
        print(f"❌ Error reading TSV file: {e}")
        return None
        
    # We want to extract SRR (run_accession), Organism (organism_name),
    # and Sample info like healthy/control (diagnosis, disease, etc.)
    
    # Normalize column names to lowercase to find them easily
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # Identify which columns we actually have in this specific TSV
    run_col = 'run_accession' if 'run_accession' in df.columns else 'run'
    org_col = 'organism_name' if 'organism_name' in df.columns else 'organism'
    sample_col = 'sample_title' if 'sample_title' in df.columns else 'sample_name'
    
    # Try to find the disease/diagnosis column dynamically
    disease_col = None
    for col in ['diagnosis', 'disease', 'health_state', 'phenotype', 'disease_state', 'subject_status']:
        if col in df.columns:
            disease_col = col
            break
            
    # Also grab gender if available
    gender_col = 'gender' if 'gender' in df.columns else 'sex' if 'sex' in df.columns else None
    
    # Select only the columns we found
    cols_to_keep = [run_col, org_col, sample_col]
    if disease_col: cols_to_keep.append(disease_col)
    if gender_col: cols_to_keep.append(gender_col)
    
    # Filter the dataframe to just these columns
    cols_to_keep = [c for c in cols_to_keep if c in df.columns]
    result_df = df[cols_to_keep].copy()
    
    return result_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse local metadata TSV for a given SRP ID")
    parser.add_argument("srp_id", help="The SRP accession to process (e.g. SRP050377)")
    args = parser.parse_args()
    
    df = parse_local_metadata(args.srp_id)
    
    if df is not None and not df.empty:
        print(f"✅ Successfully parsed {len(df)} samples.")
        print("\n📊 Extracted Data:")
        print(df.head(15).to_string())
        print("\n💡 You can easily integrate this exact logic into the Streamlit app!")
    else:
        print("⚠️ No data could be extracted.")
