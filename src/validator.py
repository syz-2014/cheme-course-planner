import re

PLACEHOLDERS = {
    "PHYSICS_SEQUENCE_COURSE_1",
    "PHYSICS_SEQUENCE_COURSE_2",
    "PHYSICS_SEQUENCE_LAB_OR_THIRD_COURSE",
    "CHEMISTRY_SEQUENCE_COURSE_1",
    "CHEMISTRY_SEQUENCE_COURSE_2",
    "CHEMISTRY_SEQUENCE_COURSE_3_IF_APPLICABLE",
    "ENGL_CC1010_OR_ENGI_E1102",
    "ENGI_E1102_OR_ENGL_CC1010",
    "CORE_SEQUENCE_COURSE_1",
    "CORE_SEQUENCE_COURSE_2",
    "MATH_UN2030_OR_APMA_E2101",
    "HUMA_UN1121_OR_HUMA_UN1123",
    "NATURAL_SCIENCE_LAB_OPTION",
    "MATH_ELECTIVE",
    "NONTECH_ELECTIVE",
    "TECHNICAL_ELECTIVE"
}


TECH_REQUIREMENTS = {
    "thermo": {"tag": "thermo_elective", "required": 1},
    "transport": {"tag": "transport_elective", "required": 1},
    "engineering": {"tag": "engineering_tech_elective", "required": 3},
    "advanced_stem": {"tag": "advanced_stem_tech_elective", "required": 2}
}

# Per SEAS bulletin "Academic Procedures and Standards": full-time
# undergraduate registration is at least 12 credits/term, and students may
# not register above 21 credits/term without Committee on Academic
# Standing approval.
SEMESTER_CREDIT_MIN = 12
SEMESTER_CREDIT_MAX = 21


def is_placeholder(course_id):
    return course_id in PLACEHOLDERS


def build_alias_index(catalog):
    """Maps an alias course id (legacy numbering, alternate spreadsheet
    formatting, etc. -- see each course's `aliases` field) to its
    canonical catalog course id."""
    index = {}
    for course_id, course in catalog.items():
        for alias in course.get("aliases", []):
            index[alias] = course_id
    return index


def resolve_course_id(course_id, catalog, alias_index):
    """Returns the canonical catalog id for a possibly-aliased id, or the
    id unchanged if it's already canonical or unrecognized."""
    if course_id in catalog:
        return course_id
    return alias_index.get(course_id, course_id)


def normalize_plan_aliases(plan, catalog):
    """Rewrites every course id in the plan to its canonical catalog id,
    per `validation_rules.use_aliases_when_matching_courses` in
    requirements.json, so a course entered under an alternate/legacy id
    still satisfies the requirement it canonically counts toward."""
    alias_index = build_alias_index(catalog)
    if not alias_index:
        return plan

    return {
        semester: [resolve_course_id(c, catalog, alias_index) for c in course_ids]
        for semester, course_ids in plan.items()
    }


def flatten_plan(plan, include_placeholders=False):
    selected = []

    for semester, courses in plan.items():
        for course in courses:
            if not include_placeholders and is_placeholder(course):
                continue
            selected.append(course)

    return selected


def count_credits(course_ids, catalog, credit_overrides=None):
    credit_overrides = credit_overrides or {}
    total = 0
    warnings = []

    for course_id in course_ids:
        if is_placeholder(course_id):
            continue

        if course_id in credit_overrides:
            total += credit_overrides[course_id]
            continue

        course = catalog.get(course_id)
        if not course:
            warnings.append(f"Unknown course: {course_id}")
            continue

        credits = course.get("credits")
        if credits is None:
            warnings.append(f"Missing credits for {course_id}")
            continue

        total += credits

    return total, warnings


def check_semester_credit_loads(
    plan, catalog, credit_overrides=None,
    min_credits=SEMESTER_CREDIT_MIN, max_credits=SEMESTER_CREDIT_MAX
):
    """Per-semester credit totals against the SEAS full-time minimum and
    the no-approval-needed maximum. A semester with no real courses yet
    (still empty or all placeholders) isn't flagged -- there's nothing to
    judge yet."""
    loads = {}

    for semester, course_ids in plan.items():
        real_courses = [c for c in course_ids if not is_placeholder(c)]
        total, _ = count_credits(real_courses, catalog, credit_overrides)

        loads[semester] = {
            "credits": total,
            "has_courses": len(real_courses) > 0,
            "under_min": len(real_courses) > 0 and total < min_credits,
            "over_max": total > max_credits,
            "min_credits": min_credits,
            "max_credits": max_credits
        }

    return loads


def infer_semester_term(semester_key):
    """"semester_1" -> "Fall", "semester_2" -> "Spring", etc. Assumes a
    standard full-time plan starting in the fall (odd semesters = Fall,
    even = Spring) -- not accurate for spring admits or transfers."""
    match = re.search(r"(\d+)$", semester_key)
    if not match:
        return None
    return "Fall" if int(match.group(1)) % 2 == 1 else "Spring"


def check_offering_terms(plan, catalog):
    """Soft check: flag a course scheduled in a semester whose inferred
    Fall/Spring label wasn't among the terms it was actually found
    scheduled in this academic year, per `terms_offered` (see
    scripts/fetch_offering_terms.py).

    Only fires when the expected season is also in `terms_checked` for
    that course's subject -- i.e. we actually fetched that term's page and
    it didn't turn up. Many subjects (most of SEAS, including ChemE's own
    courses) only have a Fall2026 page published as of this scrape --
    Spring 2027 registration isn't live yet for them -- so a course
    missing from `terms_offered` alone would produce false "not offered"
    warnings; `terms_checked` is what prevents that."""
    mismatches = []

    for semester, course_ids in plan.items():
        expected_term = infer_semester_term(semester)
        if expected_term is None:
            continue

        for course_id in course_ids:
            if is_placeholder(course_id):
                continue

            course = catalog.get(course_id)
            if not course:
                continue

            terms_checked = course.get("terms_checked") or []
            checked_seasons = {t.rstrip("0123456789") for t in terms_checked}
            if expected_term not in checked_seasons:
                continue

            terms_offered = course.get("terms_offered") or []
            offered_seasons = {t.rstrip("0123456789") for t in terms_offered}
            if expected_term not in offered_seasons:
                mismatches.append({
                    "course_id": course_id,
                    "semester": semester,
                    "expected_term": expected_term,
                    "terms_offered": terms_offered
                })

    return mismatches


def is_repeatable(course):
    return bool((course or {}).get("repeat_rules", {}).get("repeatable"))


def find_duplicate_courses(plan, catalog):
    seen = set()
    duplicates = set()

    for semester, courses in plan.items():
        for course_id in courses:
            if is_placeholder(course_id):
                continue
            if is_repeatable(catalog.get(course_id)):
                continue
            if course_id in seen:
                duplicates.add(course_id)
            seen.add(course_id)

    return sorted(duplicates)


def dedupe_preserve_order(course_ids, catalog):
    """Collapse accidental duplicates, but keep every instance of a
    repeatable course (e.g. multi-semester undergraduate research) since
    each instance is a real, separate enrollment."""
    seen = set()
    deduped = []

    for course_id in course_ids:
        if is_repeatable(catalog.get(course_id)):
            deduped.append(course_id)
            continue
        if course_id in seen:
            continue
        seen.add(course_id)
        deduped.append(course_id)

    return deduped


def apply_technical_elective_repeat_caps(matches, catalog):
    """Cap how many instances of a repeatable course count toward the
    technical elective requirement, and flag the department's thesis
    trigger. Instances beyond the cap still count toward total degree
    credit via count_credits() -- they just stop adding elective credit."""
    capped = []
    warnings = []
    instance_counts = {}

    for course_id in matches:
        course = catalog.get(course_id, {})
        rules = course.get("repeat_rules", {})

        if not rules.get("repeatable"):
            capped.append(course_id)
            continue

        instance_counts[course_id] = instance_counts.get(course_id, 0) + 1
        instance = instance_counts[course_id]

        thesis_above = rules.get("thesis_required_above_instances")
        if thesis_above is not None and instance == thesis_above + 1:
            warnings.append(
                f"{course_id}: taking this for more than {thesis_above} "
                "semester(s) requires an undergraduate thesis per "
                "department policy."
            )

        max_instances = rules.get("max_instances_toward_technical_elective")
        if max_instances is not None and instance > max_instances:
            warnings.append(
                f"{course_id}: only the first {max_instances} semester(s) "
                "count toward the technical elective requirement; this "
                "semester's enrollment still counts toward total degree "
                "credit but not toward technical electives."
            )
            continue

        capped.append(course_id)

    return capped, warnings


def check_all_of(selected_courses, required_courses):
    selected = set(selected_courses)
    return [c for c in required_courses if c not in selected]


def check_tag_count(selected_courses, catalog, tag):
    matches = []

    for course_id in selected_courses:
        course = catalog.get(course_id)
        if course and tag in course.get("category_tags", []):
            matches.append(course_id)

    return matches


def count_tag(selected_courses, catalog, tag):
    return [
        course_id
        for course_id in selected_courses
        if course_id in catalog and tag in catalog[course_id].get("category_tags", [])
    ]


def is_valid_nontech(course_id, catalog, nontech_rules):
    course = catalog.get(course_id)
    if not course:
        return False

    if "nontechnical_core_required" in course.get("category_tags", []):
        return True

    if "global_core" in course.get("category_tags", []):
        return True

    subject = course["subject"]
    rules = nontech_rules.get("subject_rules", {})
    rule = rules.get(subject)

    if not rule:
        return False

    policy = rule["policy"]

    if policy == "none":
        return False

    if policy == "all":
        return True

    if policy == "only":
        return course_id in rule.get("allowed_courses", [])

    if policy == "all_except":
        return course_id not in rule.get("excluded_courses", [])

    if policy == "custom":
        # "custom" subjects (e.g. DNCE, MUSI, VISC, PSYC, ANTH) have rules
        # written as free-text notes (e.g. "performance courses do not
        # count") that can't be checked automatically. Only trust explicit
        # allowed/excluded course lists; anything else needs manual review
        # and is not auto-counted, so we don't silently overcredit.
        if course_id in rule.get("excluded_courses", []):
            return False
        if course_id in rule.get("allowed_courses", []):
            return True
        return False

    return False


def find_custom_policy_review_courses(selected_courses, catalog, nontech_rules):
    """Courses in 'custom' policy subjects that aren't explicitly allowed or
    excluded, and so were excluded from nontech credit pending manual review."""
    rules = nontech_rules.get("subject_rules", {})
    review_courses = []

    for course_id in selected_courses:
        course = catalog.get(course_id)
        if not course:
            continue

        rule = rules.get(course["subject"])
        if not rule or rule["policy"] != "custom":
            continue

        if course_id in rule.get("excluded_courses", []):
            continue
        if course_id in rule.get("allowed_courses", []):
            continue

        review_courses.append(course_id)

    return review_courses


def check_choose_one_sequence(selected_courses, sequences):
    selected = set(selected_courses)

    for sequence in sequences:
        if all(c in selected for c in sequence):
            return {
                "completed": True,
                "sequence_completed": sequence,
                "sequences": sequences
            }

    return {
        "completed": False,
        "sequence_completed": None,
        "sequences": sequences
    }


def check_math_foundation(selected_courses, requirement):
    selected = set(selected_courses)
    required_courses = requirement.get("required_courses", [])
    choose_one_of = requirement.get("choose_one_of", [])

    missing_required = [c for c in required_courses if c not in selected]
    choose_one_satisfied = any(c in selected for c in choose_one_of)

    return {
        "completed": not missing_required and choose_one_satisfied,
        "missing_required": missing_required,
        "choose_one_of": choose_one_of,
        "choose_one_satisfied": choose_one_satisfied
    }


def check_tag_credit_minimum(selected_courses, catalog, tag, credits_min, credit_overrides=None):
    credit_overrides = credit_overrides or {}
    matches = check_tag_count(selected_courses, catalog, tag)

    total = 0
    for course_id in matches:
        if course_id in credit_overrides:
            total += credit_overrides[course_id]
        elif catalog.get(course_id, {}).get("credits") is not None:
            total += catalog[course_id]["credits"]

    return {
        "completed": total >= credits_min,
        "credits_found": total,
        "credits_min": credits_min,
        "courses_found": matches
    }


def check_concentration_progress(selected_courses, concentration):
    """Elective specializations are optional -- completing one just means
    4 of your technical electives happen to be drawn from its approved
    list (12 points), not an extra requirement layered on top. Grades
    aren't tracked, so the bulletin's "no P/F courses" rule for
    specializations isn't enforced here."""
    selected = set(selected_courses)
    courses_found = [c for c in concentration["courses"] if c in selected]

    return {
        "id": concentration["id"],
        "name": concentration["name"],
        "completed": len(courses_found) >= concentration["courses_required"],
        "courses_required": concentration["courses_required"],
        "courses_found": courses_found,
        "courses_completed": len(courses_found)
    }


def check_all_concentrations(selected_courses, concentrations):
    return {
        conc_id: check_concentration_progress(selected_courses, concentration)
        for conc_id, concentration in concentrations.items()
    }


def parse_course_level(number):
    """'E3010' -> 3010, 'UN2010' -> 2010, 'GU4001' -> 4001. None if unparseable."""
    match = re.search(r"(\d{3,4})", number or "")
    return int(match.group(1)) if match else None


def check_subject_level_count_group(selected_courses, catalog, group):
    subjects = set(group.get("subjects", []))
    min_level = group.get("min_level")
    max_level = group.get("max_level")
    exclude = set(group.get("exclude", []))

    matches = []
    for course_id in selected_courses:
        course = catalog.get(course_id)
        if not course or course.get("subject") not in subjects or course_id in exclude:
            continue

        level = parse_course_level(course.get("number"))
        if min_level is not None and (level is None or level < min_level):
            continue
        if max_level is not None and (level is None or level > max_level):
            continue

        matches.append(course_id)

    credits_required = group.get("credits_required")
    if credits_required is not None:
        total_credits = sum(
            catalog[c]["credits"] for c in matches
            if catalog.get(c, {}).get("credits") is not None
        )
        satisfied = total_credits >= credits_required
    else:
        satisfied = len(matches) >= group.get("count", 1)

    return matches, satisfied


def check_minor_group(selected_courses, catalog, group):
    gtype = group["type"]

    if gtype == "free_form":
        return {**group, "courses_found": [], "satisfied": None, "verifiable": False}

    if gtype == "subject_level_count":
        matches, satisfied = check_subject_level_count_group(selected_courses, catalog, group)
        return {**group, "courses_found": matches, "satisfied": satisfied, "verifiable": True}

    options = group.get("options", [])
    selected = set(selected_courses)
    found = [c for c in options if c in selected]

    if gtype == "all_of":
        satisfied = len(found) == len(options)
    elif gtype == "choose_one_of":
        satisfied = len(found) >= 1
    elif gtype == "choose_n_of":
        satisfied = len(found) >= group.get("count", 1)
    else:
        satisfied = False

    return {**group, "courses_found": found, "satisfied": satisfied, "verifiable": True}


def check_minor_progress(selected_courses, catalog, minor):
    """Minors are optional and entirely outside this app's actual degree
    validation -- nothing here gates graduation. `free_form` groups (a
    prose rule this app has no way to check) are always reported as
    unverified rather than guessed at; `completed_verifiable` only
    reflects the groups that could actually be checked."""
    if minor.get("unstructured"):
        return {
            "id": minor["id"], "name": minor["name"], "unstructured": True,
            "description": minor.get("description"), "groups": [],
            "completed_verifiable": None, "has_unverifiable_groups": True
        }

    group_results = [
        check_minor_group(selected_courses, catalog, group)
        for group in minor.get("groups", [])
    ]

    verifiable_groups = [g for g in group_results if g["verifiable"]]
    has_unverifiable = len(verifiable_groups) < len(group_results)
    completed_verifiable = all(g["satisfied"] for g in verifiable_groups) if verifiable_groups else False

    return {
        "id": minor["id"], "name": minor["name"], "unstructured": False,
        "groups": group_results,
        "completed_verifiable": completed_verifiable,
        "has_unverifiable_groups": has_unverifiable
    }


def check_all_minors(selected_courses, catalog, minors):
    return {
        minor_id: check_minor_progress(selected_courses, catalog, minor)
        for minor_id, minor in minors.items()
    }


def compute_elective_nontech_credits(
    nontech_courses, nontech_credits, required_courses,
    core_sequence_status, art_music_status, catalog, credit_overrides=None
):
    """The nontechnical requirement's 27 total credits include some
    required components (ENGL_CC1010/ECON_UN1105, the core sequence pair,
    art/music humanities); the elective_nontechnical sub-band is only the
    remainder the student chose freely."""
    credit_overrides = credit_overrides or {}
    selected_nontech = set(nontech_courses)

    required_component_ids = {c for c in required_courses if c in selected_nontech}

    path = core_sequence_status.get("path_completed")
    if path == "literature_humanities":
        required_component_ids.update(["HUMA_CC1001", "HUMA_CC1002"])
    elif path == "contemporary_civilization":
        required_component_ids.update(["COCI_CC1101", "COCI_CC1102"])
    elif path == "global_core":
        required_component_ids.update(
            core_sequence_status.get("global_core_courses_found", [])[:2]
        )

    required_component_ids.update(art_music_status.get("courses_found", []))

    required_component_credits = 0
    for course_id in required_component_ids:
        if course_id in credit_overrides:
            required_component_credits += credit_overrides[course_id]
        elif catalog.get(course_id, {}).get("credits") is not None:
            required_component_credits += catalog[course_id]["credits"]

    return nontech_credits - required_component_credits


def check_core_sequence_path(selected_courses, catalog):
    selected = set(selected_courses)

    lit_hum_courses = ["HUMA_CC1001", "HUMA_CC1002"]
    cc_courses = ["COCI_CC1101", "COCI_CC1102"]

    lit_hum_completed = all(c in selected for c in lit_hum_courses)
    cc_completed = all(c in selected for c in cc_courses)

    global_core_courses = [
        c for c in selected_courses
        if c in catalog and "global_core" in catalog[c].get("category_tags", [])
    ]

    global_core_completed = len(global_core_courses) >= 2

    return {
        "completed": lit_hum_completed or cc_completed or global_core_completed,
        "path_completed": (
            "literature_humanities" if lit_hum_completed
            else "contemporary_civilization" if cc_completed
            else "global_core" if global_core_completed
            else None
        ),
        "lit_hum_completed": lit_hum_completed,
        "cc_completed": cc_completed,
        "global_core_completed": global_core_completed,
        "global_core_courses_found": global_core_courses,
        "global_core_courses_required": 2
    }


def check_art_or_music(selected_courses):
    selected = set(selected_courses)
    options = ["HUMA_UN1121", "HUMA_UN1123"]
    completed_courses = [c for c in options if c in selected]

    return {
        "completed": len(completed_courses) >= 1,
        "courses_found": completed_courses,
        "options": options
    }


def check_prerequisites(plan, catalog, prerequisite_overrides=None):
    errors = []
    completed_before = set(prerequisite_overrides or [])

    for semester, courses in plan.items():
        current_semester = set(courses)

        for course_id in courses:
            if is_placeholder(course_id):
                continue

            course = catalog.get(course_id)
            if not course:
                continue

            prereqs = course.get("prerequisites", [])

            for prereq in prereqs:
                if prereq not in completed_before:
                    errors.append(
                        f"{course_id} requires {prereq}, but {prereq} is not completed in an earlier semester or marked as waived."
                    )

        completed_before.update(current_semester)

    return errors


def validate_plan(
    plan,
    catalog,
    requirements,
    nontech_rules,
    prerequisite_overrides=None,
    credit_overrides=None,
    concentrations=None,
    minors=None
):
    credit_overrides = credit_overrides or {}
    concentrations = concentrations or {}
    minors = minors or {}
    plan = normalize_plan_aliases(plan, catalog)

    alias_index = build_alias_index(catalog)
    prerequisite_overrides = {
        resolve_course_id(c, catalog, alias_index)
        for c in (prerequisite_overrides or [])
    }

    selected_courses = dedupe_preserve_order(flatten_plan(plan), catalog)

    # AP/placement/transfer/waiver credit should satisfy the specific
    # requirement it stands in for (a required course, a sequence, a tag
    # count) exactly like actually taking the course would. It should NOT
    # inflate point-total metrics (total_credits, nontech_credits) since
    # we don't track how many real Columbia points, if any, a given
    # waiver confers -- so those stay strictly selected_courses-based.
    requirement_courses = selected_courses + [
        c for c in prerequisite_overrides if c not in selected_courses
    ]

    results = {
        "errors": [],
        "warnings": [],
        "progress": {}
    }
    results["progress"]["prerequisite_overrides_applied"] = sorted(prerequisite_overrides)

    duplicate_courses = find_duplicate_courses(plan, catalog)
    if duplicate_courses:
        results["errors"].append(
            "Duplicate course(s) appear in more than one semester (counted "
            f"only once toward credits/requirements): {', '.join(duplicate_courses)}"
        )

    prereq_errors = check_prerequisites(
        plan,
        catalog,
        prerequisite_overrides
    )
    results["errors"].extend(prereq_errors)

    art_music_status = check_art_or_music(requirement_courses)
    results["progress"]["art_or_music_humanities"] = art_music_status

    core_sequence_status = check_core_sequence_path(requirement_courses, catalog)
    results["progress"]["core_sequence_requirement"] = core_sequence_status

    tech_breakdown = {}
    for key, config in TECH_REQUIREMENTS.items():
        matches = count_tag(requirement_courses, catalog, config["tag"])
        tech_breakdown[key] = len(matches)

    results["progress"]["tech_breakdown"] = tech_breakdown

    total_credits, credit_warnings = count_credits(
        selected_courses,
        catalog,
        credit_overrides
    )
    results["warnings"].extend(credit_warnings)
    results["progress"]["total_credits"] = total_credits

    semester_loads = check_semester_credit_loads(plan, catalog, credit_overrides)
    results["progress"]["semester_credit_loads"] = semester_loads

    term_mismatches = check_offering_terms(plan, catalog)
    results["progress"]["term_mismatches"] = term_mismatches
    for mismatch in term_mismatches:
        label = mismatch["semester"].replace("_", " ").title()
        if mismatch["terms_offered"]:
            schedule_note = f"it's only scheduled in {', '.join(mismatch['terms_offered'])}"
        else:
            schedule_note = "it isn't scheduled this academic year"
        results["warnings"].append(
            f"{mismatch['course_id']} is planned for {label} (assumed "
            f"{mismatch['expected_term']}), but this year {schedule_note}."
        )

    for semester, load in semester_loads.items():
        label = semester.replace("_", " ").title()
        if load["under_min"]:
            results["warnings"].append(
                f"{label}: {load['credits']:g} credits is below the "
                f"{load['min_credits']}-credit full-time minimum."
            )
        elif load["over_max"]:
            results["warnings"].append(
                f"{label}: {load['credits']:g} credits exceeds the "
                f"{load['max_credits']}-credit maximum allowed without "
                "Committee on Academic Standing approval."
            )

    major_req = requirements["requirements"]["major_required_courses"]["courses"]
    missing_major = check_all_of(requirement_courses, major_req)

    results["progress"]["major_required_completed"] = len(major_req) - len(missing_major)
    results["progress"]["major_required_total"] = len(major_req)
    results["progress"]["missing_major_required"] = missing_major

    math_foundation_req = requirements["requirements"]["math_foundation"]
    results["progress"]["math_foundation_requirement"] = check_math_foundation(
        requirement_courses, math_foundation_req
    )

    physics_req = requirements["requirements"]["physics_requirement"]
    results["progress"]["physics_requirement"] = check_choose_one_sequence(
        requirement_courses, physics_req["sequences"]
    )

    chemistry_req = requirements["requirements"]["chemistry_requirement"]
    results["progress"]["chemistry_requirement"] = check_choose_one_sequence(
        requirement_courses, chemistry_req["sequences"]
    )

    nat_sci_lab_req = requirements["requirements"]["natural_science_lab"]
    results["progress"]["natural_science_lab_requirement"] = check_tag_credit_minimum(
        requirement_courses, catalog,
        nat_sci_lab_req["required_tag"], nat_sci_lab_req["credits_min"],
        credit_overrides
    )

    pe_courses = requirements["requirements"]["physical_education"]["courses"]
    missing_pe = check_all_of(requirement_courses, pe_courses)
    results["progress"]["physical_education_completed"] = len(pe_courses) - len(missing_pe)
    results["progress"]["physical_education_total"] = len(pe_courses)
    results["progress"]["missing_physical_education"] = missing_pe

    math_electives = check_tag_count(requirement_courses, catalog, "math_elective")
    results["progress"]["math_elective_completed"] = len(math_electives) >= 1
    results["progress"]["math_electives_found"] = math_electives

    tech_electives_raw = check_tag_count(requirement_courses, catalog, "technical_elective")
    tech_electives, repeat_warnings = apply_technical_elective_repeat_caps(
        tech_electives_raw, catalog
    )
    results["warnings"].extend(repeat_warnings)
    results["progress"]["technical_electives_completed"] = len(tech_electives)
    results["progress"]["technical_electives_required"] = 7
    results["progress"]["technical_electives_found"] = tech_electives

    results["progress"]["concentrations"] = check_all_concentrations(
        requirement_courses, concentrations
    )

    results["progress"]["minors"] = check_all_minors(
        requirement_courses, catalog, minors
    )

    nontech_courses = [
        c for c in selected_courses
        if is_valid_nontech(c, catalog, nontech_rules)
    ]

    review_courses = find_custom_policy_review_courses(
        selected_courses, catalog, nontech_rules
    )
    if review_courses:
        results["warnings"].append(
            "Course(s) need manual review against department policy notes "
            "before counting as nontechnical credit (not currently counted): "
            f"{', '.join(review_courses)}"
        )

    nontech_credits = 0
    for c in nontech_courses:
        if c in credit_overrides:
            nontech_credits += credit_overrides[c]
        elif c in catalog and catalog[c].get("credits") is not None:
            nontech_credits += catalog[c]["credits"]

    nontech_req = requirements["requirements"]["nontechnical_requirement"]
    required_nontech = nontech_req["credits_min"]

    results["progress"]["nontech_courses"] = nontech_courses
    results["progress"]["nontech_credits"] = nontech_credits
    results["progress"]["nontech_completed"] = nontech_credits >= required_nontech

    nontech_required_courses = nontech_req.get("required_courses", [])
    missing_nontech_required = check_all_of(requirement_courses, nontech_required_courses)
    results["progress"]["missing_nontech_required_courses"] = missing_nontech_required

    elective_nontech_req = nontech_req.get("elective_nontechnical", {})
    elective_nontech_credits = compute_elective_nontech_credits(
        nontech_courses, nontech_credits, nontech_required_courses,
        core_sequence_status, art_music_status, catalog, credit_overrides
    )
    elective_min = elective_nontech_req.get("credits_min")
    elective_max = elective_nontech_req.get("credits_max")

    results["progress"]["elective_nontechnical_credits"] = elective_nontech_credits
    results["progress"]["elective_nontechnical_min"] = elective_min
    results["progress"]["elective_nontechnical_max"] = elective_max

    if elective_min is not None and elective_nontech_credits < elective_min:
        results["warnings"].append(
            f"Elective nontechnical credits ({elective_nontech_credits:g}) are "
            f"below the department's expected {elective_min}-{elective_max} "
            "point range for freely-chosen nontechnical electives."
        )
    elif elective_max is not None and elective_nontech_credits > elective_max:
        results["warnings"].append(
            f"Elective nontechnical credits ({elective_nontech_credits:g}) "
            f"exceed the department's expected {elective_min}-{elective_max} "
            "point range (extra credits still count toward the 27-point "
            "total and graduation)."
        )

    return results

def recommend_courses(catalog, progress, interests=None, max_results=8):
    interests = [i.lower() for i in (interests or [])]

    tech = progress.get("tech_breakdown", {})

    needed_tags = []

    if tech.get("thermo", 0) < 1:
        needed_tags.append("thermo_elective")

    if tech.get("transport", 0) < 1:
        needed_tags.append("transport_elective")

    if tech.get("engineering", 0) < 3:
        needed_tags.append("engineering_tech_elective")

    if tech.get("advanced_stem", 0) < 2:
        needed_tags.append("advanced_stem_tech_elective")

    if not progress.get("math_elective_completed"):
        needed_tags.append("math_elective")

    recommendations = []

    for course_id, course in catalog.items():
        tags = course.get("category_tags", [])
        title = (course.get("title") or "").lower()

        matched_tags = [t for t in needed_tags if t in tags]
        if not matched_tags:
            continue

        # Interest matching
        interest_score = 0
        matched_interests = []

        for interest in interests:
            if interest in title:
                interest_score += 2
                matched_interests.append(interest)
            elif interest in " ".join(tags):
                interest_score += 1
                matched_interests.append(interest)

        recommendations.append({
            "course_id": course_id,
            "title": course.get("title"),
            "credits": course.get("credits"),
            "matched_requirements": matched_tags,
            "matched_interests": matched_interests,
            "score": interest_score + len(matched_tags)
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return recommendations[:max_results]