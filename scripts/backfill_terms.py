"""
Backfill `terms_offered` and `terms_checked` fields onto courses from the
caches built by scripts/fetch_offering_terms.py.

- `terms_offered`: terms the course was actually found scheduled in (e.g.
  ["Fall2026"], ["Fall2026", "Spring2027"]). Only set for courses found.
- `terms_checked`: terms that were successfully fetched for the course's
  *subject*, regardless of whether this specific course turned up. This is
  what makes an absence from `terms_offered` meaningful: if "Spring2027"
  isn't in `terms_checked`, we never actually got to look (Spring
  registration pages for many subjects, especially most of SEAS, aren't
  published yet as of this scrape) -- so absence there means "unknown,"
  not "not offered."

Run from project root:
    /usr/local/bin/python3 scripts/backfill_terms.py
"""

import json
from pathlib import Path

TERMS_CACHE_PATH = Path("data/raw/doc_of_classes_terms_offered.json")
CHECKED_CACHE_PATH = Path("data/raw/doc_of_classes_terms_checked.json")
CATALOG_FILES = [
    Path("data/courses_core.json"),
    Path("data/courses_tech_electives.json"),
    Path("data/courses_globalcore.json"),
]


def backfill_catalog(path: Path, terms_by_course: dict, checked_by_subject: dict):
    with open(path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    updated = []

    for course_id, course in catalog.items():
        checked = checked_by_subject.get(course.get("subject"))
        offered = terms_by_course.get(course_id)

        if checked is None and offered is None:
            continue

        changed = False
        if checked is not None and course.get("terms_checked") != checked:
            course["terms_checked"] = checked
            changed = True
        if offered is not None and course.get("terms_offered") != offered:
            course["terms_offered"] = offered
            changed = True

        if changed:
            updated.append(course_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with_terms = sum(1 for c in catalog.values() if c.get("terms_offered"))
    with_checked = sum(1 for c in catalog.values() if c.get("terms_checked"))

    return updated, with_terms, with_checked, len(catalog)


def main():
    with open(TERMS_CACHE_PATH, encoding="utf-8") as f:
        terms_by_course = json.load(f)
    with open(CHECKED_CACHE_PATH, encoding="utf-8") as f:
        checked_by_subject = json.load(f)

    print(f"Loaded term data for {len(terms_by_course)} courses across "
          f"{len(checked_by_subject)} checked subjects.\n")

    for path in CATALOG_FILES:
        updated, with_terms, with_checked, total = backfill_catalog(
            path, terms_by_course, checked_by_subject
        )
        print(f"{path}: backfilled {len(updated)} courses; "
              f"{with_terms}/{total} have terms_offered, "
              f"{with_checked}/{total} have terms_checked")


if __name__ == "__main__":
    main()
