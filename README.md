# SPSS_DATA_ENRICHER

## 📝 Google Sheets to SPSS (.sav) Converter with Random Data Augmentation

This script reads survey data from a **Google Sheets spreadsheet**, cleans and processes it, and exports it as an **SPSS `.sav` file** using `pyreadstat`. Optionally, it can also **generate realistic random survey rows** for data enrichment.

---
## 🧩 Overview

1. **Create a Google Form** with your survey questions.
2. **Link the form to a Google Sheet** (this is automatic in Google Forms).
3. This script:
   - Authenticates with Google Sheets
   - Cleans and normalizes the data
   - Exports it to `.sav` (SPSS format)
   - Optionally adds random synthetic rows for testing or simulation


## 📦 Requirements

Install the required Python packages:

```bash
pip install gspread google-auth pandas pyreadstat unidecode
```

## ⚙️ Configuration

Edit the top of the script to customize these settings:
```python
SPREADSHEET_NAME = "Worksheet (Responses)"
WORKSHEET_INDEX = 0
JSON_KEY_FILE = "credentials.json"
OUTPUT_SAV_FILE = "survey_data.sav"
```
> 🔐 The `credentials.json` is a **Google service account** key file.  
> Follow [this guide](https://gspread.readthedocs.io/en/latest/oauth2.html) to create and download it.

## 🧠 How It Works

### ✅ Step 1: Authenticate and Fetch Data

-   Authenticates with Google Sheets using your service account
    
-   Reads all rows from the specified worksheet
    

### ✅ Step 2: Clean and Normalize

-   Automatically detects the header row
    
-   Removes timestamp-like columns
    
-   Cleans column names to be SPSS-compatible (alphanumeric, unique, max 64 characters)
    

### ✅ Step 3: Export to SPSS

-   Creates a `.sav` file using `pyreadstat`
    

### ✅ Step 4: (Optional) Enrich the Data

-   Prompts the user to add randomly generated rows
    
-   Auto-detects value ranges (numeric) and answer options (categorical)
    
-   Appends generated data and saves a new `.sav` file and a `.csv` preview

## 🚀 How to Run
```bash
python main.py
```
Follow the on-screen prompts to add fake survey data optionally.

## 📂 Output Files

-   `survey_data.sav`: Original cleaned data
    
-   `survey_data_enriched.sav`: File with added fake rows (if selected)
    
-   `converted.csv`: A CSV version for preview
    


## ✨ Notes

-   Works with multi-language headers (converts to ASCII with `unidecode`)
    
-   Ensures compatibility with SPSS by cleaning field names
    
-   Random data generation helps with prototyping or testing statistical models

## 🛡️ Disclaimer

Use synthetic data only for testing or anonymized datasets. Be cautious when manipulating real user data, especially with auto-generated records.
