"""
Backfill missing `prerequisites` values in the course catalogs from the
Columbia Engineering Bulletin PDF, which lists a "Prerequisites: ..."
sentence right after many (not all) course descriptions, e.g.:

    CHEN E4020 PROTECTN OF INDUST/INTELL PROP. 3.00 points.
    Prerequisites: (CHEN E3230) or equivalent, or instructors permission.

Only fills courses with an empty `prerequisites` list AND a bulletin entry
-- never overwrites a hand-curated list. Same schedule-based ceiling as
the credit backfill: only SEAS courses actually described in this year's
bulletin are covered at all (~40% of the catalog, going by the credit
backfill's coverage).

The prerequisite clause is free text, not a fixed format, so this is
deliberately conservative:
  - Boilerplate escape phrases ("or equivalent", "or instructor's
    permission") are stripped before parsing -- they're department
    discretion, not an enumerable alternative course.
  - If what's left names one or more course codes joined only by "and"/
    commas, that becomes the prerequisites list (AND semantics, matching
    how validator.check_prerequisites already treats the field).
  - If real course codes are joined by "or" (e.g. "CHEN E3120 or
    CHEE E3010"), that's genuine alternative-course logic the current
    schema can't express (it's AND-only) -- these are left unfilled, with
    the raw clause preserved as a note so the information isn't lost.
  - If no course code appears at all (e.g. "Instructor's permission",
    "A Python course", a topic description), same: note only, no guess.

Run from project root:
    /usr/local/bin/python3 scripts/backfill_prerequisites.py
"""

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from load_data import load_all_data, build_alias_index

PDF_PATH = Path("data/raw/Columbia_Engineering_Bulletin_2026-2027.pdf")
CATALOG_FILES = [
    Path("data/courses_core.json"),
    Path("data/courses_tech_electives.json"),
    Path("data/courses_globalcore.json"),
]
# Where a brand-new course referenced only as someone else's prerequisite
# (never itself a ChemE technical elective) gets added.
NEW_COURSES_TARGET = Path("data/courses_globalcore.json")

# Columbia retired single-letter course-number prefixes (V/C/W, roughly
# pre-2015) in favor of UN/GU/etc. A code like "MATH V1201" in the
# bulletin's prose may really mean the modern "MATH_UN1201" -- but only if
# that modern id actually exists in our catalog; if not, the safest
# assumption is that the course was renumbered enough that we can't
# reliably guess the modern id, so it's left unresolved rather than
# creating a course id nothing can ever satisfy.
LEGACY_PREFIX_PATTERN = re.compile(r"^([VCW])(\d{3,4}[A-Z]?)$")

COURSE_HEADER_PATTERN = re.compile(
    r"^([A-Z]{2,6}) ([A-Z]{0,2}\d{3,4}[A-Z]{0,2}) .+?\.\s+"
    r"[\d.]+(?:-[\d.]+)?\s*points\.\s*$",
    re.MULTILINE
)
# The prerequisite clause is confined to the same line as "Prerequisites:"
# in the source PDF -- it's sometimes period-terminated ("... or
# equivalent. ") and sometimes not (just "(MATH UN1101)" followed by a
# line break straight into the course description). Capturing past a
# newline here would swallow the description (and, further down, the
# per-section schedule listing) into the "prerequisite" text.
PREREQ_LINE_PATTERN = re.compile(r"Prerequisites?:[ \t]*([^\n]*)")
BOILERPLATE_PATTERN = re.compile(
    r";?\s*,?\s*or\s+(the\s+)?(equivalent|instructors?\s+permission)\b",
    re.IGNORECASE
)
COURSE_CODE_PATTERN = re.compile(r"\(?([A-Z]{2,6})\s+([A-Z]{0,2}\d{3,4}[A-Z]{0,2})\)?")
CONNECTOR_PATTERN = re.compile(r"\b(and|or|the)\b|[();,]", re.IGNORECASE)

# How far past a course header to look for its "Prerequisites:" clause,
# in characters -- generously past the header/points line but well short
# of the next course's description in practice.
LOOKAHEAD_CHARS = 600


def extract_bulletin_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).replace("\xa0", " ")


def parse_prereq_clause(raw: str, had_period: bool):
    """Returns (course_ids or None, status) where status is one of
    "ok", "ambiguous_or", "no_course_codes", "possibly_truncated".

    `had_period` means the source line ended in a period -- a real
    sentence boundary we can trust. Without one, the PDF's line wrap may
    have cut the clause mid-sentence (losing a trailing course code, or
    worse, an "or" that would have changed AND into OR semantics), so we
    only trust it if there's no leftover prose at all once known course
    codes and connectors are stripped out -- e.g. "(MATH UN1101)" is
    clearly complete on its own; "APMA E3101 AND APMA E4007; After the
    approval of" clearly isn't."""
    cleaned = BOILERPLATE_PATTERN.sub("", raw).strip().rstrip(";, ")

    codes = [f"{m.group(1)}_{m.group(2)}" for m in COURSE_CODE_PATTERN.finditer(cleaned)]
    if not codes:
        return None, "no_course_codes"

    remainder = COURSE_CODE_PATTERN.sub("", cleaned)

    if len(codes) > 1 and re.search(r"\bor\b", remainder, re.IGNORECASE):
        return None, "ambiguous_or"

    if not had_period:
        # a line cut off mid-clause often ends right on a dangling
        # connector ("... APMA E3101 AND") -- a strong truncation signal
        # even when the leftover-text heuristic below doesn't catch it
        if re.search(r"\b(and|or)\s*$", cleaned, re.IGNORECASE):
            return None, "possibly_truncated"

        leftover = CONNECTOR_PATTERN.sub("", remainder).strip()
        if len(leftover) > 3:
            return None, "possibly_truncated"

    return sorted(set(codes)), "ok"


def parse_bulletin_prerequisites(text: str):
    """Returns {course_id: (prereq_ids, raw_clause)} for "ok" parses, and
    {course_id: (None, raw_clause)} for clauses found but not auto-encoded
    (still useful as a note)."""
    headers = list(COURSE_HEADER_PATTERN.finditer(text))
    results = {}

    for i, header in enumerate(headers):
        subject, number = header.group(1), header.group(2)
        course_id = f"{subject}_{number}"

        window_end = min(header.end() + LOOKAHEAD_CHARS, len(text))
        if i + 1 < len(headers):
            window_end = min(window_end, headers[i + 1].start())
        window = text[header.end():window_end]

        clause_match = PREREQ_LINE_PATTERN.search(window)
        if not clause_match:
            continue

        line = clause_match.group(1).strip()
        if not line:
            continue

        # truncate at the first period on this line, if any -- the rest
        # of the line (if no period) is the whole clause
        period_index = line.find(".")
        had_period = period_index != -1
        raw_clause = line[:period_index] if had_period else line
        raw_clause = raw_clause.strip()
        if not raw_clause:
            continue

        prereq_ids, status = parse_prereq_clause(raw_clause, had_period)

        # if a course id repeats (multiple terms), keep the first
        # non-ambiguous parse we saw
        if course_id in results and results[course_id][0] is not None:
            continue

        results[course_id] = (prereq_ids, raw_clause)

    return results


def is_legacy_prefixed(code):
    _, number = code.split("_", 1)
    return bool(LEGACY_PREFIX_PATTERN.match(number))


def try_legacy_remap(code, courses, alias_index):
    subject, number = code.split("_", 1)
    match = LEGACY_PREFIX_PATTERN.match(number)
    if not match:
        return None

    digits = match.group(2)
    for new_prefix in ("UN", "GU"):
        candidate = f"{subject}_{new_prefix}{digits}"
        if candidate in courses:
            return candidate
        if candidate in alias_index:
            return alias_index[candidate]

    return None


def resolve_referenced_codes(all_codes, courses, alias_index):
    """Returns (resolved_map, unresolvable, new_bare_course_ids).
    resolved_map maps every resolvable raw code to its canonical catalog
    id (itself, its legacy-prefix remap, or itself again once added as a
    new bare entry). unresolvable codes are ones we have no safe way to
    resolve -- most often a retired V/C/W-prefixed code with no live
    equivalent in our catalog."""
    resolved_map = {}
    unresolvable = set()
    new_bare_course_ids = []

    for code in all_codes:
        if code in courses:
            resolved_map[code] = code
        elif code in alias_index:
            resolved_map[code] = alias_index[code]
        elif is_legacy_prefixed(code):
            remapped = try_legacy_remap(code, courses, alias_index)
            if remapped:
                resolved_map[code] = remapped
            else:
                unresolvable.add(code)
        else:
            # Not in our catalog, not a legacy code -- almost certainly a
            # real, current Columbia course that's simply outside the
            # scope of what we've imported so far (our catalogs only
            # cover ChemE-relevant subjects). Safe to add as a bare entry.
            resolved_map[code] = code
            new_bare_course_ids.append(code)

    return resolved_map, unresolvable, new_bare_course_ids


def add_bare_courses(course_ids):
    with open(NEW_COURSES_TARGET, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    for course_id in course_ids:
        if course_id in catalog:
            continue
        subject, number = course_id.split("_", 1)
        catalog[course_id] = {
            "id": course_id, "subject": subject, "number": number, "title": None,
            "credits": None, "category_tags": [], "prerequisites": [], "corequisites": [],
            "aliases": [], "notes": [
                "Added as a prerequisite referenced by another course "
                "(Engineering Bulletin, fetched 2026-09-18); not itself "
                "confirmed as a ChemE-relevant course."
            ]
        }

    with open(NEW_COURSES_TARGET, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")


def backfill_catalog(path: Path, bulletin_prereqs, resolved_map, unresolvable):
    with open(path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    filled = []
    noted = []

    for course_id, course in catalog.items():
        if course.get("prerequisites"):
            continue

        if course_id not in bulletin_prereqs:
            continue

        prereq_ids, raw_clause = bulletin_prereqs[course_id]

        if prereq_ids and not (set(prereq_ids) & unresolvable):
            course["prerequisites"] = sorted({resolved_map[c] for c in prereq_ids})
            course["prerequisites_source"] = "columbia_engineering_bulletin_2026_2027"
            filled.append(course_id)
        else:
            note = f"Prerequisite per bulletin (not auto-encoded): {raw_clause}."
            if note not in course.get("notes", []):
                course.setdefault("notes", []).append(note)
            noted.append(course_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with_prereqs = sum(1 for c in catalog.values() if c.get("prerequisites"))

    return filled, noted, with_prereqs, len(catalog)


def main():
    text = extract_bulletin_text(PDF_PATH)
    bulletin_prereqs = parse_bulletin_prerequisites(text)

    ok_results = {k: v for k, v in bulletin_prereqs.items() if v[0] is not None}
    print(f"Parsed {len(bulletin_prereqs)} course prerequisite clauses from "
          f"bulletin ({len(ok_results)} auto-encodable, "
          f"{len(bulletin_prereqs) - len(ok_results)} left as notes only).\n")

    courses, *_ = load_all_data()
    alias_index = build_alias_index(courses)
    all_codes = {code for ids, _ in ok_results.values() for code in ids}

    resolved_map, unresolvable, new_bare_course_ids = resolve_referenced_codes(
        all_codes, courses, alias_index
    )
    print(f"Referenced course codes: {len(all_codes)} total, "
          f"{len(new_bare_course_ids)} added as new bare entries, "
          f"{len(unresolvable)} unresolvable (left as notes only).\n")

    if new_bare_course_ids:
        add_bare_courses(new_bare_course_ids)

    for path in CATALOG_FILES:
        filled, noted, with_prereqs, total = backfill_catalog(
            path, bulletin_prereqs, resolved_map, unresolvable
        )
        print(f"{path}: filled {len(filled)} course(s), noted "
              f"{len(noted)} unencodable clause(s); "
              f"{with_prereqs}/{total} now have prerequisites")


if __name__ == "__main__":
    main()
