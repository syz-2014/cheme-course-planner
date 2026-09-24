"""
One-time data entry: adds `source_url` fields pointing students directly
at the official bulletin page behind each requirement, concentration, and
minor, so the app can link out to primary sources instead of just
asserting "this is the rule."

Also writes data/ap_credit_chart.json, Columbia Engineering's official AP
(and IB/A-level) credit chart -- sourced from the same bulletin page
(fetched 2026-09-23). This is reference data only; the app doesn't try to
automatically apply it (several rows are grade-in-a-follow-on-course
contingent, e.g. "credit reduced to 0 if PHYS UN1401 is taken", which
isn't something this app can verify).

Run from project root:
    /usr/local/bin/python3 scripts/add_source_links.py
"""

import json
from pathlib import Path

REQUIREMENTS_PATH = Path("data/requirements.json")
CONCENTRATIONS_PATH = Path("data/concentrations.json")
MINORS_PATH = Path("data/minors.json")
AP_CHART_PATH = Path("data/ap_credit_chart.json")

CHEME_BULLETIN_URL = (
    "https://bulletin.columbia.edu/columbia-engineering/academic-departments-programs/"
    "chemical-engineering/undergraduate-programs/chemical-engineering-bs/#curriculumtext"
)
FIRST_YEAR_SOPHOMORE_URL = (
    "https://bulletin.columbia.edu/columbia-engineering/undergraduate-studies/"
    "undergraduate-programs/first-year-sophomore-program/"
)
GLOBAL_CORE_URL = "https://www.gs.columbia.edu/content/global-core-requirement"
MINORS_INDEX_URL = "https://bulletin.columbia.edu/columbia-engineering/undergraduate-minors/"

REQUIREMENT_SOURCE_URLS = {
    "math_foundation": CHEME_BULLETIN_URL,
    "physics_requirement": CHEME_BULLETIN_URL,
    "chemistry_requirement": CHEME_BULLETIN_URL,
    "major_required_courses": CHEME_BULLETIN_URL,
    "math_elective": CHEME_BULLETIN_URL,
    "natural_science_lab": CHEME_BULLETIN_URL,
    "technical_electives": CHEME_BULLETIN_URL,
    "physical_education": FIRST_YEAR_SOPHOMORE_URL,
    "nontechnical_requirement": FIRST_YEAR_SOPHOMORE_URL,
}

# Bulletin page title -> our minor id, from the Undergraduate Minors index
# (https://bulletin.columbia.edu/columbia-engineering/undergraduate-minors/),
# fetched 2026-09-23.
MINOR_NAME_TO_URL = {
    "Aerospace Engineering Minor": "/columbia-engineering/undergraduate-minors/aerospace-engineering-minor/",
    "American Studies Minor": "/columbia-engineering/undergraduate-minors/american-studies-minor/",
    "Anthropology Minor": "/columbia-engineering/undergraduate-minors/anthropology-minor/",
    "Applied Mathematics Minor": "/columbia-engineering/undergraduate-minors/applied-mathematics-minor/",
    "Applied Physics Minor": "/columbia-engineering/undergraduate-minors/applied-physics-minor/",
    "Architecture Minor": "/columbia-engineering/undergraduate-minors/architecture-minor/",
    "Art History Minor": "/columbia-engineering/undergraduate-minors/art-history-minor/",
    "Artificial Intelligence Minor": "/columbia-engineering/undergraduate-minors/artificial-intelligence-minor/",
    "Biomedical Engineering Minor": "/columbia-engineering/undergraduate-minors/biomedical-engineering-minor/",
    "Catalan Minor": "/columbia-engineering/undergraduate-minors/catalan-minor/",
    "Civil Engineering Minor": "/columbia-engineering/undergraduate-minors/civil-engineering-minor/",
    "Computer Science Minor": "/columbia-engineering/undergraduate-minors/computer-science-minor/",
    "Dance Minor": "/columbia-engineering/undergraduate-minors/dance-minor/",
    "Earth and Environmental Engineering Minor": "/columbia-engineering/undergraduate-minors/earth-environmental-engineering-minor/",
    "East Asian Studies Minor": "/columbia-engineering/undergraduate-minors/east-asian-studies-minor/",
    "Economics Minor": "/columbia-engineering/undergraduate-minors/economics-minor/",
    "Electrical Engineering Minor": "/columbia-engineering/undergraduate-minors/electrical-engineering-minor/",
    "Engineering Mechanics Minor": "/columbia-engineering/undergraduate-minors/engineering-mechanics-minor/",
    "English and Comparative Literature Minor": "/columbia-engineering/undergraduate-minors/english-comparative-literature-minor/",
    "Entrepreneurship and Innovation Minor": "/columbia-engineering/undergraduate-minors/entrepreneurship-innovation-minor/",
    "Ethnicity and Race Minor": "/columbia-engineering/undergraduate-minors/ethnicity-race-minor/",
    "Film and Media Studies Minor": "/columbia-engineering/undergraduate-minors/film-media-studies-minor/",
    "French and Francophone Studies Minor": "/columbia-engineering/undergraduate-minors/french-francophone-studies-minor/",
    "Fusion Energy Minor": "/columbia-engineering/undergraduate-minors/fusion-energy-minor/",
    "German Minor": "/columbia-engineering/undergraduate-minors/german-minor/",
    "Greek or Latin Minor": "/columbia-engineering/undergraduate-minors/greek-latin-minor/",
    "Hispanic Studies Minor": "/columbia-engineering/undergraduate-minors/hispanic-studies-minor/",
    "History Minor": "/columbia-engineering/undergraduate-minors/history-minor/",
    "Industrial Engineering Minor": "/columbia-engineering/undergraduate-minors/industrial-engineering-minor/",
    "Italian Minor": "/columbia-engineering/undergraduate-minors/italian-minor/",
    "Jewish Studies Minor": "/columbia-engineering/undergraduate-minors/jewish-studies-minor/",
    "Linguistics Minor": "/columbia-engineering/undergraduate-minors/linguistics-minor/",
    "Materials Science Minor": "/columbia-engineering/undergraduate-minors/materials-science-minor/",
    "Mechanical Engineering Minor": "/columbia-engineering/undergraduate-minors/mechanical-engineering-minor/",
    "Middle Eastern, South Asian, and African Studies Minor": "/columbia-engineering/undergraduate-minors/middle-eastern-south-asian-african-studies-minor/",
    "Mining Engineering Minor": "/columbia-engineering/undergraduate-minors/mining-engineering-minor/",
    "Music Minor": "/columbia-engineering/undergraduate-minors/music-minor/",
    "Operations Research Minor": "/columbia-engineering/undergraduate-minors/operations-research-minor/",
    "Philosophy Minor": "/columbia-engineering/undergraduate-minors/philosophy-minor/",
    "Political Science Minor": "/columbia-engineering/undergraduate-minors/political-science-minor/",
    "Portuguese Minor": "/columbia-engineering/undergraduate-minors/portuguese-minor/",
    "Psychology Minor": "/columbia-engineering/undergraduate-minors/psychology-minor/",
    "Religion Minor": "/columbia-engineering/undergraduate-minors/religion-minor/",
    "Sociology Minor": "/columbia-engineering/undergraduate-minors/sociology-minor/",
    "Statistics Minor (legacy, pre-2026-2027)": "/columbia-engineering/undergraduate-minors/statistics-minor/",
    "Statistics Minor -- Applied Track": "/columbia-engineering/undergraduate-minors/statistics-minor-applied-track/",
    "Statistics Minor -- Theory Track": "/columbia-engineering/undergraduate-minors/statistics-minor-theory-track/",
    "Sustainable Engineering Minor": "/columbia-engineering/undergraduate-minors/sustainable-engineering-minor/",
    "Women's, Gender and Sexuality Studies Minor": "/columbia-engineering/undergraduate-minors/womens-gender-sexuality-studies-minor/",
}
BULLETIN_BASE = "https://bulletin.columbia.edu"

# Columbia Engineering's official AP Credit Chart, from "The First Year/
# Sophomore Program" bulletin page (fetched 2026-09-23). Reference only --
# several rows are conditional on a grade in a specific follow-on course,
# which this app has no mechanism to verify, so nothing here is enforced
# automatically.
AP_CREDIT_CHART = {
    "source_url": FIRST_YEAR_SOPHOMORE_URL,
    "max_total_points": 16,
    "notes": [
        "A maximum of 16 points of AP/IB/A-level credit total may be applied toward the degree.",
        "AP credit in appropriate subject areas can be applied toward the 9-point elective "
        "nontechnical requirement and for Principles of Economics.",
        "AP credits may be applied toward minor requirements depending on the specific rules "
        "of the minor; when allowed, only one course per minor may be replaced by AP credit.",
        "Students majoring in Chemical Engineering or Materials Science must complete both "
        "the Chemistry and Physics labs regardless of AP credit earned."
    ],
    "chart": [
        {"subject": "Art History", "score": "5", "credit_points": 3, "note": "No exemption from HUMA UN1121"},
        {"subject": "Biology", "score": "5", "credit_points": 3, "note": "No exemption"},
        {"subject": "Chemistry", "score": "4 or 5", "credit_points": 3, "note": "Requires completion of CHEM UN1604 with grade of C or better"},
        {"subject": "Chemistry", "score": "4 or 5", "credit_points": 6, "note": "Requires completion of CHEM UN2045-CHEM UN2046 with grade of C or better"},
        {"subject": "Computer Science A", "score": "4 or 5", "credit_points": 3, "note": "Exemption from COMS W1004"},
        {"subject": "Computer Principles", "score": "4 or 5", "credit_points": 3, "note": "Exemption from COMS W1001"},
        {"subject": "Economics Micro & Macro", "score": "5 and 4", "credit_points": 4, "note": "Exemption from ECON UN1105. Exams must be taken in both micro and macro, with a score of 5 in one and at least a 4 in the other."},
        {"subject": "English Language and Composition", "score": "5", "credit_points": 3, "note": "No exemption"},
        {"subject": "English Literature and Composition", "score": "5", "credit_points": 3, "note": "No exemption"},
        {"subject": "French", "score": "4 or 5", "credit_points": 3, "note": ""},
        {"subject": "German Language", "score": "4 or 5", "credit_points": 3, "note": ""},
        {"subject": "Government and Politics United States", "score": "5", "credit_points": 4, "note": "Exemption from POLS UN2201"},
        {"subject": "Government and Politics Comparative", "score": "5", "credit_points": 4, "note": "Exemption from POLS UN2501"},
        {"subject": "History European", "score": "5", "credit_points": 3, "note": ""},
        {"subject": "History United States", "score": "5", "credit_points": 3, "note": ""},
        {"subject": "Italian Language", "score": "4 or 5", "credit_points": 3, "note": ""},
        {"subject": "Latin Literature", "score": "5", "credit_points": 3, "note": ""},
        {"subject": "Mathematics Calculus AB", "score": "4 or 5", "credit_points": 3, "note": "Requires completion of MATH UN1102 with a grade of C or better. Credit is reduced to 0 if MATH UN1101 is taken."},
        {"subject": "Mathematics Calculus BC", "score": "4", "credit_points": 3, "note": "Requires completion of MATH UN1102 with a grade of C or better. Credit is reduced to 0 if MATH UN1101 is taken."},
        {"subject": "Mathematics Calculus BC", "score": "5", "credit_points": 6, "note": "Requires completion of APMA E2000 with a grade of C or better. Credit is reduced to 0 if MATH UN1101 is taken, or to 3 if MATH UN1102 is taken."},
        {"subject": "Physics C-E&M", "score": "4 or 5", "credit_points": 3, "note": "Maximum of six credits combined with Physics C-Mech. Credit is reduced to 0 if PHYS UN1401 or 1601 is taken, or if PHYS UN2801 is taken with a final grade of C- or lower."},
        {"subject": "Physics C-Mech", "score": "4 or 5", "credit_points": 3, "note": "Credit is reduced to 0 if PHYS UN1401 or 1601 is taken, or if PHYS UN2801 is taken with a final grade of C- or lower."},
        {"subject": "Physics 1 and 2", "score": "4 or 5", "credit_points": 3, "note": "No exemption. Both AP Physics 1 and 2 must be taken to receive credit."},
        {"subject": "Spanish Language", "score": "4 or 5", "credit_points": 3, "note": ""},
        {"subject": "Spanish Literature", "score": "4 or 5", "credit_points": 3, "note": ""},
    ]
}


def add_requirement_source_urls():
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for req_id, url in REQUIREMENT_SOURCE_URLS.items():
        if req_id in data["requirements"]:
            data["requirements"][req_id]["source_url"] = url

    with open(REQUIREMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def add_concentration_source_urls():
    with open(CONCENTRATIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for concentration in data["concentrations"].values():
        concentration["source_url"] = CHEME_BULLETIN_URL

    with open(CONCENTRATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def add_minor_source_urls():
    with open(MINORS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    name_to_id = {minor["name"]: minor_id for minor_id, minor in data["minors"].items()}
    missing = []

    for name, path in MINOR_NAME_TO_URL.items():
        minor_id = name_to_id.get(name)
        if not minor_id:
            missing.append(name)
            continue
        data["minors"][minor_id]["source_url"] = BULLETIN_BASE + path

    unmatched = [
        minor["name"] for minor in data["minors"].values()
        if "source_url" not in minor
    ]

    with open(MINORS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return missing, unmatched


def write_ap_credit_chart():
    AP_CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AP_CHART_PATH, "w", encoding="utf-8") as f:
        json.dump(AP_CREDIT_CHART, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    add_requirement_source_urls()
    print("Added source_url to requirements.json entries.")

    add_concentration_source_urls()
    print("Added source_url to all concentrations.")

    missing, unmatched = add_minor_source_urls()
    if missing:
        print(f"WARNING: {len(missing)} bulletin names had no matching minor id: {missing}")
    if unmatched:
        print(f"WARNING: {len(unmatched)} minors still missing source_url: {unmatched}")
    if not missing and not unmatched:
        print(f"Added source_url to all minors.")

    write_ap_credit_chart()
    print(f"Wrote {AP_CHART_PATH}.")
