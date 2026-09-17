import json
from pathlib import Path

DATA_DIR = Path("data")

def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def merge_courses(base, new):
    for course_id, course in new.items():
        if course_id not in base:
            base[course_id] = course
        else:
            # Keep existing core course, but merge aliases/notes if useful
            existing = base[course_id]

            existing["aliases"] = list(set(
                existing.get("aliases", []) + course.get("aliases", [])
            ))

            existing["notes"] = list(set(
                existing.get("notes", []) + course.get("notes", [])
            ))

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