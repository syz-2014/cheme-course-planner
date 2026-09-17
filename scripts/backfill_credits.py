"""
Backfill missing `credits` values in the course catalogs from two sources,
in priority order:

1. The Columbia Engineering Bulletin PDF (SEAS course descriptions):
    CHEN E3899 Research Training. 0.00 points.
    APMA E4903 SEM-PROBLEMS IN APPLIED MATH. 3.00-4.00 points.
   (note: the PDF uses U+00A0 non-breaking spaces between the code and title)

2. data/raw/doc_of_classes_credits.json, a cache built by
   scripts/fetch_doc_credits.py from Columbia's public Directory of Classes
   (covers non-SEAS subjects the Engineering Bulletin doesn't describe).

Both sources are schedule-based: they only cover courses actually offered
in the current/upcoming terms, so plenty of catalog courses (especially
Global Core courses not taught this year) won't be found in either. Only
fills in courses that are missing credits AND found in a source -- this
script does not guess at credit values.

For variable-credit courses (e.g. undergraduate research), the minimum of
the range is stored as `credits` and the full range is recorded in `notes`,
so totals stay conservative and students can raise it via the app's credit
override if they take more.

Run from project root:
    /usr/local/bin/python3 scripts/backfill_credits.py
"""

import json
import re
from pathlib import Path

from pypdf import PdfReader

PDF_PATH = Path("data/raw/Columbia_Engineering_Bulletin_2026-2027.pdf")
DOC_CREDITS_CACHE_PATH = Path("data/raw/doc_of_classes_credits.json")
CATALOG_FILES = [
    Path("data/courses_core.json"),
    Path("data/courses_tech_electives.json"),
    Path("data/courses_globalcore.json"),
]

COURSE_CREDIT_PATTERN = re.compile(
    r"^([A-Z]{2,6}) ([A-Z]{0,2}\d{3,4}[A-Z]{0,2}) .+?\.\s+"
    r"([\d.]+)(?:-([\d.]+))?\s*points\.\s*$",
    re.MULTILINE
)


def extract_bulletin_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).replace("\xa0", " ")


def parse_bulletin_credits(text: str):
    """Returns {course_id: (min_credits, max_credits)}. Skips course ids
    that appear with inconsistent credit values across the bulletin, since
    that suggests two distinct courses shared a raw code by parsing error."""
    found = {}
    conflicting = set()

    for match in COURSE_CREDIT_PATTERN.finditer(text):
        subject, number, lo, hi = match.groups()
        course_id = f"{subject}_{number}"
        lo = float(lo)
        hi = float(hi) if hi else lo

        if course_id in found and found[course_id] != (lo, hi):
            conflicting.add(course_id)
            continue

        found[course_id] = (lo, hi)

    for course_id in conflicting:
        found.pop(course_id, None)

    return found


def load_doc_credits_cache(path: Path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {course_id: tuple(vals) for course_id, vals in raw.items()}


def backfill_catalog(path: Path, sources):
    """sources: list of (source_name, {course_id: (lo, hi)}), applied in
    order -- the first source with a match wins for each course."""
    with open(path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    updated = []

    for course_id, course in catalog.items():
        if course.get("credits") is not None:
            continue

        for source_name, credits_map in sources:
            if course_id not in credits_map:
                continue

            lo, hi = credits_map[course_id]
            course["credits"] = lo
            course["credits_source"] = source_name

            if lo != hi:
                note = (
                    f"Variable credit course ({lo:.2f}-{hi:.2f} points per "
                    f"{source_name}); minimum applied by default, adjust "
                    "via credit override if you take more."
                )
                if note not in course.get("notes", []):
                    course.setdefault("notes", []).append(note)

            updated.append(course_id)
            break

    with open(path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    still_missing = sum(1 for c in catalog.values() if c.get("credits") is None)

    return updated, still_missing, len(catalog)


def main():
    text = extract_bulletin_text(PDF_PATH)
    bulletin_credits = parse_bulletin_credits(text)
    doc_credits = load_doc_credits_cache(DOC_CREDITS_CACHE_PATH)

    print(f"Parsed {len(bulletin_credits)} course credit entries from bulletin.")
    print(f"Loaded {len(doc_credits)} course credit entries from "
          f"Directory of Classes cache.\n")

    sources = [
        ("columbia_engineering_bulletin_2026_2027", bulletin_credits),
        ("columbia_directory_of_classes_2026_2027", doc_credits),
    ]

    for path in CATALOG_FILES:
        updated, still_missing, total = backfill_catalog(path, sources)
        print(f"{path}: backfilled {len(updated)} courses; "
              f"{still_missing}/{total} still missing credits")


if __name__ == "__main__":
    main()
