"""
Fetch which term(s) (Fall2026, Spring2027) each course is scheduled in from
Columbia's public Directory of Classes, and cache the results to
data/raw/doc_of_classes_terms_offered.json.

Unlike scripts/fetch_doc_credits.py (which only needs one term page per
subject to find a credit value), this needs BOTH the Fall and Spring page
per subject to know which term(s) a course runs in.

This is schedule-based, same caveat as the credit backfill: a course only
shows up here if it's actually being taught in AY2026-2027. A course not
found in either term isn't necessarily off-cycle forever -- it just isn't
scheduled this particular year.

Run from project root:
    /usr/local/bin/python3 scripts/fetch_offering_terms.py <subject_terms.json>

subject_terms.json maps subject code -> list of term strings to check, e.g.
    {"HIST": ["Fall2026", "Spring2027"]}
"""

import json
import re
import time
from pathlib import Path

import requests

BASE_URL = "https://doc.sis.columbia.edu/subj/{subject}/_{term}.html"
OUTPUT_PATH = Path("data/raw/doc_of_classes_terms_offered.json")
CHECKED_OUTPUT_PATH = Path("data/raw/doc_of_classes_terms_checked.json")

HEADER_PATTERN = re.compile(
    r"<th colspan=2>(?:Fall|Spring|Summer)\s+\d{4}\s+.*?\s"
    r"([A-Z]{1,2}\d{3,4}[A-Z]?)(?:\s*\([^)]*\))?<br>",
    re.IGNORECASE
)


def parse_subject_page_numbers(html: str):
    """Returns the set of course numbers found on one subject/term page."""
    return {m.group(1).upper() for m in HEADER_PATTERN.finditer(html)}


def fetch_subject_term_numbers(subject: str, term: str, session: requests.Session):
    url = BASE_URL.format(subject=subject, term=term)
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return parse_subject_page_numbers(resp.text)


def fetch_all(subject_terms: dict, delay_seconds: float = 0.3):
    """subject_terms: {subject_code: [term_string, ...]}. Returns
    (course_terms, subject_checked_terms, failures):
      - course_terms: {course_id: sorted [term, ...]} -- terms a course was
        actually found scheduled in.
      - subject_checked_terms: {subject: sorted [term, ...]} -- terms that
        were successfully fetched for that subject, i.e. real evidence a
        course's *absence* from a term is meaningful rather than just
        unpublished (e.g. Spring registration pages often aren't live yet
        when this is run in the fall)."""
    session = requests.Session()
    session.headers.update({"User-Agent": "ChemE-Course-Planner-data-pipeline"})

    course_terms = {}
    subject_checked_terms = {}
    failures = []

    for subject, terms in sorted(subject_terms.items()):
        for term in terms:
            try:
                numbers = fetch_subject_term_numbers(subject, term, session)
            except requests.RequestException as e:
                failures.append((subject, term, str(e)))
                continue

            subject_checked_terms.setdefault(subject, set()).add(term)

            for number in numbers:
                course_id = f"{subject}_{number}"
                course_terms.setdefault(course_id, set()).add(term)

            if delay_seconds:
                time.sleep(delay_seconds)

    course_terms = {cid: sorted(terms) for cid, terms in course_terms.items()}
    subject_checked_terms = {
        subj: sorted(terms) for subj, terms in subject_checked_terms.items()
    }

    return course_terms, subject_checked_terms, failures


def main(subject_terms: dict):
    course_terms, subject_checked_terms, failures = fetch_all(subject_terms)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(course_terms.items())), f, indent=2)
        f.write("\n")

    with open(CHECKED_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(subject_checked_terms.items())), f, indent=2)
        f.write("\n")

    print(f"Fetched term data for {len(course_terms)} courses "
          f"across {len(subject_terms)} subjects.")
    print(f"{len(subject_checked_terms)} subjects had at least one term "
          "page successfully checked.")
    if failures:
        print(f"{len(failures)} subject/term page(s) failed to fetch:")
        for subject, term, error in failures:
            print(f"  {subject} {term}: {error}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: fetch_offering_terms.py <subject_terms.json>\n"
            "subject_terms.json maps subject code -> [term, ...], e.g. "
            '{"HIST": ["Fall2026", "Spring2027"]}'
        )
    with open(sys.argv[1]) as f:
        subject_terms = json.load(f)
    main(subject_terms)
