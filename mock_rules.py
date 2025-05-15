import random
import pandas as pd
import re
import unidecode


def analyze_metadata(df):
    survey_questions = {}
    column_data_types = {}

    for col in df.columns:
        unique_vals = df[col].dropna().unique()
        if len(unique_vals) == 0:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            column_data_types[col] = "numeric"
            min_val, max_val = df[col].min(), df[col].max()
            if pd.isnull(min_val) or pd.isnull(max_val):
                continue
            survey_questions[col] = (min_val, max_val)
        else:
            column_data_types[col] = "categorical"
            survey_questions[col] = list(unique_vals)

    return survey_questions, column_data_types


def clean_column(name):
    name = unidecode.unidecode(name)
    name = re.sub(r"\W+", "_", name)
    if not name or not name[0].isalpha():
        name = "v_" + name
    return name[:64]


def generate_random_answers(survey_questions, column_data_types, columns):
    row = {}
    for col in columns:
        if col not in column_data_types:
            row[col] = ""
            continue

        if column_data_types[col] == "numeric":
            min_val, max_val = survey_questions[col]
            if isinstance(min_val, float) or isinstance(max_val, float):
                row[col] = round(random.uniform(min_val, max_val), 2)
            else:
                row[col] = random.randint(min_val, max_val)
        else:
            row[col] = random.choice(survey_questions[col])

    return row


def generate_mock_data(df, meta, num_rows):
    columns = list(meta.column_names)
    survey_questions, column_data_types = analyze_metadata(df)

    mock_data = [
        generate_random_answers(survey_questions, column_data_types, columns)
        for _ in range(num_rows)
    ]
    random_df = pd.DataFrame(mock_data, columns=columns)

    enriched_df = pd.concat([df, random_df], ignore_index=True)
    enriched_df = enriched_df[columns]
    enriched_df = enriched_df.dropna(axis=1, how="all")

    return enriched_df
