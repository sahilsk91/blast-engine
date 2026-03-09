import sys
import pandas as pd
from local_db import init_db, save_lead

def merge_csv_to_db():
    init_db()
    for file_path in sys.argv[1:]:
        print(f"Merging {file_path} into deduplication database...")
        try:
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                email = str(row.get('Emails', '')).strip()
                if email and email.lower() != 'nan':
                    name = str(row.get('Name', '')).strip()
                    source = str(row.get('Source_URL', '')).strip()
                    save_lead(email, name, source)
        except Exception as e:
            print(f"Error merging {file_path}: {e}")

if __name__ == "__main__":
    merge_csv_to_db()
    print("Database sync complete.")
