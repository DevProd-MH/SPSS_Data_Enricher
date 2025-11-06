# extract_form_questions.py
import re
import json
import csv
from bs4 import BeautifulSoup

# Load the saved Google Form HTML source
with open("source.txt", "r", encoding="utf-8") as f:
    html_txt = f.read()

soup = BeautifulSoup(html_txt, "html.parser")

# Primary question block class; fallback available
qblocks = soup.find_all("div", class_="Qr7Oae")
if not qblocks:
    qblocks = soup.find_all("div", class_="geS5n")

def extract_first_array(s):
    if not s:
        return None
    start = s.find('[')
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(s[start:], start):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def extract_from_parsed(obj):
    entry_ids = []
    options = []
    # entries are usually in obj[4] as [[entryid, [[opt1,...], [opt2,...]]], ...]
    if isinstance(obj, list) and len(obj) > 4:
        entries_block = obj[4]
        if isinstance(entries_block, list):
            for ent in entries_block:
                if isinstance(ent, list) and len(ent) >= 2:
                    eid = ent[0]
                    entry_ids.append(f"entry.{eid}_sentinel")
                    opts = ent[1]
                    if isinstance(opts, list):
                        for op in opts:
                            if isinstance(op, list) and len(op) > 0:
                                val = op[0]
                                if isinstance(val, str):
                                    options.append(val.strip())
                                else:
                                    options.append(str(val))
    return entry_ids, options

def dom_fallback(qblock):
    entries = []
    answers = []
    # collect input names
    for inp in qblock.find_all(["input","textarea","select"], {"name": re.compile(r"^entry\.\d+")}):
        name = inp.get("name")
        if name and name not in entries:
            entries.append(name)
    # collect visible option texts via attributes
    for el in qblock.find_all(lambda tag: tag.has_attr('data-value') or tag.has_attr('aria-label')):
        val = el.get('data-value') or el.get('aria-label')
        if val and val.strip() and val.strip() not in answers:
            answers.append(val.strip())
    # collect span/div based visible texts (class heuristics)
    for span in qblock.find_all("span"):
        cls = " ".join(span.get("class") or [])
        if re.search(r'\baDTYNe\b|\bsnByac\b|\bOvPDhc\b|\bR2wJe\b', cls):
            txt = span.get_text(strip=True)
            if txt and txt not in answers:
                answers.append(txt)
    for div in qblock.find_all("div"):
        cls = " ".join(div.get("class") or [])
        if re.search(r'\bOd2TWd\b|\bYEVVod\b|\blLfZXe\b|\bHoXoMd\b', cls):
            txt = div.get_text(strip=True)
            if txt and txt not in answers:
                answers.append(txt)
    return entries, answers

questions_data = []

for qb in qblocks:
    # question text
    qtext = ""
    h = qb.find("div", {"role": "heading"})
    if h and h.get_text(strip=True):
        qtext = h.get_text(strip=True)
    else:
        span = qb.find(class_="M7eMe")
        if span and span.get_text(strip=True):
            qtext = span.get_text(strip=True)
    if not qtext:
        continue

    dp_elem = qb.find(attrs={'data-params': True})
    entries = []
    answers = []
    if dp_elem:
        dp = dp_elem.get('data-params')
        arr = extract_first_array(dp)
        if arr:
            try:
                parsed = json.loads(arr)
                ent_ids, opts = extract_from_parsed(parsed)
                entries = ent_ids
                answers = opts
            except Exception:
                entries, answers = dom_fallback(qb)
        else:
            entries, answers = dom_fallback(qb)
    else:
        entries, answers = dom_fallback(qb)

    # If answers missing but inputs exist -> text/number question
    if not answers and entries:
        answers = ["(نص حر / رقم)"]

    # Clean answers: remove duplicates and non-options like 'Required question' or duplicate question text
    cleaned = []
    for a in answers:
        a_str = a.strip()
        if not a_str:
            continue
        if a_str.lower().startswith("required") or a_str == qtext or a_str == (qtext + "*"):
            continue
        if a_str not in cleaned:
            cleaned.append(a_str)
    answers = cleaned if cleaned else ["(نص حر / رقم)"]

    # Remove glued concatenations: skip any answer that contains two or more other answers as substrings
    final_answers = []
    for a in answers:
        count = sum(1 for b in answers if b != a and b in a)
        if count >= 2:
            continue
        final_answers.append(a)
    if not final_answers:
        final_answers = ["(نص حر / رقم)"]

    # Ensure we have at least one entry id if possible (look inside block)
    if not entries:
        for inp in qb.find_all(["input","textarea"], {"name": re.compile(r"^entry\.\d+")}):
            name = inp.get("name")
            if name and name not in entries:
                entries.append(name)
    # fallback: extract a numeric id from raw data-params string
    if not entries and dp_elem:
        dp_raw = dp_elem.get('data-params') or ""
        m = re.search(r'\[\s*([0-9]{6,12})\s*,', dp_raw)
        if m:
            entries.append(f"entry.{m.group(1)}_sentinel")

    questions_data.append({
        "entries": entries,
        "question": qtext,
        "answers": final_answers
    })

# Save JSON
with open("form_questions.json", "w", encoding="utf-8") as f:
    json.dump(questions_data, f, ensure_ascii=False, indent=2)

# Save CSV for review
with open("form_questions.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Entry IDs", "Question", "Answers"])
    for q in questions_data:
        writer.writerow([";".join(q["entries"]), q["question"], ";".join(q["answers"])])

print(f"Extracted {len(questions_data)} questions. Saved to form_questions.json and form_questions.csv")
