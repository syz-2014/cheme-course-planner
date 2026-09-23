import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from backfill_prerequisites import (
    parse_prereq_clause, is_legacy_prefixed, try_legacy_remap,
    resolve_referenced_codes
)


def test_parse_prereq_clause_and_list():
    ids, status = parse_prereq_clause("CHEE E3010 AND MSAE E3111; or equivalent", had_period=True)
    assert status == "ok"
    assert ids == ["CHEE_E3010", "MSAE_E3111"]


def test_parse_prereq_clause_single_course_with_boilerplate():
    ids, status = parse_prereq_clause("(CHEN E3230) or equivalent, or instructors permission", had_period=True)
    assert status == "ok"
    assert ids == ["CHEN_E3230"]


def test_parse_prereq_clause_no_course_codes():
    ids, status = parse_prereq_clause("Instructor's permission", had_period=True)
    assert status == "no_course_codes"
    assert ids is None


def test_parse_prereq_clause_ambiguous_or_between_real_courses():
    ids, status = parse_prereq_clause("(CHEN E3120) or CHEE E3010; or instructor's permission", had_period=True)
    assert status == "ambiguous_or"
    assert ids is None


def test_parse_prereq_clause_dangling_connector_without_period_is_rejected():
    # simulates a PDF line-wrap that cut the clause off mid-list
    ids, status = parse_prereq_clause("(APMA E3101) and (APMA E4200) APMA E3101 AND", had_period=False)
    assert status == "possibly_truncated"
    assert ids is None


def test_parse_prereq_clause_trailing_prose_without_period_is_rejected():
    ids, status = parse_prereq_clause("APMA E3101 AND APMA E4007; After the approval of", had_period=False)
    assert status == "possibly_truncated"
    assert ids is None


def test_parse_prereq_clause_complete_parenthetical_without_period_is_accepted():
    # "(MATH UN1101)" with nothing else on the line -- genuinely complete,
    # just never got a period because it's a noun phrase, not a sentence
    ids, status = parse_prereq_clause("(MATH UN1101)", had_period=False)
    assert status == "ok"
    assert ids == ["MATH_UN1101"]


def test_is_legacy_prefixed():
    assert is_legacy_prefixed("MATH_V1201") is True
    assert is_legacy_prefixed("PHYS_C1401") is True
    assert is_legacy_prefixed("PHYS_W3008") is True
    assert is_legacy_prefixed("MATH_UN1101") is False
    assert is_legacy_prefixed("CHEN_E3010") is False


def test_try_legacy_remap_finds_modern_equivalent():
    courses = {"PHYS_UN1401": {}}
    assert try_legacy_remap("PHYS_C1401", courses, {}) == "PHYS_UN1401"


def test_try_legacy_remap_returns_none_when_no_modern_equivalent_exists():
    assert try_legacy_remap("MATH_V1201", {}, {}) is None


def test_resolve_referenced_codes_classifies_correctly():
    courses = {"CHEN_E3010": {}, "PHYS_UN1401": {}}
    alias_index = {}
    codes = {
        "CHEN_E3010",     # already exists
        "PHYS_C1401",     # legacy, remaps to an existing modern course
        "MATH_V1201",     # legacy, no modern equivalent -- unresolvable
        "MATH_UN9999",    # not legacy-prefixed, missing -- safe to add
    }

    resolved_map, unresolvable, new_bare = resolve_referenced_codes(codes, courses, alias_index)

    assert resolved_map["CHEN_E3010"] == "CHEN_E3010"
    assert resolved_map["PHYS_C1401"] == "PHYS_UN1401"
    assert resolved_map["MATH_UN9999"] == "MATH_UN9999"
    assert "MATH_V1201" in unresolvable
    assert new_bare == ["MATH_UN9999"]
