"""
Build courses_technical_electives.json from the ChemE electives spreadsheet.

Run from project root:
    /usr/local/bin/python3 scripts/load_technical_electives.py
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

import openpyxl

INPUT_PATH = Path("data/raw/Electives Course List-New Study Plan.xlsx")
OUTPUT_PATH = Path("data/courses_tech_electives.json")


SEAS_SUBJECTS = {
    "APAM", "APMA", "BMCH", "BMEN", "CHAP", "CHEE", "CHEN",
    "CIEN", "CSOR", "EAEE", "ECBM", "EECS", "ELEN", "IEOR",
    "MECE", "MSAE"
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_course_code(raw):
    """
    Convert messy spreadsheet course codes into a canonical form.

    Examples:
    CHEN E4130 -> (CHEN, E4130, CHEN_E4130)
    STAT GU4001 -> (STAT, GU4001, STAT_GU4001)
    BIOL W2501 -> (BIOL, W2501, BIOL_W2501)
    EEEB UN3005/3015 -> (EEEB, UN3005_3015, EEEB_UN3005_3015)
    """
    if raw is None:
        return None

    text = normalize_whitespace(raw).upper()
    text = text.replace(".", "")
    text = re.sub(r"\([^)]*\)", "", text).strip()

    # collapse internal whitespace
    text = re.sub(r"\s+", " ", text)

    # subject + level+number
    m = re.match(r"^([A-Z]{3,5})\s+([A-Z]{1,2})\s*([0-9]{4}(?:/[0-9]{4})?)$", text)
    if m:
        subject, prefix, number = m.groups()
        number = number.replace("/", "_")
        number_full = f"{prefix}{number}"
        course_id = f"{subject}_{number_full}"
        return subject, number_full, course_id

    # subject glued to level+number
    m = re.match(r"^([A-Z]{3,5})\s*([A-Z]{1,2}[0-9]{4}(?:/[0-9]{4})?)$", text)
    if m:
        subject, number_full = m.groups()
        number_full = number_full.replace("/", "_")
        course_id = f"{subject}_{number_full}"
        return subject, number_full, course_id

    # subject + plain number, assume engineering E-number if SEAS subject
    m = re.match(r"^([A-Z]{3,5})\s+([0-9]{4}(?:/[0-9]{4})?)$", text)
    if m:
        subject, number = m.groups()
        number = number.replace("/", "_")
        if subject in SEAS_SUBJECTS:
            number_full = f"E{number}"
        else:
            number_full = number
        course_id = f"{subject}_{number_full}"
        return subject, number_full, course_id

    return None


def blank_course(subject, number, course_id, title):
    return {
        "id": course_id,
        "subject": subject,
        "number": number,
        "title": normalize_whitespace(title) if title else None,
        "credits": None,
        "category_tags": [],
        "prerequisites": [],
        "corequisites": [],
        "aliases": [],
        "notes": []
    }


def add_tag(course, tag):
    if tag not in course["category_tags"]:
        course["category_tags"].append(tag)


def add_note(course, note):
    if note is None:
        return
    note = normalize_whitespace(note)
    if note and note not in course["notes"]:
        course["notes"].append(note)


def get_or_create(catalog, raw_code, raw_title):
    parsed = normalize_course_code(raw_code)
    if not parsed:
        return None

    subject, number, course_id = parsed

    if course_id not in catalog:
        catalog[course_id] = blank_course(subject, number, course_id, raw_title)
    else:
        if not catalog[course_id]["title"] and raw_title:
            catalog[course_id]["title"] = normalize_whitespace(raw_title)

    return catalog[course_id]


def parse_yes(value):
    return normalize_whitespace(value).upper() == "X"


def load_workbook(path: Path):
    return openpyxl.load_workbook(path, data_only=True)


def process_chhen_bucket_sheet(ws, catalog, bucket_tag):
    """
    Sheets:
    - CHEN - Thermo
    - CHEN - Transport
    Columns expected:
    course code | title | note
    """
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row or row[0] is None:
            continue

        course = get_or_create(catalog, row[0], row[1] if len(row) > 1 else None)
        if not course:
            continue

        add_tag(course, "technical_elective")
        add_tag(course, bucket_tag)

        # CHEN thermo/transport courses are also engineering tech electives
        if course["subject"] in {"CHEN", "CHEE", "CHAP", "BMCH", "BMEN", "MECE", "MSAE"}:
            add_tag(course, "engineering_tech_elective")

        if len(row) > 2:
            add_note(course, row[2])


def process_general_sheet(ws, catalog, mode):
    """
    Handles the larger classification sheets.

    mode='chen_classes'
    Expected spreadsheet meaning:
      course | title | seas tech | eng tech | adv stem | nat sci lab | does not count | ... | note

    mode='non_chen_seas'
    Expected:
      course | title | eng tech | adv stem | nat sci lab | math elective | does not count | ... | note

    mode='non_seas'
    Expected:
      course | title | misc bucket | eng tech | adv stem | nat sci lab | math elective | does not count | ... | note
    """
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row or row[0] is None:
            continue

        course = get_or_create(catalog, row[0], row[1] if len(row) > 1 else None)
        if not course:
            continue

        if mode == "chen_classes":
            seas_tech = parse_yes(row[2]) if len(row) > 2 else False
            eng_tech = parse_yes(row[3]) if len(row) > 3 else False
            adv_stem = parse_yes(row[4]) if len(row) > 4 else False
            nat_lab = parse_yes(row[5]) if len(row) > 5 else False
            does_not_count = row[6] if len(row) > 6 else None
            note = row[8] if len(row) > 8 else None

            if seas_tech or eng_tech or adv_stem:
                add_tag(course, "technical_elective")
            if eng_tech:
                add_tag(course, "engineering_tech_elective")
            if adv_stem:
                add_tag(course, "advanced_stem_tech_elective")
            if nat_lab:
                add_tag(course, "natural_science_lab_option")

            add_note(course, does_not_count)
            add_note(course, note)

        elif mode == "non_chen_seas":
            eng_tech = parse_yes(row[2]) if len(row) > 2 else False
            adv_stem = parse_yes(row[3]) if len(row) > 3 else False
            nat_lab = parse_yes(row[4]) if len(row) > 4 else False
            math_el = parse_yes(row[5]) if len(row) > 5 else False
            does_not_count = row[6] if len(row) > 6 else None
            note = row[8] if len(row) > 8 else None

            if eng_tech or adv_stem:
                add_tag(course, "technical_elective")
            if eng_tech:
                add_tag(course, "engineering_tech_elective")
            if adv_stem:
                add_tag(course, "advanced_stem_tech_elective")
            if nat_lab:
                add_tag(course, "natural_science_lab_option")
            if math_el:
                add_tag(course, "math_elective")

            add_note(course, does_not_count)
            add_note(course, note)

        elif mode == "non_seas":
            eng_tech = parse_yes(row[3]) if len(row) > 3 else False
            adv_stem = parse_yes(row[4]) if len(row) > 4 else False
            nat_lab = parse_yes(row[5]) if len(row) > 5 else False
            math_el = parse_yes(row[6]) if len(row) > 6 else False
            does_not_count = row[7] if len(row) > 7 else None
            note = row[9] if len(row) > 9 else None

            if eng_tech or adv_stem:
                add_tag(course, "technical_elective")
            if eng_tech:
                add_tag(course, "engineering_tech_elective")
            if adv_stem:
                add_tag(course, "advanced_stem_tech_elective")
            if nat_lab:
                add_tag(course, "natural_science_lab_option")
            if math_el:
                add_tag(course, "math_elective")

            add_note(course, does_not_count)
            add_note(course, note)


def cleanup_catalog(catalog):
    cleaned = OrderedDict()

    for course_id in sorted(catalog.keys()):
        course = catalog[course_id]

        # only keep actual technical electives in this file
        if "technical_elective" not in course["category_tags"] and \
           "thermo_elective" not in course["category_tags"] and \
           "transport_elective" not in course["category_tags"] and \
           "engineering_tech_elective" not in course["category_tags"] and \
           "advanced_stem_tech_elective" not in course["category_tags"]:
            continue

        # dedupe and sort tags
        course["category_tags"] = sorted(set(course["category_tags"]))

        # remove empty title placeholders if needed
        if course["title"]:
            course["title"] = normalize_whitespace(course["title"])

        cleaned[course_id] = course

    return cleaned


def build_technical_electives():
    wb = load_workbook(INPUT_PATH)
    catalog = {}

    # These sheet names should match your workbook
    if "CHEN - Thermo" in wb.sheetnames:
        process_chhen_bucket_sheet(wb["CHEN - Thermo"], catalog, "thermo_elective")

    if "CHEN - Transport" in wb.sheetnames:
        process_chhen_bucket_sheet(wb["CHEN - Transport"], catalog, "transport_elective")

    if "CHEN classes" in wb.sheetnames:
        process_general_sheet(wb["CHEN classes"], catalog, "chen_classes")

    if "non-CHEN SEAS" in wb.sheetnames:
        process_general_sheet(wb["non-CHEN SEAS"], catalog, "non_chen_seas")

    if "non SEAS" in wb.sheetnames:
        process_general_sheet(wb["non SEAS"], catalog, "non_seas")

    return cleanup_catalog(catalog)


if __name__ == "__main__":
    catalog = build_technical_electives()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(catalog)} courses to {OUTPUT_PATH}")