"""
Fetch course credit ("points") values from Columbia's public Directory of
Classes (doc.sis.columbia.edu) for a given list of subject codes, and cache
the results to data/raw/doc_of_classes_credits.json.

The Directory of Classes covers every Columbia school (not just SEAS), so
it's the source for credits on Global Core and non-SEAS technical elective
courses that the Engineering Bulletin doesn't describe. It only lists
courses actually offered in the current/upcoming terms, so it will not
cover everything either.

Run from project root:
    /usr/local/bin/python3 scripts/fetch_doc_credits.py
"""

import json
import re
import time
from pathlib import Path

import requests

BASE_URL = "https://doc.sis.columbia.edu/subj/{subject}/_{term}.html"
OUTPUT_PATH = Path("data/raw/doc_of_classes_credits.json")

# Preferred term per subject is resolved by the caller (build_fetch_plan.py
# logic lives in the backfill orchestration script); this module just needs
# subject -> term to fetch.

HEADER_PATTERN = re.compile(
    r"<th colspan=2>(?:Fall|Spring|Summer)\s+\d{4}\s+.*?\s"
    r"([A-Z]{1,2}\d{3,4}[A-Z]?)(?:\s*\([^)]*\))?<br>",
    re.IGNORECASE
)
POINTS_PATTERN = re.compile(r"Points:</dt>\s*<dd>([\d.]+)(?:-([\d.]+))?</dd>")


def parse_subject_page(html: str):
    """Returns {number: (min_credits, max_credits)} for one subject page."""
    chunks = re.split(r"(?=<th colspan=2>)", html)
    found = {}

    for chunk in chunks:
        header_match = HEADER_PATTERN.search(chunk)
        if not header_match:
            continue

        points_match = POINTS_PATTERN.search(chunk)
        if not points_match:
            continue

        number = header_match.group(1).upper()
        lo = float(points_match.group(1))
        hi = float(points_match.group(2)) if points_match.group(2) else lo

        if number in found and found[number] != (lo, hi):
            # inconsistent across sections (e.g. lecture vs. lab pairing
            # sharing a header) -- skip rather than guess
            found[number] = None
            continue

        found[number] = (lo, hi)

    return {num: val for num, val in found.items() if val is not None}


def fetch_subject_credits(subject: str, term: str, session: requests.Session):
    url = BASE_URL.format(subject=subject, term=term)
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return parse_subject_page(resp.text)


def fetch_all(subject_terms: dict, delay_seconds: float = 0.5):
    """subject_terms: {subject_code: term_string}. Returns
    {course_id: (min_credits, max_credits)}."""
    session = requests.Session()
    session.headers.update({"User-Agent": "ChemE-Course-Planner-data-pipeline"})

    all_credits = {}
    failures = []

    for i, (subject, term) in enumerate(sorted(subject_terms.items())):
        try:
            found = fetch_subject_credits(subject, term, session)
        except requests.RequestException as e:
            failures.append((subject, str(e)))
            continue

        for number, credits in found.items():
            all_credits[f"{subject}_{number}"] = credits

        if delay_seconds:
            time.sleep(delay_seconds)

    return all_credits, failures


def main(subject_terms: dict):
    all_credits, failures = fetch_all(subject_terms)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {cid: list(vals) for cid, vals in sorted(all_credits.items())},
            f, indent=2
        )
        f.write("\n")

    print(f"Fetched {len(all_credits)} course credit entries "
          f"from {len(subject_terms)} subjects.")
    if failures:
        print(f"{len(failures)} subject page(s) failed to fetch:")
        for subject, error in failures:
            print(f"  {subject}: {error}")


if __name__ == "__main__":
    import sys
    subject_terms_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not subject_terms_path:
        raise SystemExit(
            "Usage: fetch_doc_credits.py <subject_terms.json>\n"
            "subject_terms.json maps subject code -> term string, e.g. "
            '{"HIST": "Fall2026"}'
        )
    with open(subject_terms_path) as f:
        subject_terms = json.load(f)
    main(subject_terms)
