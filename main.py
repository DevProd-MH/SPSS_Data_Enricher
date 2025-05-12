import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import pyreadstat
import re
import unidecode
import random

# === Configuration ===
# Your Worksheet Name
SPREADSHEET_NAME = "Worksheet (Responses)"

# The index of the worksheet you want to read from (0 for the first sheet)
# If you have multiple sheets, change this index accordingly
WORKSHEET_INDEX = 0

# Google API credentials
# Make sure to create a service account and download the JSON key file
JSON_KEY_FILE = "credentials.json"  # Path to your Google API credentials JSON file
# The JSON key file should be in the same directory as this script
                                   
OUTPUT_SAV_FILE = "survey_data.sav"     # Output file name for SPSS .sav file



# === Authenticate with Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scope)
client = gspread.authorize(creds)

# === Fetch all sheet data ===
sheet = client.open(SPREADSHEET_NAME).get_worksheet(WORKSHEET_INDEX)
all_data = sheet.get_all_values()

# === Detect header row (first with 2+ non-empty cells) ===
header_row = next((i for i, row in enumerate(all_data) if len([c for c in row if c.strip()]) >= 2), None)
if header_row is None:
    raise Exception("❌ No valid header row found.")

headers = all_data[header_row]
rows = all_data[header_row + 1:]

# === Remove timestamp-like columns ===
exclude_indices = [i for i, col in enumerate(headers) if "time" in col.lower()]
clean_headers = [col for i, col in enumerate(headers) if i not in exclude_indices]
clean_rows = [[cell for i, cell in enumerate(row) if i not in exclude_indices] for row in rows]

# === Normalize rows strictly to match header length ===
row_length = len(clean_headers)
normalized_rows = []
for row in clean_rows:
    trimmed = row[:row_length]
    if len(trimmed) < row_length:
        trimmed += [''] * (row_length - len(trimmed))
    normalized_rows.append(trimmed)

# === Create DataFrame using only valid headers ===
df = pd.DataFrame(normalized_rows, columns=clean_headers)
df = df.loc[:, clean_headers]
df.dropna(axis=1, how='all', inplace=True)

# === Clean and ensure unique SPSS-compatible column names ===
def clean_column(name):
    name = unidecode.unidecode(name)
    name = re.sub(r'\W+', '_', name)
    if not name or not name[0].isalpha():
        name = "v_" + name
    return name[:64]

raw_columns = df.columns.tolist()
cleaned_columns = []
seen = {}

# Ensure unique column names
# by appending a number if the base name already exists
for col in raw_columns:
    base = clean_column(col)
    count = seen.get(base, 0)
    new_name = base if count == 0 else f"{base}_{count}"
    seen[base] = count + 1
    cleaned_columns.append(new_name)

df.columns = cleaned_columns

# === Export cleaned data to SPSS .sav ===
pyreadstat.write_sav(df, OUTPUT_SAV_FILE)
print(f"✅ Data exported to: {OUTPUT_SAV_FILE}")

# === Prompt for data enrichment ===
if input("Do you want to add random rows to the data? (y/n): ").strip().lower() != 'y':
    print("Exiting without adding random rows.")
    exit()

# === Read back .sav with metadata ===
df, meta = pyreadstat.read_sav(OUTPUT_SAV_FILE)
columns = list(meta.column_names)  # Use only the original columns

# === Ensure we use existing columns for random data generation ===
# Build answer options from current data
survey_questions = {}
column_data_types = {}

for col in df.columns:
    unique_vals = df[col].dropna().unique()

    if len(unique_vals) == 0:
        # Skip columns with no data
        continue

    if pd.api.types.is_numeric_dtype(df[col]):
        column_data_types[col] = 'numeric'
        min_val, max_val = df[col].min(), df[col].max()
        if pd.isnull(min_val) or pd.isnull(max_val):
            continue  # skip columns with bad numeric data
        survey_questions[col] = (min_val, max_val)
    else:
        column_data_types[col] = 'categorical'
        survey_questions[col] = list(unique_vals)

# === Random row generation based on existing columns ===
def generate_random_answers():
    row = {}
    for col in columns:
        if column_data_types[col] == 'numeric':
            # Generate a random number within the range of the existing values
            min_val, max_val = survey_questions[col]
            row[col] = random.uniform(min_val, max_val) if isinstance(min_val, float) else random.randint(min_val, max_val)
        else:
            # Generate a random answer from the list of unique values for categorical columns
            row[col] = random.choice(survey_questions[col])
    return row

NUMBER_OF_ROWS_TO_ADD = int(input("Enter the number of rows to add: "))
random_rows = [generate_random_answers() for _ in range(NUMBER_OF_ROWS_TO_ADD)]
random_df = pd.DataFrame(random_rows, columns=columns)

# === Combine and export enriched data without adding extra columns ===
df_enriched = pd.concat([df, random_df], ignore_index=True, sort=False)  # Ensure no extra columns are added
df_enriched = df_enriched[columns]  # Reorder columns to match original

# === Remove empty columns (columns with all NaN values) ===
df_enriched = df_enriched.dropna(axis=1, how='all')

# === Export the enriched data to .sav ===
pyreadstat.write_sav(df_enriched, "survey_data_enriched.sav")
print("✅ Data enriched and saved to survey_data_enriched.sav")

# === Optional: Convert to CSV for verification ===
df_enriched.to_csv("converted.csv", index=False)
print("✅ CSV preview saved as converted.csv")
