"""
One-time data entry: adds Columbia ChemE's 4 undergraduate elective
specializations (informally "concentrations") and any course catalog
entries they reference that weren't already present.

Source: the Chemical Engineering (BS) bulletin page, "Elective
Specializations" section --
https://bulletin.columbia.edu/columbia-engineering/academic-departments-programs/chemical-engineering/undergraduate-programs/chemical-engineering-bs/#curriculumtext
(fetched 2026-09-18).

Per the bulletin: "To fulfill a specialization, the student must complete
any combination of four courses (12 points total) from a list of technical
elective courses that have been approved by the department to count
towards that specialization. Courses taken P/F do not count towards
specializations." -- the P/F exclusion isn't enforced here since the app
doesn't track grades at all yet.

Writes data/concentrations.json and adds any missing referenced courses to
data/courses_tech_electives.json (tagged "technical_elective" per the
bulletin's framing, but NOT sub-classified into engineering/advanced-STEM
tech elective buckets -- that needs advisor verification, same as any
other course in this catalog).

Run from project root:
    /usr/local/bin/python3 scripts/add_specialization_data.py
"""

import json
from pathlib import Path

CONCENTRATIONS_PATH = Path("data/concentrations.json")
TECH_ELECTIVES_PATH = Path("data/courses_tech_electives.json")

CONCENTRATIONS = {
    "advanced_materials": {
        "id": "advanced_materials",
        "name": "Advanced Materials",
        "type": "choose_n_courses",
        "courses_required": 4,
        "credits_required": 12,
        "description": (
            "Understanding of the fundamentals and technological "
            "challenges associated with the design of new materials, "
            "including soft materials, materials for electrochemical "
            "energy storage, and biomaterials."
        ),
        "courses": [
            "CHEN_E3900", "APCH_E4080", "CHEN_E4620", "CHEN_E4630",
            "CHEN_E4650", "CHEN_E4860", "CHEN_E4665", "CHEN_E4870",
            "CHEN_E4880", "CHEN_E4910", "MSAE_E3010", "MSAE_E4090",
            "MSAE_E4206", "MSAE_E4260"
        ],
        "notes": [
            "Courses taken P/F do not count towards specializations "
            "(not enforced here -- grades aren't tracked)."
        ]
    },
    "biotech_biopharma": {
        "id": "biotech_biopharma",
        "name": "Biotechnology and Biopharmaceuticals",
        "type": "choose_n_courses",
        "courses_required": 4,
        "credits_required": 12,
        "description": (
            "Recent developments within biotechnology and "
            "biopharmaceuticals, focusing on engineering applications "
            "and approaches."
        ),
        "courses": [
            "CHEN_E3900", "CHEN_E4180", "CHEN_E4325", "CHEN_E4400",
            "CHEN_E4660", "CHEN_E4700", "CHEN_E4725", "CHEN_E4800",
            "CHEN_E4870", "CHEN_E4890", "CHEN_E4910", "CHEN_E4920",
            "CHEN_E4930", "CHEN_E8100", "BMEN_E4110", "BMEN_E6500",
            "BIOL_UN2005", "BIOL_UN2006", "BIOL_UN2501", "BIOC_UN3300"
        ],
        "notes": [
            "Courses taken P/F do not count towards specializations "
            "(not enforced here -- grades aren't tracked)."
        ]
    },
    "climate_environment_energy": {
        "id": "climate_environment_energy",
        "name": "Climate, Environment, and Energy Solutions",
        "type": "choose_n_courses",
        "courses_required": 4,
        "credits_required": 12,
        "description": (
            "Fundamentals and technological challenges associated with "
            "solutions to climate change and environmental pollution, "
            "including clean energy and storage, geoengineering, "
            "pollution control, and electrochemical processes for "
            "sustainable production of chemicals, fuels, and materials."
        ),
        "courses": [
            "CHEN_E3900", "CHEN_E4201", "CHEN_E4231", "CHEN_E4331",
            "CHEN_E4600", "CHEN_E4410", "EAEE_E3103", "EAEE_E4002",
            "EAEE_E4003", "EAEE_E4011", "EAEE_E4163", "EAEE_E4180",
            "EAEE_E4300", "EAEE_E4301", "EAEE_E4305", "CIEE_E3255",
            "CIEE_E3250", "CIEE_E4252", "MECE_E4211", "MSAE_E4260",
            "EESC_UN2100", "EESC_UN3101", "EESC_GU4008", "EESC_W4020",
            "EESC_GU4924"
        ],
        "notes": [
            "Courses taken P/F do not count towards specializations "
            "(not enforced here -- grades aren't tracked)."
        ]
    },
    "data_computational_science": {
        "id": "data_computational_science",
        "name": "Data and Computational Science",
        "type": "choose_n_courses",
        "courses_required": 4,
        "credits_required": 12,
        "description": (
            "Data science tools and computational modeling methods "
            "relevant to modern chemical engineering practice: data "
            "curation, statistical data analysis, predictive modeling, "
            "and experimental design integrating machine learning and "
            "AI into the chemical engineering domain."
        ),
        "courses": [
            "CHEN_E3900", "CHEN_E4010", "CHEN_E4180", "CHEN_E4670",
            "CHEN_E4580", "CHAP_E4120", "CHEN_E4150", "CHEN_E4880",
            "ORCA_E2500", "STAT_GU4001", "COMS_W4721", "COMS_W4771"
        ],
        "notes": [
            "Courses taken P/F do not count towards specializations "
            "(not enforced here -- grades aren't tracked).",
            "Per the bulletin: ORCA_E2500, STAT_GU4001, COMS_W4721, and "
            "COMS_W4771 cannot be counted as technical electives, but "
            "may be used for the math elective requirement instead."
        ]
    }
}

# (subject, number, title) for every referenced course not already in the
# catalog, per the same bulletin page.
NEW_COURSES = [
    ("BIOL", "UN2005", "INTRO BIO I: BIOCHEM,GEN,MOLEC"),
    ("BIOL", "UN2006", "INTRO BIO II:CELL BIO,DEV/PHYS"),
    ("BMEN", "E6500", "TISSUE/MOLECULAR ENGI LAB"),
    ("CHEN", "E4010", "MATH METHODS IN CHEMICAL ENGIN"),
    ("CHEN", "E4410", None),
    ("CHEN", "E4930", "Biopharmaceutical Process Laboratory"),
    ("CIEE", "E3250", None),
    ("CIEE", "E3255", None),
    ("CIEE", "E4252", None),
    ("COMS", "W4721", "MACHINE LEARNING FOR DATA SCI"),
    ("COMS", "W4771", "MACHINE LEARNING"),
    ("EAEE", "E4163", None),
    ("EAEE", "E4301", "CARBON STORAGE"),
    ("EESC", "GU4008", "Introduction to Atmospheric Science"),
    ("EESC", "GU4924", "INTRO TO ATMOSPHERIC CHEMISTRY"),
    ("EESC", "UN2100", "EARTH'S ENVIRO SYST: CLIM SYST"),
    ("EESC", "UN3101", "Geochemistry for a Habitable Planet"),
    ("EESC", "W4020", "Humans and the Carbon Cycle"),
    ("ORCA", "E2500", "FOUNDATIONS OF DATA SCIENCE 1"),
]

# Per the bulletin, ORCA/STAT/COMS courses in the Data and Computational
# Science list explicitly do NOT count as technical electives (they may
# instead satisfy the math elective) -- everything else in these lists is
# explicitly framed as drawn from "a list of technical elective courses."
NOT_TECHNICAL_ELECTIVE_SUBJECTS = {"ORCA", "STAT", "COMS"}
MATH_ELECTIVE_OVERRIDE = {"ORCA_E2500", "STAT_GU4001", "COMS_W4721", "COMS_W4771"}


def add_missing_courses():
    with open(TECH_ELECTIVES_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    added = []
    for subject, number, title in NEW_COURSES:
        course_id = f"{subject}_{number}"
        if course_id in catalog:
            continue

        tags = []
        if course_id in MATH_ELECTIVE_OVERRIDE:
            tags.append("math_elective")
        elif subject not in NOT_TECHNICAL_ELECTIVE_SUBJECTS:
            tags.append("technical_elective")

        catalog[course_id] = {
            "id": course_id,
            "subject": subject,
            "number": number,
            "title": title,
            "credits": None,
            "category_tags": tags,
            "prerequisites": [],
            "corequisites": [],
            "aliases": [],
            "notes": [
                "Added from the ChemE elective specialization course "
                "lists (bulletin, fetched 2026-09-18). Tech-elective "
                "sub-category (engineering vs. advanced STEM) not yet "
                "classified -- needs advisor verification."
            ] if tags == ["technical_elective"] else []
        }
        added.append(course_id)

    with open(TECH_ELECTIVES_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return added


def write_concentrations():
    CONCENTRATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONCENTRATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump({"concentrations": CONCENTRATIONS}, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    added = add_missing_courses()
    write_concentrations()
    print(f"Added {len(added)} new course(s) to {TECH_ELECTIVES_PATH}: {added}")
    print(f"Wrote {CONCENTRATIONS_PATH} with {len(CONCENTRATIONS)} specializations.")
