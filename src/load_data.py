import json
from pathlib import Path

DATA_DIR = Path("data")

def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def build_alias_index(courses):
    index = {}
    for course_id, course in courses.items():
        for alias in course.get("aliases", []):
            index[alias] = course_id
    return index

def merge_courses(base, new):
    # An incoming id may itself be a known alias of an already-loaded
    # course (e.g. the electives spreadsheet parses a legacy code like
    # "CHEM 3085" into its own "CHEM_3085" entry, when it's really the
    # same course as the canonical "CHEM_UN3085" already loaded from
    # courses_core.json, which records "CHEM_3085" as an alias). Without
    # this, the two land as separate catalog entries for the same real
    # course -- one with real credits/prereqs, one without -- and a
    # student could select both and silently double-count it.
    alias_index = build_alias_index(base)

    for course_id, course in new.items():
        canonical_id = course_id
        if course_id not in base and course_id in alias_index:
            canonical_id = alias_index[course_id]

        if canonical_id not in base:
            base[canonical_id] = course
            continue

        # Keep existing course's own fields, but merge in anything useful
        # from the incoming duplicate/alias entry
        existing = base[canonical_id]

        incoming_aliases = course.get("aliases", [])
        if course_id != canonical_id:
            incoming_aliases = incoming_aliases + [course_id]

        existing["aliases"] = sorted(set(
            existing.get("aliases", []) + incoming_aliases
        ))

        existing["notes"] = sorted(set(
            existing.get("notes", []) + course.get("notes", [])
        ))

        existing["category_tags"] = sorted(set(
            existing.get("category_tags", []) + course.get("category_tags", [])
        ))

        if existing.get("credits") is None and course.get("credits") is not None:
            existing["credits"] = course["credits"]

        if not existing.get("prerequisites") and course.get("prerequisites"):
            existing["prerequisites"] = course["prerequisites"]

    return base

def load_all_data():
    courses = {}

    # Load core first and protect it
    courses = merge_courses(courses, load_json("courses_core.json"))
    courses = merge_courses(courses, load_json("courses_tech_electives.json"))
    courses = merge_courses(courses, load_json("courses_globalcore.json"))

    requirements = load_json("requirements.json")
    template = load_json("template.json")
    nontech_rules = load_json("nontech_rules.json")

    return courses, requirements, template, nontech_rules