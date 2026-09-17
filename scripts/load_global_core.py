"""
Build course_globalcore.json from the local Columbia Global Core PDF.

This version includes only the full Morningside approved-course list
and ignores all abroad/off-campus offerings.

Run from project root:
    /usr/local/bin/python3 scripts/load_global_core.py
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

from pypdf import PdfReader

PDF_PATH = Path("data/raw/global_core_requirement.pdf")
OUTPUT_PATH = Path("data/courses_globalcore.json")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_course_id(subject: str, number: str) -> str:
    return f"{subject}_{number}"


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def find_section(text: str, start_pattern: str, end_pattern: str | None) -> str:
    start_match = re.search(start_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not start_match:
        raise ValueError(f"Could not find start pattern: {start_pattern}")

    start = start_match.end()

    if end_pattern is None:
        return text[start:]

    end_match = re.search(end_pattern, text[start:], flags=re.IGNORECASE | re.DOTALL)
    if not end_match:
        raise ValueError(f"Could not find end pattern: {end_pattern}")

    end = start + end_match.start()
    return text[start:end]


def clean_title_and_notes(remainder: str):
    remainder = normalize_whitespace(remainder)
    notes = []

    while True:
        match = re.match(r"^(.*?)(\([^()]*\))\s*$", remainder)
        if not match:
            break
        remainder = match.group(1).strip()
        notes.insert(0, match.group(2).strip("() "))

    return remainder, notes


def parse_course_line(line: str):
    """
    Parses lines like:
    ANTH UN2017 Mafias and Other Dangerous Affiliations
    DNCE BC3567 DANCES OF INDIA
    CLCV UN3244 Global Histories of the Book (Effective beginning Fall 2015)
    """
    line = normalize_whitespace(line)

    match = re.match(r"^([A-Z]{3,5})\s+([A-Z]{1,2}\d{4}[A-Z]?)\s+(.*)$", line)
    if not match:
        return None

    subject, number, remainder = match.groups()
    title, notes = clean_title_and_notes(remainder)

    return {
        "subject": subject,
        "number": number,
        "title": title,
        "notes": notes
    }


def lines_from_section(section_text: str):
    return [normalize_whitespace(x) for x in section_text.splitlines() if normalize_whitespace(x)]


def build_catalog_from_pdf():
    raw_text = extract_pdf_text(PDF_PATH)
    normalized_text = re.sub(r"[ \t]+", " ", raw_text)

    morningside_section = find_section(
        normalized_text,
        r"All Approved Courses:\s*Morningside\s*Campus",
        r"All Approved Courses:\s*Offered\s*Abroad"
    )

    catalog = OrderedDict()

    current_department = None

    for line in lines_from_section(morningside_section):
        if line.startswith("Not all courses are taught each academic year"):
            continue
        if line.startswith("Below is the full list"):
            continue
        if line.startswith("Last updated on"):
            continue
        if line.startswith("Global Core Requirement"):
            continue

        # Department headers do not start with a course code
        if not re.match(r"^[A-Z]{3,5}\s+[A-Z]{1,2}\d{4}[A-Z]?\s+", line):
            current_department = line
            continue

        parsed = parse_course_line(line)
        if not parsed:
            continue

        course_id = make_course_id(parsed["subject"], parsed["number"])

        if course_id not in catalog:
            catalog[course_id] = {
                "id": course_id,
                "subject": parsed["subject"],
                "number": parsed["number"],
                "title": parsed["title"],
                "credits": None,
                "category_tags": ["global_core", "nontechnical"],
                "department_header": current_department,
                "prerequisites": [],
                "corequisites": [],
                "aliases": [],
                "notes": parsed["notes"][:]
            }
        else:
            existing = catalog[course_id]
            for note in parsed["notes"]:
                if note not in existing["notes"]:
                    existing["notes"].append(note)

    return catalog


if __name__ == "__main__":
    catalog = build_catalog_from_pdf()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(catalog)} courses to {OUTPUT_PATH}")