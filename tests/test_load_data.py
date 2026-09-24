from load_data import merge_courses, load_all_data


def make_course(course_id, **overrides):
    course = {
        "id": course_id, "subject": course_id.split("_")[0], "number": course_id.split("_")[1],
        "title": "Untitled", "credits": None, "category_tags": [],
        "prerequisites": [], "corequisites": [], "aliases": [], "notes": []
    }
    course.update(overrides)
    return course


def test_merge_courses_keeps_new_course_with_new_id():
    base = {}
    new = {"CHEN_E1000": make_course("CHEN_E1000")}

    result = merge_courses(base, new)

    assert "CHEN_E1000" in result


def test_merge_courses_folds_known_alias_into_canonical_entry():
    # Mirrors the real CHEM_3085/CHEM_UN3085 bug: the canonical course was
    # loaded first (from courses_core.json) and already knows its alias.
    # A later catalog that only has the alias id should merge into the
    # canonical entry, not create a second course.
    base = {
        "CHEM_UN3085": make_course(
            "CHEM_UN3085", credits=3, aliases=["CHEM_3085"],
            category_tags=["natural_science_lab_option"]
        )
    }
    new = {
        "CHEM_3085": make_course(
            "CHEM_3085", credits=None,
            category_tags=["technical_elective", "advanced_stem_tech_elective"]
        )
    }

    result = merge_courses(base, new)

    assert "CHEM_3085" not in result
    assert result["CHEM_UN3085"]["credits"] == 3
    assert set(result["CHEM_UN3085"]["category_tags"]) == {
        "natural_science_lab_option", "technical_elective", "advanced_stem_tech_elective"
    }


def test_merge_courses_does_not_overwrite_existing_credits():
    base = {"MATH_UN1101": make_course("MATH_UN1101", credits=3)}
    new = {"MATH_UN1101": make_course("MATH_UN1101", credits=999)}

    result = merge_courses(base, new)

    assert result["MATH_UN1101"]["credits"] == 3


def test_merge_courses_fills_missing_credits_from_duplicate():
    base = {"CHEM_UN3085": make_course("CHEM_UN3085", credits=None, aliases=["CHEM_3085"])}
    new = {"CHEM_3085": make_course("CHEM_3085", credits=3)}

    result = merge_courses(base, new)

    assert result["CHEM_UN3085"]["credits"] == 3


def test_load_all_data_returns_nonempty_real_catalogs():
    data = load_all_data()

    assert len(data["courses"]) > 0
    assert "requirements" in data["requirements"]
    assert "semesters" in data["template"]
    assert len(data["concentrations"]) == 4
    assert len(data["minors"]) > 0
    assert "credits_min" in data["minor_global_rules"]
    assert "chart" in data["ap_credit_chart"]


def test_known_alias_resolves_to_canonical_course_in_real_data(real_data):
    courses = real_data["courses"]

    assert "CHEM_3085" not in courses
    assert "CHEM_UN3085" in courses
    assert "CHEM_3085" in courses["CHEM_UN3085"]["aliases"]
