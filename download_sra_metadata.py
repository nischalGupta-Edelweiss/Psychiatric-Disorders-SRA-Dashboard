import os
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "sra_metadata.db")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")

os.makedirs(METADATA_DIR, exist_ok=True)

def main():
    if not os.path.exists(DB_FILE):
        print(f"Error: Database {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    m_studies = []
    try:
        cursor.execute("SELECT DISTINCT study_id FROM studies")
        m_studies = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error reading studies: {e}")
        conn.close()
        return
    conn.close()

    print(f"Found {len(m_studies)} studies. Downloading metadata using pysradb...")

    for i, study_id in enumerate(m_studies):
        print(f"[{i+1}/{len(m_studies)}] Fetching {study_id}...", end=" ", flush=True)
        
        out_file = os.path.join(METADATA_DIR, f"{study_id}_metadata.tsv")
        if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
            print("Skipped (already exists)")
            continue
            
        try:
            result = subprocess.run(
                ["pysradb", "metadata", study_id, "--detailed", "--expand"],
                capture_output=True, text=True, check=True
            )
            
            if not result.stdout.strip():
                print("Failed (No Output)")
                continue

            with open(out_file, "w") as f:
                f.write(result.stdout)
            print("Done")
        except subprocess.CalledProcessError as e:
            print(f"Failed. {e.stderr.strip() if e.stderr else 'Unknown error'}")
        except FileNotFoundError:
            print("Failed. 'pysradb' not found in path. Ensure you run this inside the correct pixi environment.")
            break

if __name__ == "__main__":
    main()
