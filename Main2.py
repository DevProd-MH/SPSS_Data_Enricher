import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import pyreadstat
import json
import random
import difflib
import mock_rules  # your cleaner

# === Configuration ===
SPREADSHEET_NAME = "Worksheet"
WORKSHEET_INDEX = 0
JSON_KEY_FILE = "credentials.json"
RESULTS_FOLDER = "results"

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

# === Load form questions/answers JSON ===
with open("form_questions.json", "r", encoding="utf-8") as f:
    form_data = json.load(f)

# === Build column → question mapping (with fuzzy matching) ===
col_to_question = {}
for col in df.columns:
    best_match = difflib.get_close_matches(
        col,
        [clean_column(q["question"]) for q in form_data],
        n=1,
        cutoff=0.65,
    )
    if best_match:
        for q in form_data:
            if clean_column(q["question"]) == best_match[0]:
                col_to_question[col] = q
                break

def generate_random_answer(question):
    answers = question["answers"]
    qtext = question["question"]

    if answers == ["(نص حر / رقم)"]:
        if "اسم" in qtext:
            return random.choice(
                ["أحمد", "محمد", "سارة", "ليلى", "يوسف", "مريم", "خديجة", "فاطمة"]
            )
        elif "المستوى" in qtext or "المرحلة" in qtext:
            return random.choice(["تمهيدي", "التحصيري"])
        else:
            return random.choice(["غير محدد", "—"])

    else:
        # Yes/No handling
        if set(answers) == {"نعم", "لا"}:
            # Behavioral/psychological keywords → bias to "لا"
            negative_keywords = [
                "مزاج",
                "يشتكي",
                "صعوبة",
                "خجل",
                "انسحاب",
                "قلق",
                "آلام",
                "متوتر",
                "مكتئب",
            ]
            if any(word in qtext for word in negative_keywords):
                return random.choices(["لا", "نعم"], weights=[0.7, 0.3])[0]
            else:
                return random.choices(["نعم", "لا"], weights=[0.7, 0.3])[0]

        # Frequency scale (ابدا/دائما/etc.)
        if any(x in answers for x in ["ابدا", "دائما"]):
            weights = [0.6] + [0.3] * (len(answers) - 2) + [0.1]
            return random.choices(answers, weights=weights[: len(answers)])[0]

        return random.choice(answers)


# === Generate mock rows ===
def generate_mock_rows(num_rows):
    new_rows = []
    for _ in range(num_rows):
        row = {}
        age_value = None

        for col in df.columns:
            if col in col_to_question:
                q = col_to_question[col]
                qtext = q["question"]

                # --- Age (3–5 only) ---
                if "عمر الطفل" in qtext:
                    age_value = random.randint(3, 5)
                    row[col] = str(age_value)

                # --- Stage (depends on age) ---
                elif "المرحلة الدراسية" in qtext and age_value is not None:
                    if age_value == 5:
                        row[col] = "التحصيري"
                    else:  # 3 or 4
                        row[col] = "التمهيدي"

                # --- Siblings (distribution depends on age) ---
                elif "عدد الأشقاء" in qtext:
                    if age_value == 3:
                        siblings = random.choices(
                            [0, 1, 2, 3],
                            weights=[40, 35, 20, 5],
                            k=1,
                        )[0]
                    elif age_value == 4:
                        siblings = random.choices(
                            [0, 1, 2, 3, 4],
                            weights=[20, 35, 30, 10, 5],
                            k=1,
                        )[0]
                    elif age_value == 5:
                        siblings = random.choices(
                            [0, 1, 2, 3, 4, 5],
                            weights=[10, 20, 35, 25, 7, 3],
                            k=1,
                        )[0]
                    else:
                        siblings = 1
                    row[col] = str(siblings)

                else:
                    row[col] = generate_random_answer(q)

            else:
                row[col] = random.choice(["غير محدد", "—", str(random.randint(1, 5))])

        new_rows.append(row)
    return new_rows

# === Enrich data ===
EXISTING_SAV_FILE = OUTPUT_SAV_FILE
NUMBER_OF_ROWS_TO_ADD = int(input("Enter the number of rows to add: "))
df, meta = pyreadstat.read_sav(EXISTING_SAV_FILE)

new_rows = generate_mock_rows(NUMBER_OF_ROWS_TO_ADD)
df_enriched = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

# === Remove completely empty rows ===
df_enriched.dropna(how="all", inplace=True)
df_enriched = df_enriched[
    ~(df_enriched.astype(str).apply(lambda x: x.str.strip()).eq("")).all(axis=1)
]

# === Save enriched outputs ===
ENRICHED_OUTPUT_FILE = os.path.join(RESULTS_FOLDER, SPREADSHEET_NAME + "_enriched.sav")
pyreadstat.write_sav(df_enriched, ENRICHED_OUTPUT_FILE)
print(f"✅ Enriched data saved to: {ENRICHED_OUTPUT_FILE}")

CSV_OUTPUT_FILE = os.path.join(RESULTS_FOLDER, SPREADSHEET_NAME + ".csv")
df_enriched.to_csv(CSV_OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"✅ CSV preview saved as: {CSV_OUTPUT_FILE}")
