import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import pyreadstat
import mock_rules  # Import the mock rules module

# === Configuration ===
# Replace with your actual Google Sheets spreadsheet name and worksheet index
SPREADSHEET_NAME = "Worksheet"
WORKSHEET_INDEX = 0
JSON_KEY_FILE = "credentials.json"
RESULTS_FOLDER = "results"

# Create the 'results' folder if it doesn't exist
os.makedirs(RESULTS_FOLDER, exist_ok=True)

OUTPUT_SAV_FILE = os.path.join(RESULTS_FOLDER, SPREADSHEET_NAME + ".sav")

# === Authenticate with Google Sheets ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scope)
client = gspread.authorize(creds)

# === Fetch data from the spreadsheet ===
sheet = client.open(SPREADSHEET_NAME).get_worksheet(WORKSHEET_INDEX)
all_data = sheet.get_all_values()

# === Detect header row ===
header_row = next(
    (i for i, row in enumerate(all_data) if len([c for c in row if c.strip()]) >= 2),
    None,
)
if header_row is None:
    raise Exception("❌ No valid header row found.")

headers = all_data[header_row]
rows = all_data[header_row + 1 :]

# === Remove timestamp-like columns ===
exclude_indices = [i for i, col in enumerate(headers) if "time" in col.lower()]
clean_headers = [col for i, col in enumerate(headers) if i not in exclude_indices]
clean_rows = [
    [cell for i, cell in enumerate(row) if i not in exclude_indices] for row in rows
]

# === Normalize rows ===
row_length = len(clean_headers)
normalized_rows = [
    row[:row_length] + [""] * (row_length - len(row)) for row in clean_rows
]

# === Build DataFrame ===
df = pd.DataFrame(normalized_rows, columns=clean_headers)
df.dropna(axis=1, how="all", inplace=True)


# === Clean column names ===
def clean_column(name):
    return mock_rules.clean_column(name)


raw_columns = df.columns.tolist()
cleaned_columns = []
seen = {}

for col in raw_columns:
    base = clean_column(col)
    count = seen.get(base, 0)
    new_name = base if count == 0 else f"{base}_{count}"
    seen[base] = count + 1
    cleaned_columns.append(new_name)

df.columns = cleaned_columns

# === Export cleaned data ===
pyreadstat.write_sav(df, OUTPUT_SAV_FILE)
print(f"✅ Data exported to: {OUTPUT_SAV_FILE}")

# === Prompt for enrichment ===
if input("Do you want to add random rows to the data? (y/n): ").strip().lower() != "y":
    print("Exiting without adding random rows.")
    exit()

# === Enrich data using mock_rules ===
EXISTING_SAV_FILE = OUTPUT_SAV_FILE
NUMBER_OF_ROWS_TO_ADD = int(input("Enter the number of rows to add: "))
df, meta = pyreadstat.read_sav(EXISTING_SAV_FILE)

# Generate enriched data
df_enriched = mock_rules.generate_mock_data(df, meta, NUMBER_OF_ROWS_TO_ADD)

# Export enriched data
ENRICHED_OUTPUT_FILE = os.path.join(RESULTS_FOLDER, SPREADSHEET_NAME + "_enriched.sav")
pyreadstat.write_sav(df_enriched, ENRICHED_OUTPUT_FILE)
print(f"✅ Enriched data saved to: {ENRICHED_OUTPUT_FILE}")

# Optional: Save CSV for verification
CSV_OUTPUT_FILE = os.path.join(RESULTS_FOLDER, SPREADSHEET_NAME + ".csv")
df_enriched.to_csv(CSV_OUTPUT_FILE, index=False)
print(f"✅ CSV preview saved as: {CSV_OUTPUT_FILE}")
