from plan_io import (
    plan_to_json_bytes, plan_from_json_bytes,
    plan_to_csv_bytes, plan_from_csv_bytes,
    plan_to_xlsx_bytes, plan_from_xlsx_bytes,
)

CATALOG = {
    "MATH_UN1101": {"title": "Calculus I"},
    "CHEN_E1000": {"title": "Chemical Engineering for Humanity"},
}
PLAN = {
    "semester_1": ["MATH_UN1101", "CHEN_E1000"],
    "semester_2": [],
}
CREDIT_OVERRIDES = {"CHEN_E1000": 2.5}
PREREQ_OVERRIDES = {"MATH_UN1101"}
SEMESTERS = ["semester_1", "semester_2"]


def test_json_round_trip():
    data = plan_to_json_bytes(PLAN, CREDIT_OVERRIDES, PREREQ_OVERRIDES)
    plan, credit_overrides, prereq_overrides = plan_from_json_bytes(data)

    assert plan == PLAN
    assert credit_overrides == CREDIT_OVERRIDES
    assert prereq_overrides == ["MATH_UN1101"]


def test_csv_round_trip():
    data = plan_to_csv_bytes(PLAN, CREDIT_OVERRIDES, PREREQ_OVERRIDES, CATALOG)
    plan, credit_overrides, prereq_overrides = plan_from_csv_bytes(data, SEMESTERS)

    assert plan == PLAN
    assert credit_overrides == CREDIT_OVERRIDES
    assert prereq_overrides == ["MATH_UN1101"]


def test_csv_includes_course_titles_for_readability():
    data = plan_to_csv_bytes(PLAN, CREDIT_OVERRIDES, PREREQ_OVERRIDES, CATALOG)
    text = data.decode("utf-8")
    assert "Calculus I" in text
    assert "Chemical Engineering for Humanity" in text


def test_csv_ignores_unknown_semester():
    csv_text = (
        "type,semester,course_id,course_title,credit_override\n"
        "course,semester_99,CHEN_E1000,,\n"
    )
    plan, credit_overrides, prereq_overrides = plan_from_csv_bytes(
        csv_text.encode("utf-8"), SEMESTERS
    )
    assert plan == {"semester_1": [], "semester_2": []}


def test_csv_ignores_malformed_credit_override():
    csv_text = (
        "type,semester,course_id,course_title,credit_override\n"
        "course,semester_1,CHEN_E1000,,not-a-number\n"
    )
    plan, credit_overrides, _ = plan_from_csv_bytes(csv_text.encode("utf-8"), SEMESTERS)
    assert plan["semester_1"] == ["CHEN_E1000"]
    assert credit_overrides == {}


def test_xlsx_round_trip():
    data = plan_to_xlsx_bytes(PLAN, CREDIT_OVERRIDES, PREREQ_OVERRIDES, CATALOG)
    plan, credit_overrides, prereq_overrides = plan_from_xlsx_bytes(data, SEMESTERS)

    assert plan == PLAN
    assert credit_overrides == CREDIT_OVERRIDES
    assert prereq_overrides == ["MATH_UN1101"]


def test_xlsx_empty_plan_round_trips_to_empty_semesters():
    data = plan_to_xlsx_bytes({"semester_1": [], "semester_2": []}, {}, set(), CATALOG)
    plan, credit_overrides, prereq_overrides = plan_from_xlsx_bytes(data, SEMESTERS)

    assert plan == {"semester_1": [], "semester_2": []}
    assert credit_overrides == {}
    assert prereq_overrides == []
