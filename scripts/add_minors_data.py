"""
One-time data entry: adds Columbia Engineering's undergraduate minors (all
of them except the Chemical Engineering Minor itself, which is for
non-ChemE majors and irrelevant to this app's users) and any course
catalog entries they reference that weren't already present.

Source: https://bulletin.columbia.edu/columbia-engineering/undergraduate-minors/
and each minor's own page (fetched 2026-09-18).

Every minor is also subject to these school-wide rules (see
GLOBAL_MINOR_RULES below), none of which this app enforces since it
doesn't track grades: at least 15 points, GPA 2.0 minimum, no more than
one course from outside Columbia or via AP/IB credit, no course double-
counted across two minors, no pass/fail courses, no substitutions without
department approval.

Minor requirement pages vary hugely in structure -- from a flat required
list (Biomedical Engineering) to multi-tier "choose N of category X, up to
M from category Y" rules (Fusion Energy, Aerospace) to prose-based
distribution rules that don't reduce to a course list at all (Art
History's period/region requirement, Psychology's numbering-range groups).
Each minor's `groups` list uses whichever of these types fits what the
bulletin actually says -- never a guessed course list:

  - all_of: every course in `options` is required
  - choose_one_of: exactly one course from `options`
  - choose_n_of: `count` courses from `options`
  - subject_level_count: `count` courses (or `credits_required` points)
    matching subject(s) in `subjects`, optionally bounded by `min_level`/
    `max_level` (parsed from the course number) and `exclude`
  - free_form: a real requirement that can't be resolved to a checkable
    rule from the given fields (a prose distribution rule, a category cap
    that doesn't reduce to a flat list, etc.) -- `description` holds it
    verbatim-ish; the validator always reports these as unverified rather
    than guessing at satisfaction.

A minor with `"unstructured": true` is one whose overall shape (not just
one group) couldn't be confidently captured this way; `description` holds
what the bulletin says and no group-level checking is attempted at all.

Run from project root:
    /usr/local/bin/python3 scripts/add_minors_data.py
"""

import json
from pathlib import Path

MINORS_PATH = Path("data/minors.json")
CATALOG_FILES = {
    "core": Path("data/courses_core.json"),
    "tech": Path("data/courses_tech_electives.json"),
    "globalcore": Path("data/courses_globalcore.json"),
}
# New courses referenced by minors go here by default -- they're not
# ChemE technical electives, just courses a ChemE student might take for
# a minor, so they get no category_tags.
MINOR_COURSES_TARGET = CATALOG_FILES["globalcore"]

GLOBAL_MINOR_RULES = {
    "credits_min": 15,
    "gpa_min": 2.0,
    "max_non_columbia_courses": 1,
    "pass_fail_allowed": False,
    "double_counting_across_minors_allowed": False,
    "notes": [
        "A minor requires at least 15 points of credit.",
        "No more than one course may be taken outside Columbia or via AP/IB credit (including study abroad).",
        "The same course may not be used to satisfy more than one minor.",
        "No courses taken pass/fail may count for a minor.",
        "Minimum GPA for the minor is 2.0.",
        "No substitutions or changes from the approved minor are permitted without department approval.",
        "None of these rules (GPA, pass/fail, double-counting, the AP/transfer cap) are enforced by this app -- it doesn't track grades or cross-minor state."
    ]
}

MINORS = {
    "aerospace_engineering": {
        "id": "aerospace_engineering", "name": "Aerospace Engineering Minor",
        "unstructured": True,
        "description": (
            "A combination of core courses (fluid mechanics, thermodynamics, "
            "structures/mechanics, controls, signals, AERO foundations) and "
            "elective courses across aerospace structures/systems, energy/"
            "propulsion, robotics/control, and computing/communications "
            "categories, several with their own \"up to N\" caps. The exact "
            "core-vs-elective split wasn't extractable with confidence from "
            "the bulletin's table formatting -- verify with the department."
        ),
        "notes": []
    },
    "american_studies": {
        "id": "american_studies", "name": "American Studies Minor",
        "groups": [
            {"label": "Intro to American Studies", "type": "all_of", "options": ["AMST_UN1010"]},
            {"label": "3000-level AMST seminar", "type": "subject_level_count",
             "subjects": ["AMST"], "min_level": 3000, "count": 1},
            {"label": "Additional courses on American history, culture, or politics (choose 3)",
             "type": "choose_n_of", "count": 3, "options": [
                "AFAS_UN1001", "CSER_UN3940", "ENGL_UN2826", "ENGL_BC3180", "ENGL_BC3183",
                "ENGL_UN3241", "ENGL_UN3351", "ENGL_UN3832", "HIST_UN1488", "HIST_UN1512",
                "HIST_UN2432", "HIST_UN2523", "HIST_UN2533", "HIST_UN2535", "HIST_UN2540",
                "HIST_UN2565", "HIST_UN2587", "HIST_UN2679", "HIST_UN3501", "HIST_GU4518",
                "HIST_GU4933", "POLS_UN1201", "POLS_UN3100", "POLS_UN3213", "POLS_UN3222",
                "POLS_UN3255", "POLS_UN3290", "RELI_UN1612", "RELI_GU4217", "SOCI_UN3265"
             ]}
        ],
        "notes": ["The elective list above is representative, not exhaustive, per the bulletin."]
    },
    "anthropology": {
        "id": "anthropology", "name": "Anthropology Minor",
        "groups": [
            {"label": "Intro course", "type": "choose_one_of", "options": ["ANTH_UN1002", "ANTH_UN1008"]},
            {"label": "Anthropology department courses (choose 4)", "type": "subject_level_count",
             "subjects": ["ANTH"], "count": 4}
        ],
        "notes": [
            "Also allows ethnomusicology courses or any course taught by an Anthropology "
            "instructor regardless of department -- not resolvable to a fixed subject "
            "list, so only ANTH-subject courses are auto-counted here.",
            "No distribution requirement."
        ]
    },
    "architecture": {
        "id": "architecture", "name": "Architecture Minor",
        "unstructured": True,
        "description": (
            "One to three studio courses (from a short list including "
            "ARCH_UN1020, ARCH_UN2101, ARCH_UN2103, ARCH_UN3117) plus one "
            "to three additional courses -- \"any lecture, seminar, or "
            "workshop offered or approved by the Architecture Department\" "
            "-- which isn't resolvable to a fixed course list."
        ),
        "notes": []
    },
    "art_history": {
        "id": "art_history", "name": "Art History Minor",
        "unstructured": True,
        "description": (
            "At least one course in three of four historical periods "
            "(Ancient; 400-1400; 1400-1700; 1700-present), two additional "
            "courses covering two of several world regions, plus two more "
            "Art History and Archaeology department courses -- a period/"
            "region taxonomy this app has no mapping for, so it can't be "
            "checked against specific course ids."
        ),
        "notes": []
    },
    "artificial_intelligence": {
        "id": "artificial_intelligence", "name": "Artificial Intelligence Minor",
        "groups": [
            {"label": "Math foundation", "type": "all_of", "options": ["MATH_UN2015"]},
            {"label": "Intro programming", "type": "choose_one_of", "options": ["ENGI_E1006", "COMS_W1002"]},
            {"label": "Intermediate programming", "type": "choose_one_of", "options": ["COMS_W2132", "IEOR_E2000"]},
            {"label": "AI requirement", "type": "all_of", "options": ["COMS_W4701"]},
            {"label": "Ethics requirement", "type": "choose_one_of", "options": [
                "COMS_W4710", "COMS_W2702", "PSYC_GU4836", "ORCS_E4201", "COMS_BC3420", "COMS_BC3707"
            ]},
            {"label": "AI elective", "type": "choose_one_of", "options": [
                "BMEN_E4460", "BMEN_E4470", "BMEN_E4480", "CBMF_W4761", "CHEN_E4180",
                "CIEN_E4253", "CIEN_E4256", "EAEE_E4000", "ECBM_E4040", "EECS_E4764",
                "ELEN_E4720", "ELEN_E4730", "IEOR_E4212", "IEOR_E4540", "MECE_E4520",
                "MECE_E4602", "ORCS_E4200", "ORCS_E4529", "POLS_GU4728", "STAT_GU4241",
                "STAT_GU4242", "STAT_GU4244"
            ], "notes": ["Or any COMS 47XX course, or a relevant 4995/6998 topics course -- not enumerated here."]},
            {"label": "Linear algebra", "type": "choose_one_of",
             "options": ["MATH_UN2010", "COMS_W3251", "MATH_UN2020", "APMA_E2101", "APMA_E3101"]},
            {"label": "Probability", "type": "choose_one_of",
             "options": ["STAT_UN1201", "STAT_GU4001", "IEOR_E3658"]}
        ],
        "notes": ["Computer Science majors and minors are not eligible for this minor."]
    },
    "biomedical_engineering": {
        "id": "biomedical_engineering", "name": "Biomedical Engineering Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of",
             "options": ["BIOL_UN2005", "BIOL_UN2006", "BMEN_E3010", "BMEN_E3020", "BMEN_E4001", "BMEN_E4002"]}
        ],
        "notes": ["Participation is subject to approval of the major program adviser."]
    },
    "catalan": {
        "id": "catalan", "name": "Catalan Minor",
        "unstructured": True,
        "description": (
            "Requires one year of Catalan (CATL_UN1120, CATL_UN2101) or "
            "placement equivalent, then CATL_UN2102, CATL_UN3300, "
            "CATL_UN3500, an advanced Spanish course, and one additional "
            "3000+ course -- with several proficiency-based substitution "
            "branches (testing out of CATL_UN2102 opens study-abroad or "
            "cross-department alternatives) too conditional to check "
            "automatically."
        ),
        "notes": []
    },
    "civil_engineering": {
        "id": "civil_engineering", "name": "Civil Engineering Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["ENME_E3105", "ENME_E3113"]},
            {"label": "Choose one", "type": "choose_one_of", "options": ["CIEN_E3121", "ENME_E3161", "MECE_E3100"]},
            {"label": "Choose three", "type": "choose_n_of", "count": 3, "options": [
                "CIEN_E3000", "ENME_E3161", "ENME_E3114", "ENME_E3332", "MECE_E3414",
                "CIEN_E3125", "CIEN_E4241", "EACE_E3250", "EACE_E4163", "CIEN_E3129", "CIEN_E4131"
            ]}
        ],
        "notes": []
    },
    "computer_science": {
        "id": "computer_science", "name": "Computer Science Minor",
        "groups": [
            {"label": "Intro programming", "type": "choose_one_of", "options": ["COMS_W1004", "COMS_W1007"]},
            {"label": "Data structures", "type": "choose_one_of", "options": ["COMS_W3134", "COMS_W3137"]},
            {"label": "Discrete math", "type": "all_of", "options": ["COMS_W3203"]},
            {"label": "Choose one", "type": "choose_one_of", "options": ["COMS_W3157", "COMS_W3261", "CSEE_W3827"]},
            {"label": "CS elective", "type": "free_form",
             "description": "Any 3000- or 4000-level COMS/CSXX/XXCS course of at least 3 points."},
            {"label": "CS elective or linear algebra/probability", "type": "choose_one_of",
             "options": ["APMA_E3101", "APMA_E2101", "MATH_UN2010", "MATH_UN2015", "IEOR_E3658", "STAT_UN1201", "STAT_GU4001"],
             "notes": ["Or any 3000+/4000+ level COMS/CSXX/XXCS course of at least 3 points."]}
        ],
        "notes": [
            "A 4 or 5 on the CS AP Exam A gives 3 points and exemption from COMS_W1004.",
            "Participation is subject to approval of the major program adviser."
        ]
    },
    "dance": {
        "id": "dance", "name": "Dance Minor",
        "groups": [
            {"label": "History/Criticism (choose 2)", "type": "choose_n_of", "count": 2, "options": [
                "DNCE_BC2565", "DNCE_BC2570", "DNCE_BC3000", "DNCE_BC3001", "DNCE_BC3002",
                "DNCE_BC3200", "DNCE_BC3240", "DNCE_BC3550", "DNCE_BC3567", "DNCE_BC3576", "DNCE_BC3577"
            ]},
            {"label": "Performance/Choreography (choose 2)", "type": "choose_n_of", "count": 2, "options": [
                "DNCE_BC2563", "DNCE_BC2564", "DNCE_BC2567", "DNCE_BC3601", "DNCE_BC3602",
                "DNCE_BC3603", "DNCE_BC3604", "DNCE_BC3605", "DNCE_BC3606", "DNCE_BC3607"
            ]},
            {"label": "Elective", "type": "free_form", "description": "One additional dance course."}
        ],
        "notes": ["Five 3-point courses total.", "No performance/choreography course counts toward the nontechnical requirement."]
    },
    "earth_environmental_engineering": {
        "id": "earth_environmental_engineering", "name": "Earth and Environmental Engineering Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["EAEE_E2100", "EACE_E4252"]},
            {"label": "Choose two", "type": "choose_n_of", "count": 2, "options": [
                "EAEE_E3103", "EAEE_E3200", "CHEE_E3010", "EAEE_E4003", "EACE_E3250",
                "EAEE_E3901", "EAEE_E4160", "EACE_E3255"
            ]},
            {"label": "Any 3000+ EAEE or cross-listed course (choose 2)", "type": "subject_level_count",
             "subjects": ["EAEE", "CHEE", "CIEE", "EACE", "EACH", "EAIA", "EEEL"], "min_level": 3000, "count": 2}
        ],
        "notes": []
    },
    "east_asian_studies": {
        "id": "east_asian_studies", "name": "East Asian Studies Minor",
        "groups": [
            {"label": "Survey course (choose 2)", "type": "choose_n_of", "count": 2, "options": [
                "ASCE_UN1359", "ASCE_UN1361", "ASCE_UN1363", "ASCE_UN1365", "ASCE_UN1367"
            ]},
            {"label": "Electives dealing with East Asia (choose 3)", "type": "free_form",
             "description": "Three elective courses dealing with East Asia, which may be in departments outside East Asian Languages and Cultures -- not resolvable to a fixed course list."}
        ],
        "notes": [
            "No language requirement, but one semester of an East Asian language may count as one "
            "of the three electives if at least two semesters have been completed."
        ]
    },
    "english_comparative_literature": {
        "id": "english_comparative_literature", "name": "English and Comparative Literature Minor",
        "groups": [
            {"label": "English department courses (choose 5)", "type": "subject_level_count",
             "subjects": ["ENGL"], "count": 5, "exclude": ["ENGL_CC1010"]}
        ],
        "notes": ["No distribution requirement.", "No speech courses; only one writing course allowed.", "Total 15 points."]
    },
    "entrepreneurship_innovation": {
        "id": "entrepreneurship_innovation", "name": "Entrepreneurship and Innovation Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["IEOR_E2261", "IEOR_E4998"]},
            {"label": "Opportunity Discovery & Product Innovation", "type": "choose_one_of",
             "options": ["COMS_W4460", "IEME_E4200", "IEME_E4505"]},
            {"label": "Startup Management", "type": "choose_one_of",
             "options": ["CHEN_E4020", "ECON_GU4280", "IEOR_E4003", "IEOR_E4510"]},
            {"label": "Industry Focus and Case Studies", "type": "choose_one_of",
             "options": ["CIEN_E4136", "COMS_W4444", "ENGI_E4502", "COMS_W4170", "IEOR_E4207"]}
        ],
        "notes": ["Minimum 15 points."]
    },
    "ethnicity_race": {
        "id": "ethnicity_race", "name": "Ethnicity and Race Minor",
        "groups": [
            {"label": "Intro course", "type": "all_of", "options": ["CSER_UN1010"]},
            {"label": "Choose one", "type": "choose_one_of", "options": ["CSER_UN3928", "CSER_UN3942"]},
            {"label": "Additional CSER courses (choose 3)", "type": "subject_level_count",
             "subjects": ["CSER"], "count": 3}
        ],
        "notes": ["The 3 additional CSER courses require department approval."]
    },
    "film_media_studies": {
        "id": "film_media_studies", "name": "Film and Media Studies Minor",
        "groups": [
            {"label": "Intro course", "type": "all_of", "options": ["FILM_UN1000"]},
            {"label": "Cinema history (choose 2)", "type": "choose_n_of", "count": 2,
             "options": ["FILM_UN2010", "FILM_UN2020", "FILM_UN2030", "FILM_UN2040"],
             "notes": ["One of the two must be FILM_UN2010 or FILM_UN2020 -- not separately enforced here."]},
            {"label": "Film and Media Studies department courses (choose 2)", "type": "subject_level_count",
             "subjects": ["FILM"], "count": 2}
        ],
        "notes": [
            "Only one elective may be a lab course (FILM_UN2410/2420/2510/2520).",
            "Only one study-abroad/transfer class (3-credit equivalent) may count.",
            "Five courses (15 credits) total."
        ]
    },
    "french_francophone_studies": {
        "id": "french_francophone_studies", "name": "French and Francophone Studies Minor",
        "groups": [
            {"label": "Core", "type": "all_of", "options": ["FREN_UN3405"]},
            {"label": "Core (choose one)", "type": "choose_one_of", "options": ["FREN_UN3409", "FREN_UN3410"]},
            {"label": "Interdisciplinary electives (choose 3)", "type": "subject_level_count",
             "subjects": ["FREN"], "min_level": 3000, "count": 3}
        ],
        "notes": [
            "Prerequisite: FREN_UN2102 Intermediate French II.",
            "Some French courses at Barnard may be approved by the Director of Undergraduate Studies.",
            "Five courses / minimum 15 points beyond the language prerequisite."
        ]
    },
    "fusion_energy": {
        "id": "fusion_energy", "name": "Fusion Energy Minor",
        "groups": [
            {"label": "Core courses in nuclear and plasma physics (choose 2)", "type": "choose_n_of", "count": 2,
             "options": ["APPH_E3300", "APPH_E4010", "APPH_E4018", "APPH_E4301", "APPH_E6101", "APPH_E6102"]},
            {"label": "Elective courses (4, across capped categories)", "type": "free_form", "description": (
                "Four elective courses across capped categories: up to 1 more in nuclear/plasma "
                "physics (same list as core), up to 1 in fluid dynamics (APPH_E4200, MECE_E3100, "
                "ENME_E3161), up to 2 in circuits and control (ELEN_E3201, ELEN_E3801, EEME_E3601, "
                "EEME_E4601, MECE_E4602), up to 1 in mathematical/computational modeling "
                "(APMA_E4300, APMA_E4301, APMA_E4101, COMS_W4701, COMS_W4771), up to 1 in fluid/"
                "finite element modeling (ENME_E3332, MECE_E6102, MECE_E6106), and up to 2 in "
                "materials science (MSAE_E3010, MSAE_E4206, MSAE_E4215, MECE_E4461). The per-"
                "category caps don't reduce to a single flat course-count check."
            )}
        ],
        "notes": []
    },
    "german": {
        "id": "german", "name": "German Minor",
        "groups": [
            {"label": "Core", "type": "all_of", "options": ["GERM_UN3333"]},
            {"label": "3000/4000-level German literature/culture (choose 3)", "type": "subject_level_count",
             "subjects": ["GERM"], "min_level": 3000, "count": 3}
        ],
        "notes": [
            "Requires 4 semesters of German (through Intermediate II) or placement equivalent.",
            "Up to 6 of the 15 total points may come from upper-level language courses "
            "(Intermediate II and/or Advanced); the rest must be 3000/4000-level literature/culture.",
            "Five courses / 15 points total."
        ]
    },
    "greek_latin": {
        "id": "greek_latin", "name": "Greek or Latin Minor",
        "unstructured": True,
        "description": (
            "A minimum of 13 points in the chosen language (Greek or Latin) at the "
            "1200 level or higher, plus 3 points in ancient history of the "
            "corresponding civilization -- a points-in-level-range rule, not a "
            "fixed course list."
        ),
        "notes": []
    },
    "hispanic_studies": {
        "id": "hispanic_studies", "name": "Hispanic Studies Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["SPAN_UN3300", "SPAN_UN3349", "SPAN_UN3350"]},
            {"label": "Latin American and Iberian Cultures electives (choose 3)", "type": "subject_level_count",
             "subjects": ["SPAN"], "min_level": 3000, "count": 3,
             "notes": ["May also include other LAIC-department courses beyond SPAN -- not enumerated here."]}
        ],
        "notes": ["Contact the LAIC Director of Undergraduate Studies to declare."]
    },
    "history": {
        "id": "history", "name": "History Minor",
        "groups": [
            {"label": "History department courses (choose 5)", "type": "subject_level_count",
             "subjects": ["HIST"], "count": 5}
        ],
        "notes": ["No distribution or seminar requirements.", "Transfer or study-abroad credit may not be applied."]
    },
    "industrial_engineering": {
        "id": "industrial_engineering", "name": "Industrial Engineering Minor",
        "groups": [
            {"label": "Probability/statistics", "type": "choose_one_of",
             "options": ["IEOR_E3658", "STAT_GU4001", "STAT_GU4203"]},
            {"label": "Required courses", "type": "all_of",
             "options": ["IEOR_E3402", "IEOR_E3608", "IEOR_E4003"]},
            {"label": "IEOR/ORCS/CSOR 3000+ electives (choose 2)", "type": "subject_level_count",
             "subjects": ["IEOR", "ORCS", "CSOR"], "min_level": 3000, "count": 2}
        ],
        "notes": [
            "18 credits total.",
            "Operations Research, Financial Engineering, or Engineering Management Systems majors "
            "need 3 additional IEOR electives not used for their major."
        ]
    },
    "italian": {
        "id": "italian", "name": "Italian Minor",
        "groups": [
            {"label": "Sequence (choose one of three)", "type": "free_form", "description": (
                "One of three sequences: (1) ITAL_UN3335 plus Italian-through-content courses "
                "(e.g. ITAL_UN3337/3338/3339/3341/3342/3343, ITAL_UN3232, ITAL_UN3645); "
                "(2) ITAL_UN3333 + ITAL_UN3334; or (3) ITAL_GU4502 + ITAL_GU4503."
            )},
            {"label": "Additional electives (choose 3)", "type": "subject_level_count",
             "subjects": ["ITAL"], "min_level": 3000, "count": 3,
             "notes": ["May include Humanities/Social Science courses outside Italian with a substantial Italian focus (not enumerated); at least one must be within the Italian Department."]}
        ],
        "notes": [
            "Prerequisite: Intermediate II Italian or placement equivalent.",
            "Five courses / 15 points total."
        ]
    },
    "jewish_studies": {
        "id": "jewish_studies", "name": "Jewish Studies Minor",
        "groups": [
            {"label": "Jewish Studies courses (choose 5)", "type": "choose_n_of", "count": 5, "options": [
                "JWST_UN2155", "RELI_UN2306", "HIST_UN2611", "SOCI_UN3285", "RELI_V3301",
                "SPJS_UN3303", "YIDD_UN3500", "CLYD_UN3500", "HIST_UN3604", "MUSI_GU4113",
                "JWST_GU4145", "JWST_GU4147", "JWST_GU4156", "JWST_GU4157", "JWST_GU4149",
                "JWST_GU4153", "JWST_GU4154", "CLYD_GU4250", "WMST_GU4336", "RELI_GU4509",
                "HIST_GU4525", "SOCI_GU4801", "ENGL_GU4938", "JWST_GU4990"
            ]}
        ],
        "notes": [
            "15-20 points total.",
            "Introductory language study relevant to Jewish Studies coursework may count as one course; "
            "advanced language courses conducted in the language may count as an additional course.",
            "Other courses with significant Jewish Studies content may also be applicable -- contact the department."
        ]
    },
    "linguistics": {
        "id": "linguistics", "name": "Linguistics Minor",
        "groups": [
            {"label": "Core and approved linguistics-related courses (choose 6)", "type": "choose_n_of",
             "count": 6, "options": [
                "AMST_UN3931", "ENGL_GU4901", "LING_UN3101", "LING_UN3103", "LING_GU4108",
                "LING_GU4120", "LING_GU4171", "LING_GU4190", "LING_GU4376", "LING_GU4800",
                "LING_GU4903", "ANTH_UN1009", "CHNS_GU4019", "COMS_W4705", "CPLS_GU4111",
                "HNGR_UN3343", "PHIL_UN2685", "PHIL_UN3411", "PHIL_UN3685", "PHIL_GU4490",
                "PSYC_UN2215", "PSYC_UN2440", "PSYC_UN2450", "PSYC_BC3164", "PSYC_BC3369",
                "PSYC_GU4232", "SPAN_BC3382", "SPAN_GU4010"
             ], "notes": [
                "A cross-department course needs program approval; this list reflects previously "
                "approved courses per the bulletin and may not be exhaustive."
             ]}
        ],
        "notes": []
    },
    "middle_eastern_south_asian_african_studies": {
        "id": "middle_eastern_south_asian_african_studies",
        "name": "Middle Eastern, South Asian, and African Studies Minor",
        "unstructured": True,
        "description": (
            "Five courses, chosen with approval of the MESAAS Director of Undergraduate "
            "Studies; no elementary or intermediate language courses may count. No fixed "
            "course list is given."
        ),
        "notes": []
    },
    "materials_science": {
        "id": "materials_science", "name": "Materials Science Minor",
        "groups": [
            {"label": "MSAE 3000/4000-level courses (choose 5)", "type": "subject_level_count",
             "subjects": ["MSAE"], "min_level": 3000, "max_level": 4999, "count": 5,
             "exclude": ["MSAE_E3900", "MSAE_E3156", "MSAE_E3157", "MSAE_E4301"]}
        ],
        "notes": []
    },
    "mechanical_engineering": {
        "id": "mechanical_engineering", "name": "Mechanical Engineering Minor",
        "groups": [
            {"label": "Choose four", "type": "choose_n_of", "count": 4, "options": [
                "MECE_E3100", "ENME_E3161", "CHEN_E3110", "EAEE_E3200", "ENME_E3105",
                "ENME_E3106", "MECE_E3301", "CHEE_E3010", "MSAE_E3111", "MECE_E3414",
                "MECE_E3408", "MECE_E3311", "MECE_E3610", "EEME_E3601"
            ]},
            {"label": "Additional ME electives (choose 2)", "type": "subject_level_count",
             "subjects": ["MECE"], "count": 2,
             "notes": ["May reuse the list above, MECE_E3401/E3450, or any 3-credit 4000-level ME Bulletin course; not all courses are offered every year."]}
        ],
        "notes": []
    },
    "mining_engineering": {
        "id": "mining_engineering", "name": "Mining Engineering Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["EAEE_E3103", "EAEE_E4200"]},
            {"label": "Choose two", "type": "choose_n_of", "count": 2, "options": [
                "EACE_E3255", "EAEE_E4160", "EAEE_E4150", "CHEE_E4252", "EACE_E4252", "CIEE_E4257"
            ]},
            {"label": "Choose two", "type": "choose_n_of", "count": 2, "options": [
                "EAEE_E4002", "EAEE_E4009", "EAEE_E4100", "CHEE_E3010", "EAEE_E4257",
                "CHEN_E3110", "EACH_E4560"
            ]}
        ],
        "notes": []
    },
    "music": {
        "id": "music", "name": "Music Minor",
        "groups": [
            {"label": "Choose one", "type": "choose_one_of", "options": ["MUSI_UN2318", "MUSI_UN2319"]},
            {"label": "Choose one", "type": "choose_one_of", "options": ["MUSI_UN3128", "MUSI_UN3129", "MUSI_UN3400"]},
            {"label": "Electives (3, chosen with the Music DUS)", "type": "free_form", "description": (
                "Three nontechnical electives chosen with the Music DUS; up to 6 of the 15 "
                "total credits may be performance (lessons/ensembles, by audition); excludes "
                "Music Hum courses."
            )}
        ],
        "notes": ["Music Performance Program credits do not count toward the 128 graduation credits."]
    },
    "operations_research": {
        "id": "operations_research", "name": "Operations Research Minor",
        "groups": [
            {"label": "Probability/statistics", "type": "choose_one_of",
             "options": ["IEOR_E3658", "STAT_GU4001", "STAT_GU4203"]},
            {"label": "Required courses", "type": "all_of",
             "options": ["IEOR_E3106", "IEOR_E3608", "IEOR_E3404"]},
            {"label": "IEOR/ORCS/CSOR 3000+ electives (choose 2)", "type": "subject_level_count",
             "subjects": ["IEOR", "ORCS", "CSOR"], "min_level": 3000, "count": 2}
        ],
        "notes": [
            "18 credits total.",
            "Industrial Engineering majors need 3 additional IEOR electives not used for their major."
        ]
    },
    "philosophy": {
        "id": "philosophy", "name": "Philosophy Minor",
        "groups": [
            {"label": "Philosophy department courses (choose 5)", "type": "subject_level_count",
             "subjects": ["PHIL"], "count": 5}
        ],
        "notes": ["No distribution requirement; total 15 points.", "Some PHIL courses may not count as nontechnical electives."]
    },
    "political_science": {
        "id": "political_science", "name": "Political Science Minor",
        "groups": [
            {"label": "Intro courses (choose 2)", "type": "choose_n_of", "count": 2, "options": [
                "POLS_UN1101", "POLS_UN1201", "POLS_UN1501", "POLS_UN1601"
            ]},
            {"label": "Political Science department courses (choose 3)", "type": "subject_level_count",
             "subjects": ["POLS"], "count": 3}
        ],
        "notes": ["No distribution requirement; total 9 points beyond the intro courses."]
    },
    "portuguese": {
        "id": "portuguese", "name": "Portuguese Minor",
        "groups": [
            {"label": "Choose one", "type": "choose_one_of", "options": ["PORT_UN2102", "PORT_UN2120"]},
            {"label": "4 courses at the 3000+ level (rotating)", "type": "choose_n_of", "count": 4, "options": [
                "PORT_UN3300", "PORT_UN3101", "PORT_UN3301", "PORT_UN3330", "PORT_UN3350",
                "PORT_UN3601", "PORT_GU4033"
            ]}
        ],
        "notes": [
            "Prerequisite: 3 semesters of Portuguese (PORT_UN1101, PORT_UN1102, PORT_UN2101) or "
            "placement equivalent.",
            "Students who test out of PORT_UN2102 have several substitution options (other LAIC "
            "language courses, study abroad, or an outside-LAIC elective) not modeled here."
        ]
    },
    "psychology": {
        "id": "psychology", "name": "Psychology Minor",
        "groups": [
            {"label": "Intro course", "type": "all_of", "options": ["PSYC_UN1001"]},
            {"label": "4 courses from at least 2 of 3 groups", "type": "free_form", "description": (
                "Perception and Cognition (2200s/3200s/4200s), Psychobiology and Neuroscience "
                "(PSYC_UN2430 plus 2400s/3400s/4400s), and Social/Personality/Abnormal "
                "(2600s/3600s/4600s) -- a course-numbering-range rule this app has no general "
                "mechanism for."
            )}
        ],
        "notes": []
    },
    "religion": {
        "id": "religion", "name": "Religion Minor",
        "groups": [
            {"label": "Religion department courses (choose 5)", "type": "subject_level_count",
             "subjects": ["RELI"], "count": 5}
        ],
        "notes": ["Total 15 points.", "At least one course must be at the 2000 level -- not separately enforced here."]
    },
    "sociology": {
        "id": "sociology", "name": "Sociology Minor",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["SOCI_UN1000", "SOCI_UN3000"]},
            {"label": "Sociology department courses (choose 3)", "type": "subject_level_count",
             "subjects": ["SOCI"], "min_level": 2000, "count": 3}
        ],
        "notes": []
    },
    "statistics_legacy": {
        "id": "statistics_legacy", "name": "Statistics Minor (legacy, pre-2026-2027)",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": [
                "STAT_UN1101", "STAT_UN2102", "STAT_UN2103", "STAT_UN2104", "STAT_UN3105", "STAT_UN3106"
            ]}
        ],
        "notes": [
            "Superseded for students declaring in 2026-2027 or later, and for the Class of 2029+ "
            "-- see the Applied Track / Theory Track minors instead.",
            "A theory-oriented substitution list also existed: STAT_GU4203/4204/4205/4206/4207.",
            "Up to two courses may count toward both this minor and another Engineering major, "
            "with DUS permission."
        ]
    },
    "statistics_applied_track": {
        "id": "statistics_applied_track", "name": "Statistics Minor -- Applied Track",
        "groups": [
            {"label": "Required courses", "type": "all_of", "options": ["STAT_UN1101", "STAT_UN2102", "STAT_UN2103"]},
            {"label": "Choose two", "type": "choose_n_of", "count": 2, "options": [
                "STAT_UN2104", "STAT_UN3104", "STAT_UN3105", "STAT_UN3106", "STAT_UN3702"
            ]}
        ],
        "notes": ["For students declaring in 2026-2027 or later, and the Class of 2029+."]
    },
    "statistics_theory_track": {
        "id": "statistics_theory_track", "name": "Statistics Minor -- Theory Track",
        "groups": [
            {"label": "Required courses", "type": "all_of",
             "options": ["STAT_UN1201", "STAT_GU4203", "STAT_GU4204", "STAT_GU4205"]},
            {"label": "Choose one", "type": "choose_one_of", "options": ["STAT_GU4207", "STAT_GU4241"],
             "notes": ["Or an approved Statistics Department elective numbered 4000+."]}
        ],
        "notes": [
            "For students declaring in 2026-2027 or later, and the Class of 2029+.",
            "STAT_UN1201 may be substituted with an advanced elective with advisor permission."
        ]
    },
    "sustainable_engineering": {
        "id": "sustainable_engineering", "name": "Sustainable Engineering Minor",
        "groups": [
            {"label": "Choose four", "type": "choose_n_of", "count": 4, "options": [
                "EAEE_E2002", "EAEE_E2100", "EACE_E3250", "CIEE_E3260", "EAEE_E3901",
                "EAEE_E4001", "ECIA_W4100", "APPH_E4130", "EAEE_E4190", "MECE_E4211",
                "EAEE_E4257", "EESC_GU4404", "MECE_E4350", "MECE_E4313", "MECE_E4612"
            ]},
            {"label": "Choose one (economics/policy)", "type": "choose_one_of", "options": [
                "ECON_UN2257", "PLAN_A4151", "PLAN_A4304", "ECON_GU4321", "ECON_GU4527",
                "PLAN_A4579", "ECON_GU4625"
            ]},
            {"label": "Choose one (politics/society)", "type": "choose_one_of", "options": [
                "POLS_UN3212", "POLS_UN3213", "SOCI_UN3235", "SOCI_UN3324"
            ]}
        ],
        "notes": ["Six courses total; no substitutions allowed except an approved similar course from the Sustainable Development bulletin's Economics or Law/Policy/Human Rights groups."]
    },
    "womens_gender_sexuality_studies": {
        "id": "womens_gender_sexuality_studies", "name": "Women's, Gender and Sexuality Studies Minor",
        "groups": [
            {"label": "Choose one", "type": "choose_one_of", "options": ["WMST_UN1001", "WMST_UN3125"]},
            {"label": "WMST 2000+ electives (choose 4)", "type": "subject_level_count",
             "subjects": ["WMST"], "min_level": 2000, "count": 4,
             "notes": ["Also allows courses cross-listed at ISSG, not enumerated here."]}
        ],
        "notes": ["Five courses, 15-20 points total.", "No prerequisites; the required course may be taken concurrently with electives."]
    }
}

# (subject, number, title) for referenced courses not already in the catalog.
NEW_COURSES = [
    ("AEME", "E4304", "Turbomachinery"),
    ("AEME", "E4305", "Propulsion"),
    ("AEME", "E4306", "Intro to Aerodynamics"),
    ("AFAS", "UN1001", "INTRO TO AFRICAN-AMER STUDIES"),
    ("AMST", "UN1010", "INTRO TO AMERICAN STUDIES"),
    ("AMST", "UN3931", "Topics in American Studies"),
    ("ANTH", "UN1002", "THE INTERPRETATION OF CULTURE"),
    ("ANTH", "UN1008", "THE RISE OF CIVILIZATION"),
    ("ANTH", "UN1009", "INTRO TO LANGUAGE & CULTURE"),
    ("APPH", "E4018", "APPLIED PHYSICS LABORATORY"),
    ("APPH", "E4130", "SOLAR ENERGY & STORAGE"),
    ("APPH", "E4200", "PHYSICS OF FLUIDS"),
    ("APPH", "E6101", "PLASMA PHYSICS I"),
    ("APPH", "E6102", "PLASMA PHYSICS II"),
    ("ASCE", "UN1359", "INTRO TO EAST ASIAN CIV: CHINA"),
    ("ASCE", "UN1361", "INTRO EAST ASIAN CIV: JPN"),
    ("ASCE", "UN1363", "INTRO TO EAST ASIAN CIV: KOREA"),
    ("ASCE", "UN1365", "INTRO EAST ASIAN CIV: TIBET"),
    ("ASCE", "UN1367", "INTRO EA CIV: VIETNAM"),
    ("CATL", "UN1120", "COMPREHENSIVE BEG CATALAN"),
    ("CATL", "UN2101", "INTERMEDIATE CATALAN I"),
    ("CATL", "UN2102", "INTERMEDIATE CATALAN II"),
    ("CATL", "UN3300", "ADVANCED CATALAN"),
    ("CATL", "UN3500", "Literature in Catalan Cinema"),
    ("CBMF", "W4761", "COMPUTATIONAL GENOMICS"),
    ("CHNS", "GU4019", "HISTORY OF CHINESE LANGUAGE"),
    ("CIEE", "E3260", "ENGINEERING FOR COMMUNITY DEVELOPMENT"),
    ("CIEE", "E4257", "GROUND CONT TRANSP & REMED"),
    ("CIEN", "E3000", "THE ART OF STRUCTURAL DESIGN"),
    ("CIEN", "E3121", "STRUCTURAL ANALYSIS"),
    ("CIEN", "E3125", "STRUCTURAL DESIGN"),
    ("CIEN", "E3129", "PROJECT MGMT FOR CONSTRUCTION"),
    ("CIEN", "E4131", "PRIN OF CONSTRUCTN TECHNIQUES"),
    ("CIEN", "E4136", "Entrepreneurship in Engineering and Construction"),
    ("CIEN", "E4241", "GEOTECHNCL ENGNEERNG FUNDMNTLS"),
    ("CIEN", "E4253", "COMP SOLID MECHANICS WITH AI"),
    ("CIEN", "E4256", "Applied Machine Learning in Civil Engineering"),
    ("CLYD", "UN3500", "READINGS IN JEWISH LITERATURE"),
    ("CLYD", "GU4250", "Memory and Trauma in Yiddish Literature (in English)"),
    ("COMS", "W1002", "COMPUTING IN CONTEXT"),
    ("COMS", "W1004", "PROGRAMMING IN JAVA"),
    ("COMS", "W1007", None),
    ("COMS", "W2132", "Intermediate Computing in Python"),
    ("COMS", "W2702", "AI in Context"),
    ("COMS", "W3134", "Data Structures in Java"),
    ("COMS", "W3137", "HONORS DATA STRUCTURES & ALGOL"),
    ("COMS", "W3157", "ADVANCED PROGRAMMING"),
    ("COMS", "W3203", "DISCRETE MATHEMATICS"),
    ("COMS", "W3251", "COMPUTATIONAL LINEAR ALGEBRA"),
    ("COMS", "W3261", "COMPUTER SCIENCE THEORY"),
    ("COMS", "W4170", "USER INTERFACE DESIGN"),
    ("COMS", "W4444", "PROGRAMMING & PROBLEM SOLVING"),
    ("COMS", "W4460", "PRIN-INNOVATN/ENTREPRENEURSHIP"),
    ("COMS", "W4701", "ARTIFICIAL INTELLIGENCE"),
    ("COMS", "W4705", "NATURAL LANGUAGE PROCESSING"),
    ("COMS", "W4710", "Ethical and Responsible AI"),
    ("COMS", "BC3420", "PRIVACY IN A NETWORKED WORLD"),
    ("COMS", "BC3707", "LARGE LANGUAGE MODELS: FOUNDATIONS AND ETHICS"),
    ("CPLS", "GU4111", "World Philology"),
    ("CSEE", "W3827", "FUNDAMENTALS OF COMPUTER SYSTS"),
    ("CSER", "UN1010", "INTRO TO COMP ETHNIC STUDIES"),
    ("CSER", "UN3928", "COLONIZATION/DECOLONIZATION"),
    ("CSER", "UN3940", "COMP STUDY OF CONSTITUTNL CHAL"),
    ("CSER", "UN3942", "RACE AND RACISMS"),
    ("EACE", "E3250", "Hydrosystems Engineering"),
    ("EACE", "E3255", "ENVIRONMENTAL CONTROL AND POLLUTION REDUCTION"),
    ("EACE", "E4163", "Sustainable Water Treatment and Reuse"),
    ("EACE", "E4252", "Foundations of Environmental Engineering"),
    ("EACH", "E4560", "Particle technology and multiphase reactor design"),
    ("EAEE", "E2002", None),
    ("EAEE", "E3901", "ENVIRONMENTAL MICROBIOLOGY"),
    ("EAEE", "E4001", "INDUST ECOLOGY-EARTH RESOURCES"),
    ("EAEE", "E4009", "GIS-RES,ENVIR,INFRASTRUCTR MGT"),
    ("EAEE", "E4100", "A Better Planet by Design (MS)"),
    ("EAEE", "E4150", "AIR POLLUTION PREVENTION/CONTR"),
    ("EAEE", "E4160", "SOLID & HAZARDOUS WASTE MGMT"),
    ("EAEE", "E4190", "PHOTOVOLTAIC SYSTEMS ENGIN"),
    ("EAEE", "E4200", "Introduction to Sustainable Production of Earth Mineral & Metal Resources"),
    ("EAEE", "E4257", "ENVIR DATA ANALYSIS & MODELING"),
    ("ECBM", "E4040", "NEURAL NETWRKS & DEEP LEARNING"),
    ("ECIA", "W4100", "MGMT & DEVPT OF WATER SYSTEMS"),
    ("ECON", "UN2105", "THE AMERICAN ECONOMY"),
    ("ECON", "UN2257", "THE GLOBAL ECONOMY"),
    ("ECON", "UN3025", "FINANCIAL ECONOMICS"),
    ("ECON", "UN3211", "INTERMEDIATE MICROECONOMICS"),
    ("ECON", "UN3213", "INTERMEDIATE MACROECONOMICS"),
    ("ECON", "UN3265", "MONEY AND BANKING"),
    ("ECON", "UN3412", "INTRODUCTION TO ECONOMETRICS"),
    ("ECON", "UN3901", "ECONOMICS OF EDUCATION"),
    ("ECON", "UN3952", "MACROECONOMICS & FORMATION OF EXPECTATIONS"),
    ("ECON", "GU4020", "ECON OF UNCERTAINTY & INFORMTN"),
    ("ECON", "GU4211", "ADVANCED MICROECONOMICS"),
    ("ECON", "GU4213", "ADVANCED MACROECONOMICS"),
    ("ECON", "GU4230", "ECONOMICS OF NEW YORK CITY"),
    ("ECON", "GU4251", "INDUSTRIAL ORGANIZATION"),
    ("ECON", "GU4260", "MARKET DESIGN"),
    ("ECON", "GU4301", "ECONOMIC GROWTH & DEVELOPMNT I"),
    ("ECON", "GU4321", "ECONOMIC DEVELOPMENT"),
    ("ECON", "GU4370", "POLITICAL ECONOMY"),
    ("ECON", "GU4400", "LABOR ECONOMICS"),
    ("ECON", "GU4412", "ADVANCED ECONOMETRICS"),
    ("ECON", "GU4413", "Econometrics of Time Series and Forecasting"),
    ("ECON", "GU4415", "GAME THEORY"),
    ("ECON", "GU4438", "ECONOMICS OF RACE IN THE U.S."),
    ("ECON", "GU4465", "PUBLIC ECONOMICS"),
    ("ECON", "GU4480", "GENDER & APPLIED ECONOMICS"),
    ("ECON", "GU4500", "INTERNATIONAL TRADE"),
    ("ECON", "GU4505", "INTERNATIONAL MACROECONOMICS"),
    ("ECON", "GU4527", "ECON ORG & DEVELOPMNT OF CHINA"),
    ("ECON", "GU4625", "ECONOMICS OF THE ENVIRONMENT"),
    ("ECON", "GU4700", "FINANCIAL CRISES"),
    ("ECON", "GU4710", "FINANCE AND THE REAL ECONOMY"),
    ("ECON", "GU4750", "GLOBALIZATION & ITS RISKS"),
    ("ECON", "GU4840", "BEHAVIORAL ECONOMICS"),
    ("ECON", "GU4850", "COGNITIVE MECH & ECON BEHAVIOR"),
    ("ECON", "GU4860", "BEHAVIORAL FINANCE"),
    ("EEME", "E3601", "Introduction to Continuous Control Systems"),
    ("EEME", "E4601", "DISCRETE CONTROL SYSTEMS"),
    ("EECS", "E4764", "Artificial Intelligence of Things (AIoT)"),
    ("ELEN", "E1201", "INTRO-ELECTRICAL ENGINEERING"),
    ("ELEN", "E3081", "CIRCUIT ANALYSIS LABORATORY"),
    ("ELEN", "E3082", "DIGITAL SYSTEMS LABORATORY"),
    ("ELEN", "E3106", "SOLID STATE DEVICES-MATERIALS"),
    ("ELEN", "E3201", "CIRCUIT ANALYSIS"),
    ("ELEN", "E3401", "ELECTROMAGNETICS"),
    ("ELEN", "E3701", "INTRO TO COMMUNICATION SYSTEMS"),
    ("ELEN", "E3801", "SIGNALS AND SYSTEMS"),
    ("ELEN", "E4361", "POWER ELECTRONICS"),
    ("ELEN", "E4720", "Machine Learning for Signals, Information and Data"),
    ("ELEN", "E4730", "Quantum Optimization and Machine Learning"),
    ("ELEN", "E4810", "DIGITAL SIGNAL PROCESSING"),
    ("ENGI", "E4502", "Design of UI/UX for Connected Systems"),
    ("ENGL", "UN2826", "American Modernism"),
    ("ENGL", "BC3180", "AMERICAN LITERATURE 1800-1870"),
    ("ENGL", "BC3183", "AMERICAN LITERATURE SINCE 1945"),
    ("ENGL", "UN3241", "African American Literature: The Essay"),
    ("ENGL", "UN3351", "FAMILY FICTIONS: MEMOIR, FILM AND THE NOVEL"),
    ("ENGL", "UN3832", "New York Intellectuals: Mary McCarthy, Hannah Arendt, Susan Sontag"),
    ("ENGL", "GU4901", "HISTORY OF THE ENGLISH LANGUAGE"),
    ("ENGL", "GU4938", "HISTORY OF HORROR CINEMA"),
    ("ENME", "E3105", "MECHANICS"),
    ("ENME", "E3106", "DYNAMICS AND VIBRATIONS"),
    ("ENME", "E3113", "MECHANICS OF SOLIDS"),
    ("ENME", "E3114", "EXPERIMENTAL MECH OF MATERIALS"),
    ("ENME", "E3161", "FLUID MECHANICS"),
    ("ENME", "E3332", "A FIRST CRSE/FINITE ELEMENTS"),
    ("ENME", "E4113", "ADVANCED MECHANICS OF SOLIDS"),
    ("ENME", "E4114", "MECHANCS OF FRACTURE & FATIGUE"),
    ("ENME", "E4117", "Mechanics of Fiber-Reinforced Composites"),
    ("ENME", "E4202", "ADVANCED MECHANICS"),
    ("ENME", "E4214", "THEORY OF PLATES AND SHELLS"),
    ("ENME", "E4215", "THEORY OF VIBRATIONS"),
    ("FILM", "UN1000", "INTRO TO FILM & MEDIA STUDIES"),
    ("FILM", "UN2010", "CINEMA HIST I: BEGIN-1930"),
    ("FILM", "UN2020", "CINEMA HIST II: 1930-1960"),
    ("FILM", "UN2030", "CINEMA HIST III:1960-1990"),
    ("FILM", "UN2040", "CINEMA HISTORY IV: AFTER 1990"),
    ("FILM", "UN2410", "LAB IN WRITING FILM CRITICISM"),
    ("FILM", "UN2420", "LABORATORY IN SCREENWRITING"),
    ("FILM", "UN2510", "LAB IN FICTION FILMMAKING"),
    ("FILM", "UN2520", "LAB IN NONFICTION FILMMAKING"),
    ("FREN", "UN3405", "Read, Think, Write in French"),
    ("FREN", "UN3409", "INTRO TO FRENCH & FRANCOPHONE HISTORY"),
    ("FREN", "UN3410", "Intro French & Francophone Literature"),
    ("GERM", "UN3333", "INTRO TO GERMAN LIT (GERMAN)"),
    ("HIST", "UN1488", "Indigenous History of North America"),
    ("HIST", "UN1512", "The Battle for North America"),
    ("HIST", "UN2432", "US ERA OF CIVIL WAR & RECON"),
    ("HIST", "UN2523", "HEALTH INEQUALITY: MODERN US"),
    ("HIST", "UN2533", "US LESBIAN & GAY HISTORY"),
    ("HIST", "UN2535", "HIST OF THE CITY OF NEW YORK"),
    ("HIST", "UN2540", "HISTORY OF THE SOUTH"),
    ("HIST", "UN2565", "American History at the Movies"),
    ("HIST", "UN2587", "SPORT & SOCIETY IN THE AMERICAS"),
    ("HIST", "UN2611", "JEWS & JUDAISM IN ANTIQUITY"),
    ("HIST", "UN2679", "Atlantic Slave Trade"),
    ("HIST", "UN3501", "Indians and Empires in North America"),
    ("HIST", "UN3604", "Jews and the City"),
    ("HIST", "GU4518", "Research Seminar: Columbia and Slavery"),
    ("HIST", "GU4525", "Immigrant New York"),
    ("HIST", "GU4933", "American Radicalism in the Archives"),
    ("HNGR", "UN3343", "DESCRIPTIVE GRAMMAR-HUNGARIAN"),
    ("IEME", "E4200", "HUMAN-CENTERED DESIGN AND INNOVATION"),
    ("IEME", "E4505", "Frontiers of Tough Tech"),
    ("IEOR", "E2000", "Data Engineering with Python"),
    ("IEOR", "E2261", "ACCOUNTING AND FINANCE"),
    ("IEOR", "E3106", "STOCHASTIC SYSTEMS AND APPLICATIONS"),
    ("IEOR", "E3402", "PRODUCTN-INVENTORY PLAN-CONTRL"),
    ("IEOR", "E3404", "SIMULATION MODELING AND ANALYSIS"),
    ("IEOR", "E3608", "FOUNDATIONS OF OPTIMIZATION"),
    ("IEOR", "E4003", "CORPORATE FINANCE FOR ENGINEERS"),
    ("IEOR", "E4207", "HUMAN FACTORS: PERFORMANCE"),
    ("IEOR", "E4212", "Data Analytics & Machine Learning for OR"),
    ("IEOR", "E4510", "PROJECT MANAGEMENT"),
    ("IEOR", "E4540", "DATA MINING"),
    ("IEOR", "E4998", "MANAG TECH INNOV & ENTREPRENEURSHIP"),
    ("ITAL", "UN3232", "ITALY:EMIGRATION-IMMIGRATION"),
    ("ITAL", "UN3333", "INTRO TO ITALIAN LITERATURE I"),
    ("ITAL", "UN3334", "INTRO TO ITALIAN LITERATURE II"),
    ("ITAL", "UN3335", "ADVANCED ITALIAN I"),
    ("ITAL", "UN3337", "ITALIAN THROUGH CINEMA"),
    ("ITAL", "UN3338", "Italiana: Introduction to Italian Culture"),
    ("ITAL", "UN3339", "Learning Italian in Class and Online"),
    ("ITAL", "UN3341", "Art Itineraries: Italian through Art"),
    ("ITAL", "UN3342", "Business Italian and the Made in Italy Excellence"),
    ("ITAL", "UN3343", "ADVANCED ITALIAN: COMPARATIVE STYLISTICS AND TRANSLATION"),
    ("ITAL", "UN3645", "Grand Tour in Italy"),
    ("ITAL", "GU4502", "ITALIAN CULTURAL STUDIES I"),
    ("ITAL", "GU4503", "ITL CULTRL ST II:WWI-PRESENT"),
    ("JWST", "UN2155", "Music, Sound, and Antisemitism"),
    ("JWST", "GU4145", "Topics in Israeli Cinema"),
    ("JWST", "GU4147", "Between Tradition & Innovation"),
    ("JWST", "GU4149", "A History of Jewish-Muslim Encounters"),
    ("JWST", "GU4153", "U.S. Civil and Human Rights Lawyers"),
    ("JWST", "GU4154", "Magic in Jewish History and Culture"),
    ("JWST", "GU4156", "An Introduction to World Zionist Thought"),
    ("JWST", "GU4157", "Israeli Politics in Times of Turmoil"),
    ("JWST", "GU4990", "Topics in Jewish Studies"),
    ("LING", "UN3101", "INTRODUCTION TO LINGUISTICS"),
    ("LING", "UN3103", "Language, Brain and Mind"),
    ("LING", "GU4108", "LANGUAGE HISTORY"),
    ("LING", "GU4120", "LANG DOCUMENTATION/FIELD MTHDS"),
    ("LING", "GU4171", "LANGUAGES OF AFRICA"),
    ("LING", "GU4190", "DISCOURSE ANALYSIS"),
    ("LING", "GU4376", "PHONETICS & PHONOLOGY"),
    ("LING", "GU4800", "LANGUAGE & SOCIETY"),
    ("LING", "GU4903", "SYNTAX"),
    ("MACH", "E4320", "Intro to Combustion"),
    ("MECE", "E3100", "INTRO TO MECHANCIS OF FLUIDS"),
    ("MECE", "E3301", "THERMODYNAMICS"),
    ("MECE", "E3311", "HEAT TRANSFER"),
    ("MECE", "E3401", "MECHANICS OF MACHINES"),
    ("MECE", "E3408", "COMPUTER GRAPHICS & DESIGN"),
    ("MECE", "E3414", "Mechanics of Solids for Mechanical Engineers"),
    ("MECE", "E3450", "COMPUTER AIDED DESIGN"),
    ("MECE", "E3610", "MATERIALS/PROCESSES IN MANUFAC"),
    ("MECE", "E4211", "ENERGY SOURCES AND CONVERSION"),
    ("MECE", "E4302", "ADVANCED THERMODYNAMICS"),
    ("MECE", "E4313", "Decarbonizing Buildings Studio"),
    ("MECE", "E4350", "Building Energy Modeling and Simulation"),
    ("MECE", "E4461", "Materials Selection for Mechanical Design"),
    ("MECE", "E4520", "DATA SCIENCE FOR MECHANICAL SYSTEMS"),
    ("MECE", "E4602", "INTRODUCTION TO ROBOTICS"),
    ("MECE", "E4612", "SUSTAINABLE MANUFACTURING"),
    ("MECE", "E6102", "COMPUTATNL HEAT TRANSF-FL FLOW"),
    ("MECE", "E6106", "Finite Element Method for Fluid Flow and Fluid-Structure Interactions"),
    ("MECS", "E4603", "APPLIED ROBOTICS: ALGORITHMS & SOFTWARE"),
    ("MSAE", "E3010", "FOUNDATIONS OF MATERIALS SCIENCE"),
    ("MSAE", "E3111", "THERMO/KINETIC THRY/STAT MECH"),
    ("MSAE", "E4090", "NANOTECHNOLOGY"),
    ("MSAE", "E4206", "ELEC & MAGNETIC PROP OF SOLIDS"),
    ("MSAE", "E4215", "MECH BEHAVIOR OF MATERIALS"),
    ("MSAE", "E4260", "ELECTROCHEM MATLS & DEVS"),
    ("MUSI", "UN2318", "MUSIC THEORY I"),
    ("MUSI", "UN2319", "MUSIC THEORY II"),
    ("MUSI", "UN3128", "History of Western Music: Middle Ages to Baroque"),
    ("MUSI", "UN3129", "History of Western Music: Classical Era to 20th Century"),
    ("MUSI", "UN3400", "TOPICS IN MUSIC & SOCIETY"),
    ("MUSI", "GU4113", "Medieval Mediterranean Love Songs"),
    ("ORCS", "E4200", "Data-driven Decision Modeling"),
    ("ORCS", "E4201", "Policy for Privacy Technologies"),
    ("ORCS", "E4529", "Reinforcement Learning"),
    ("PHIL", "UN2685", "INTRO TO PHIL OF LANGUAGE"),
    ("PHIL", "UN3411", "SYMBOLIC LOGIC"),
    ("PHIL", "UN3685", "PHILOSOPHY OF LANGUAGE"),
    ("PHIL", "GU4490", "LANGUAGE AND MIND"),
    ("PLAN", "A4151", "ECONOMICS FOR PLANNERS"),
    ("PLAN", "A4304", "INTRODUCTION TO HOUSING"),
    ("PLAN", "A4579", "Introduction to Environmental Planning"),
    ("POLS", "UN1101", "POLITICAL THEORY I"),
    ("POLS", "UN1201", "INTRO TO AMERICAN POLITICS"),
    ("POLS", "UN1501", "INTRO TO COMPARATIVE POLITICS"),
    ("POLS", "UN1601", "INTERNATIONAL POLITICS"),
    ("POLS", "UN3100", "JUSTICE"),
    ("POLS", "UN3212", None),
    ("POLS", "UN3213", "AMERICAN URBAN POLITICS"),
    ("POLS", "UN3222", "THE AMERICAN CONGRESS"),
    ("POLS", "UN3255", "RACE AND THE US CARCERAL SYSTEM"),
    ("POLS", "UN3290", "VOTING AND AMERICAN POLITICS"),
    ("POLS", "GU4728", "Machine Learning & AI for the Social Sciences"),
    ("PORT", "UN1101", "ELEMENTARY PORTUGUESE I"),
    ("PORT", "UN1102", "ELEMENTARY PORTUGUESE II"),
    ("PORT", "UN1320", "COMP ELEM PORT I/II-SPAN SPKRS"),
    ("PORT", "UN2101", "INTERMEDIATE PORTUGUESE I"),
    ("PORT", "UN2102", "Intermed. Portuguese II"),
    ("PORT", "UN2120", "COMPREHENSIVE INTERMED PORT"),
    ("PORT", "UN3101", "CONVERS ABOUT LUSOPHONE WORLD"),
    ("PORT", "UN3300", "ADV LANGUAGE THROUGH CONTENT"),
    ("PORT", "UN3301", "Advanced Writing and Composition in Portuguese"),
    ("PORT", "UN3330", "INTRO TO PORTUGUESE STUDIES"),
    ("PORT", "UN3350", "LUSOPHONE AFR/AFRO-BRAZ CULTRS"),
    ("PORT", "UN3601", "Race, Medicine and Literature in 19th-Century Brazil"),
    ("PORT", "GU4033", "Language & Queer Brazil (ENG)"),
    ("PSYC", "UN1001", "THE SCIENCE OF PSYCHOLOGY"),
    ("PSYC", "UN2215", "Cognition and the Brain"),
    ("PSYC", "UN2430", "COGNITIVE NEUROSCIENCE"),
    ("PSYC", "UN2440", "Language and the Brain"),
    ("PSYC", "UN2450", "BEHAVIORAL NEUROSCIENCE"),
    ("PSYC", "BC3164", "PERCEPTION AND LANGUAGE"),
    ("PSYC", "BC3369", "LANGUAGE DEVELOPMENT"),
    ("PSYC", "GU4232", "Production and Perception of Language"),
    ("PSYC", "GU4836", "Machine Intelligence"),
    ("RELI", "UN1612", "Religion and the History of Hip Hop"),
    ("RELI", "UN2306", "INTRO TO JUDAISM"),
    ("RELI", "V3301", "Hebrew Bible"),
    ("RELI", "GU4217", "American Religions in extremis"),
    ("RELI", "GU4509", "CRIME/PUNISHMENT-JEWISH CULTRE"),
    ("SOCI", "UN1000", "THE SOCIAL WORLD"),
    ("SOCI", "UN3000", "SOCIAL THEORY"),
    ("SOCI", "UN3235", "Social Movements"),
    ("SOCI", "UN3265", "SOCIOLOGY OF WORK & GENDER"),
    ("SOCI", "UN3285", "ISRAELI SOC & ISR-PLS CONFLICT"),
    ("SOCI", "UN3324", "Global Urbanism"),
    ("SOCI", "GU4801", "Israel and the Palestinians"),
    ("SPAN", "UN3300", "ADV LANGUAGE THROUGH CONTENT"),
    ("SPAN", "UN3349", "HISPANIC CULTURES I (SP)"),
    ("SPAN", "UN3350", "HISPANIC CULTURES II (SP)"),
    ("SPAN", "BC3382", "SOCIOLING ASPECTS U.S.SPANISH"),
    ("SPAN", "GU4010", "LANGUAGE CROSSING IN LATINX CARIBBEAN CULTURAL PRODUCTION"),
    ("SPJS", "UN3303", "JEWISH CULTURE IN TRANSL IN MED IBERIA"),
    ("WMST", "UN1001", "INTRO-WOMEN & GENDER STUDIES"),
    ("WMST", "UN3125", "INTRO TO SEXUALITY STUDIES"),
    ("WMST", "GU4336", "GENDER AND SEXUALITY IN YIDDISH LITERATURE"),
    ("YIDD", "UN3500", "SURVEY OF YIDDISH LIT (ENG)"),
    ("STAT", "UN1101", "INTRODUCTION TO STATISTICS"),
    ("STAT", "UN1201", "CALC-BASED INTRO TO STATISTICS"),
    ("STAT", "UN2102", "Applied Statistical Computing"),
    ("STAT", "UN2103", "APPLIED LINEAR REG ANALYSIS"),
    ("STAT", "UN2104", "APPL CATEGORICAL DATA ANALYSIS"),
    ("STAT", "UN3104", "Applied Bayesian Analysis"),
    ("STAT", "UN3105", "APPLIED STATISTICAL METHODS"),
    ("STAT", "UN3106", "APPLIED MACHINE LEARNING"),
    ("STAT", "UN3702", "Exploratory Data Analysis & Visualization"),
    ("STAT", "GU4203", "PROBABILITY THEORY"),
    ("STAT", "GU4204", "STATISTICAL INFERENCE"),
    ("STAT", "GU4205", "LINEAR REGRESSION MODELS"),
    ("STAT", "GU4207", "ELEMENTARY STOCHASTIC PROCESS"),
    ("STAT", "GU4241", "STATISTICAL MACHINE LEARNING"),
    ("STAT", "GU4242", "ADVANCED MACHINE LEARNING"),
    ("STAT", "GU4244", "Unsupervised Learning"),
    ("MATH", "UN2015", "Linear Algebra and Probability"),
    ("MATH", "UN2020", "Honors Linear Algebra"),
    ("BMEN", "E4480", "Statistical machine learning for genomics"),
    ("IEOR", "E3658", "PROBABILITY FOR ENGINEERS"),
    ("APPH", "E3300", "APPLIED ELECTROMAGNETISM"),
    ("APPH", "E4010", "INTRODUCTN TO NUCLEAR SCIENCE"),
    ("APPH", "E4301", "INTRO TO PLASMA PHYSICS"),
    ("EAEE", "E2100", "A BETTER PLANET BY DESIGN"),
    ("EAEE", "E3200", "TRANSPORT/CHEM RATE PHENOMENA"),
    ("CHEN", "E4020", "PROTECTN OF INDUST/INTELL PROP"),
    ("ECON", "GU4280", "CORPORATE FINANCE"),
    ("EESC", "GU4404", None),
    ("DNCE", "BC2563", "DANCE COMPOSITION: FORM"),
    ("DNCE", "BC2564", "DANCE COMPOSITION: CONTENT"),
    ("DNCE", "BC2567", "MUSIC FOR DANCE"),
    ("DNCE", "BC2570", "DANCE IN NEW YORK CITY"),
    ("DNCE", "BC3000", "FROM PAGE TO STAGE: DANCE & LITERATURE"),
    ("DNCE", "BC3001", "HISTORY OF THEATRICAL DANCING"),
    ("DNCE", "BC3002", "Choreographing Race in America"),
    ("DNCE", "BC3200", "DANCE IN FILM"),
    ("DNCE", "BC3240", "SEEING THE BODY"),
    ("DNCE", "BC3576", "DANCE CRITICISM"),
    ("DNCE", "BC3577", "Performing the Political"),
    ("DNCE", "BC3601", "REHEARSAL & PERFRMNCE IN DANCE"),
    ("DNCE", "BC3602", "Rehearsal and Performance in Dance"),
    ("DNCE", "BC3603", "Rehearsal and Performance in Dance"),
    ("DNCE", "BC3604", "REHEARSAL & PERFRMNCE IN DANCE"),
    ("DNCE", "BC3605", "REHEARSAL & PERFRMNCE IN DANCE"),
    ("DNCE", "BC3606", None),
    ("DNCE", "BC3607", "REHEARSAL & PERFRMNCE IN DANCE"),
]


def add_missing_courses():
    with open(MINOR_COURSES_TARGET, encoding="utf-8") as f:
        catalog = json.load(f)

    # check across all three catalogs to avoid re-adding a course that
    # already exists somewhere else
    existing_ids = set(catalog.keys())
    for path in CATALOG_FILES.values():
        if path == MINOR_COURSES_TARGET:
            continue
        with open(path, encoding="utf-8") as f:
            existing_ids.update(json.load(f).keys())

    added = []
    for subject, number, title in NEW_COURSES:
        course_id = f"{subject}_{number}"
        if course_id in existing_ids:
            continue

        catalog[course_id] = {
            "id": course_id, "subject": subject, "number": number, "title": title,
            "credits": None, "category_tags": [], "prerequisites": [], "corequisites": [],
            "aliases": [], "notes": [
                "Added from a Columbia Engineering undergraduate minor's course list "
                "(bulletin, fetched 2026-09-18). Not a ChemE technical elective."
            ]
        }
        added.append(course_id)

    with open(MINOR_COURSES_TARGET, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return added


def write_minors():
    MINORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MINORS_PATH, "w", encoding="utf-8") as f:
        json.dump({"global_rules": GLOBAL_MINOR_RULES, "minors": MINORS}, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    added = add_missing_courses()
    write_minors()
    print(f"Added {len(added)} new course(s) to {MINOR_COURSES_TARGET}")
    print(f"Wrote {MINORS_PATH} with {len(MINORS)} minors.")
