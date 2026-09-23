from validator import (
    check_all_of, check_choose_one_sequence, check_tag_credit_minimum,
    is_placeholder, find_duplicate_courses, dedupe_preserve_order,
    apply_technical_elective_repeat_caps, resolve_course_id, build_alias_index,
    normalize_plan_aliases, is_valid_nontech, check_semester_credit_loads,
    infer_semester_term, check_offering_terms, parse_course_level,
    check_subject_level_count_group, check_minor_group, check_minor_progress,
    check_concentration_progress, validate_plan,
    SEMESTER_CREDIT_MIN, SEMESTER_CREDIT_MAX
)


def make_course(course_id, **overrides):
    subject, _, number = course_id.partition("_")
    course = {
        "id": course_id, "subject": subject or course_id, "number": number,
        "title": "Untitled", "credits": 3, "category_tags": [],
        "prerequisites": [], "corequisites": [], "aliases": [], "notes": []
    }
    course.update(overrides)
    return course


# ---------------------------------------------------------------------------
# Small pure-logic checks
# ---------------------------------------------------------------------------

def test_check_all_of_reports_missing_courses():
    missing = check_all_of(["A", "B"], ["A", "B", "C"])
    assert missing == ["C"]


def test_check_all_of_empty_when_all_present():
    assert check_all_of(["A", "B", "C"], ["A", "B"]) == []


def test_check_choose_one_sequence_completed():
    sequences = [["A", "B"], ["C"]]
    result = check_choose_one_sequence(["C", "D"], sequences)
    assert result["completed"] is True
    assert result["sequence_completed"] == ["C"]


def test_check_choose_one_sequence_not_completed():
    sequences = [["A", "B"], ["C"]]
    result = check_choose_one_sequence(["A"], sequences)
    assert result["completed"] is False
    assert result["sequence_completed"] is None


def test_check_tag_credit_minimum_sums_matching_credits():
    catalog = {
        "LAB1": make_course("LAB1", credits=1.5, category_tags=["natural_science_lab_option"]),
        "LAB2": make_course("LAB2", credits=1.5, category_tags=["natural_science_lab_option"]),
        "OTHER": make_course("OTHER", credits=3, category_tags=[]),
    }
    result = check_tag_credit_minimum(["LAB1", "LAB2", "OTHER"], catalog, "natural_science_lab_option", 3)
    assert result["credits_found"] == 3
    assert result["completed"] is True


def test_check_tag_credit_minimum_not_completed_below_threshold():
    catalog = {"LAB1": make_course("LAB1", credits=1.5, category_tags=["natural_science_lab_option"])}
    result = check_tag_credit_minimum(["LAB1"], catalog, "natural_science_lab_option", 3)
    assert result["completed"] is False
    assert result["credits_found"] == 1.5


def test_is_placeholder():
    assert is_placeholder("TECHNICAL_ELECTIVE") is True
    assert is_placeholder("CHEN_E1000") is False


# ---------------------------------------------------------------------------
# Duplicate / repeatable course handling
# ---------------------------------------------------------------------------

def test_find_duplicate_courses_flags_repeat():
    catalog = {"MATH_UN1101": make_course("MATH_UN1101")}
    plan = {"semester_1": ["MATH_UN1101"], "semester_2": ["MATH_UN1101"]}
    assert find_duplicate_courses(plan, catalog) == ["MATH_UN1101"]


def test_find_duplicate_courses_ignores_repeatable_course():
    catalog = {
        "CHEN_E3900": make_course("CHEN_E3900", repeat_rules={"repeatable": True})
    }
    plan = {"semester_1": ["CHEN_E3900"], "semester_2": ["CHEN_E3900"]}
    assert find_duplicate_courses(plan, catalog) == []


def test_dedupe_preserve_order_keeps_repeatable_instances():
    catalog = {"CHEN_E3900": make_course("CHEN_E3900", repeat_rules={"repeatable": True})}
    result = dedupe_preserve_order(["CHEN_E3900", "CHEN_E3900", "OTHER", "OTHER"], catalog)
    assert result == ["CHEN_E3900", "CHEN_E3900", "OTHER"]


def test_apply_technical_elective_repeat_caps_limits_and_warns():
    catalog = {
        "CHEN_E3900": make_course("CHEN_E3900", repeat_rules={
            "repeatable": True,
            "max_instances_toward_technical_elective": 2,
            "thesis_required_above_instances": 1
        })
    }
    matches = ["CHEN_E3900", "CHEN_E3900", "CHEN_E3900"]

    capped, warnings = apply_technical_elective_repeat_caps(matches, catalog)

    assert capped == ["CHEN_E3900", "CHEN_E3900"]
    assert any("thesis" in w.lower() for w in warnings)
    assert any("only the first 2" in w for w in warnings)


def test_apply_technical_elective_repeat_caps_passes_through_normal_courses():
    catalog = {"CHEN_E4130": make_course("CHEN_E4130")}
    capped, warnings = apply_technical_elective_repeat_caps(["CHEN_E4130"], catalog)
    assert capped == ["CHEN_E4130"]
    assert warnings == []


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------

def test_build_alias_index():
    catalog = {"CHEM_UN3085": make_course("CHEM_UN3085", aliases=["CHEM_3085"])}
    assert build_alias_index(catalog) == {"CHEM_3085": "CHEM_UN3085"}


def test_resolve_course_id_via_alias():
    catalog = {"CHEM_UN3085": make_course("CHEM_UN3085")}
    alias_index = {"CHEM_3085": "CHEM_UN3085"}
    assert resolve_course_id("CHEM_3085", catalog, alias_index) == "CHEM_UN3085"


def test_resolve_course_id_passthrough_for_canonical_id():
    catalog = {"CHEM_UN3085": make_course("CHEM_UN3085")}
    assert resolve_course_id("CHEM_UN3085", catalog, {}) == "CHEM_UN3085"


def test_normalize_plan_aliases_rewrites_alias_ids():
    catalog = {"CHEM_UN3085": make_course("CHEM_UN3085", aliases=["CHEM_3085"])}
    plan = {"semester_1": ["CHEM_3085"]}
    normalized = normalize_plan_aliases(plan, catalog)
    assert normalized["semester_1"] == ["CHEM_UN3085"]


# ---------------------------------------------------------------------------
# Nontechnical subject-policy handling
# ---------------------------------------------------------------------------

def test_is_valid_nontech_custom_policy_requires_explicit_allow_or_exclude():
    # Regression test for a real bug: "custom" used to return True for any
    # course, silently crediting subjects with real exclusions (DNCE
    # performance courses, PSYC's excluded list, etc).
    catalog = {
        "PSYC_UN1001": make_course("PSYC_UN1001", subject="PSYC"),
        "PSYC_UN2235": make_course("PSYC_UN2235", subject="PSYC"),
        "PSYC_UN9999": make_course("PSYC_UN9999", subject="PSYC"),
    }
    nontech_rules = {"subject_rules": {"PSYC": {
        "policy": "custom",
        "allowed_courses": ["PSYC_UN1001"],
        "excluded_courses": ["PSYC_UN2235"]
    }}}

    assert is_valid_nontech("PSYC_UN1001", catalog, nontech_rules) is True
    assert is_valid_nontech("PSYC_UN2235", catalog, nontech_rules) is False
    assert is_valid_nontech("PSYC_UN9999", catalog, nontech_rules) is False


def test_is_valid_nontech_all_except_policy():
    catalog = {"ECON_UN1105": make_course("ECON_UN1105", subject="ECON")}
    nontech_rules = {"subject_rules": {"ECON": {"policy": "all_except", "excluded_courses": ["ECON_UN3025"]}}}
    assert is_valid_nontech("ECON_UN1105", catalog, nontech_rules) is True


def test_is_valid_nontech_none_policy():
    catalog = {"MATH_UN1101": make_course("MATH_UN1101", subject="MATH")}
    nontech_rules = {"subject_rules": {"MATH": {"policy": "none"}}}
    assert is_valid_nontech("MATH_UN1101", catalog, nontech_rules) is False


# ---------------------------------------------------------------------------
# Semester credit load bounds
# ---------------------------------------------------------------------------

def test_check_semester_credit_loads_flags_under_minimum():
    catalog = {"A": make_course("A", credits=3)}
    loads = check_semester_credit_loads({"semester_1": ["A"]}, catalog)
    assert loads["semester_1"]["credits"] == 3
    assert loads["semester_1"]["under_min"] is True
    assert loads["semester_1"]["over_max"] is False


def test_check_semester_credit_loads_flags_over_maximum():
    catalog = {f"C{i}": make_course(f"C{i}", credits=4) for i in range(6)}
    loads = check_semester_credit_loads({"semester_1": list(catalog.keys())}, catalog)
    assert loads["semester_1"]["credits"] == 24
    assert loads["semester_1"]["over_max"] is True


def test_check_semester_credit_loads_skips_empty_semester():
    loads = check_semester_credit_loads({"semester_1": []}, {})
    assert loads["semester_1"]["under_min"] is False


def test_semester_credit_bounds_match_seas_policy():
    # 12-credit min / 21-credit max per the SEAS bulletin's Academic
    # Procedures and Standards section.
    assert SEMESTER_CREDIT_MIN == 12
    assert SEMESTER_CREDIT_MAX == 21


# ---------------------------------------------------------------------------
# Offering-term mismatch checks
# ---------------------------------------------------------------------------

def test_infer_semester_term_alternates_fall_spring():
    assert infer_semester_term("semester_1") == "Fall"
    assert infer_semester_term("semester_2") == "Spring"
    assert infer_semester_term("semester_7") == "Fall"
    assert infer_semester_term("semester_8") == "Spring"


def test_check_offering_terms_flags_real_mismatch():
    catalog = {"A": make_course("A", terms_checked=["Fall2026", "Spring2027"], terms_offered=["Fall2026"])}
    mismatches = check_offering_terms({"semester_2": ["A"]}, catalog)
    assert len(mismatches) == 1
    assert mismatches[0]["course_id"] == "A"


def test_check_offering_terms_no_false_positive_when_season_not_checked():
    # Regression test: a subject whose Spring page simply isn't published
    # yet (terms_checked only has Fall) must not be flagged as "not
    # offered in Spring" -- there's no real evidence either way.
    catalog = {"A": make_course("A", terms_checked=["Fall2026"], terms_offered=["Fall2026"])}
    mismatches = check_offering_terms({"semester_2": ["A"]}, catalog)
    assert mismatches == []


def test_check_offering_terms_no_warning_when_term_matches():
    catalog = {"A": make_course("A", terms_checked=["Fall2026", "Spring2027"], terms_offered=["Fall2026"])}
    mismatches = check_offering_terms({"semester_1": ["A"]}, catalog)
    assert mismatches == []


# ---------------------------------------------------------------------------
# Minors: subject_level_count and group types
# ---------------------------------------------------------------------------

def test_parse_course_level():
    assert parse_course_level("E3010") == 3010
    assert parse_course_level("UN2010") == 2010
    assert parse_course_level("GU4001") == 4001
    assert parse_course_level("garbage") is None


def test_check_subject_level_count_group_respects_min_and_exclude():
    catalog = {
        "MSAE_E3010": make_course("MSAE_E3010", subject="MSAE", number="E3010"),
        "MSAE_E2000": make_course("MSAE_E2000", subject="MSAE", number="E2000"),
        "MSAE_E3900": make_course("MSAE_E3900", subject="MSAE", number="E3900"),
    }
    group = {"subjects": ["MSAE"], "min_level": 3000, "count": 1, "exclude": ["MSAE_E3900"]}

    matches, satisfied = check_subject_level_count_group(
        ["MSAE_E3010", "MSAE_E2000", "MSAE_E3900"], catalog, group
    )

    assert matches == ["MSAE_E3010"]
    assert satisfied is True


def test_check_minor_group_all_of():
    group = {"type": "all_of", "options": ["A", "B"]}
    result = check_minor_group(["A"], {}, group)
    assert result["satisfied"] is False
    result = check_minor_group(["A", "B"], {}, group)
    assert result["satisfied"] is True


def test_check_minor_group_choose_n_of():
    group = {"type": "choose_n_of", "count": 2, "options": ["A", "B", "C"]}
    assert check_minor_group(["A"], {}, group)["satisfied"] is False
    assert check_minor_group(["A", "B"], {}, group)["satisfied"] is True


def test_check_minor_group_free_form_is_never_auto_satisfied():
    group = {"type": "free_form", "description": "some prose rule"}
    result = check_minor_group(["A", "B", "C"], {}, group)
    assert result["verifiable"] is False
    assert result["satisfied"] is None


def test_check_minor_progress_unstructured_minor():
    minor = {"id": "x", "name": "X Minor", "unstructured": True, "description": "..."}
    result = check_minor_progress(["A"], {}, minor)
    assert result["unstructured"] is True
    assert result["completed_verifiable"] is None


def test_check_minor_progress_completed_when_all_groups_satisfied():
    minor = {
        "id": "bme", "name": "BME Minor",
        "groups": [{"type": "all_of", "options": ["A", "B"], "label": "Required"}]
    }
    result = check_minor_progress(["A", "B"], {}, minor)
    assert result["completed_verifiable"] is True
    assert result["has_unverifiable_groups"] is False


def test_check_minor_progress_free_form_group_blocks_completion_flag_but_is_tracked():
    minor = {
        "id": "x", "name": "X Minor",
        "groups": [
            {"type": "all_of", "options": ["A"], "label": "Required"},
            {"type": "free_form", "description": "prose rule", "label": "Elective"}
        ]
    }
    result = check_minor_progress(["A"], {}, minor)
    assert result["has_unverifiable_groups"] is True
    # completed_verifiable only reflects groups that could actually be checked
    assert result["completed_verifiable"] is True


# ---------------------------------------------------------------------------
# Concentrations
# ---------------------------------------------------------------------------

def test_check_concentration_progress():
    concentration = {"id": "x", "name": "X", "courses_required": 2, "courses": ["A", "B", "C"]}
    result = check_concentration_progress(["A"], concentration)
    assert result["completed"] is False
    assert result["courses_completed"] == 1

    result = check_concentration_progress(["A", "B"], concentration)
    assert result["completed"] is True


# ---------------------------------------------------------------------------
# validate_plan integration tests against the real catalog/requirements
# ---------------------------------------------------------------------------

def test_sample_valid_plan_has_no_errors(real_data):
    plan = real_data["sample_plan"]
    results = validate_plan(
        plan, real_data["courses"], real_data["requirements"], real_data["nontech_rules"],
        concentrations=real_data["concentrations"], minors=real_data["minors"]
    )
    assert results["errors"] == []


def test_duplicate_course_across_semesters_is_an_error(real_data):
    plan = {"semester_1": ["MATH_UN1101"], "semester_2": ["MATH_UN1101"]}
    results = validate_plan(plan, real_data["courses"], real_data["requirements"], real_data["nontech_rules"])
    assert any("Duplicate" in e for e in results["errors"])


def test_repeatable_course_across_semesters_is_not_an_error(real_data):
    plan = {"semester_5": ["CHEN_E3900"], "semester_6": ["CHEN_E3900"]}
    results = validate_plan(plan, real_data["courses"], real_data["requirements"], real_data["nontech_rules"])
    assert results["errors"] == []


def test_ap_credit_satisfies_requirement_without_inflating_total_credits(real_data):
    plan = {"semester_1": ["APMA_E2000"]}
    results = validate_plan(
        plan, real_data["courses"], real_data["requirements"], real_data["nontech_rules"],
        prerequisite_overrides={"MATH_UN1101", "MATH_UN1102"}
    )
    assert "MATH_UN1101" not in results["progress"]["math_foundation_requirement"]["missing_required"]
    # APMA_E2000 alone is 4 credits -- the AP-credited MATH courses must
    # not add their credits on top of that.
    assert results["progress"]["total_credits"] == 4


def test_alias_course_id_resolves_within_full_validate_plan(real_data):
    plan = {"semester_1": ["CHEM_3085"]}
    results = validate_plan(plan, real_data["courses"], real_data["requirements"], real_data["nontech_rules"])
    assert results["progress"]["total_credits"] == 3


def test_validate_plan_produces_concentration_and_minor_progress(real_data):
    results = validate_plan(
        real_data["template"]["semesters"], real_data["courses"], real_data["requirements"],
        real_data["nontech_rules"], concentrations=real_data["concentrations"], minors=real_data["minors"]
    )
    assert len(results["progress"]["concentrations"]) == 4
    assert len(results["progress"]["minors"]) == len(real_data["minors"])
