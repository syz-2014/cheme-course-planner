import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest

from load_data import load_all_data


@pytest.fixture(scope="session")
def real_data():
    """The actual project data, loaded once per test run. Use this only
    for tests that are genuinely about the real catalog (e.g. "the sample
    plan validates cleanly", "this specific known alias resolves").
    Anything testing validator *logic* in general should build its own
    small synthetic catalog instead, so it can't be broken by an
    unrelated future data change."""
    courses, requirements, template, nontech_rules, concentrations, minors, minor_global_rules = load_all_data()
    return {
        "sample_plan": json.loads((PROJECT_ROOT / "data" / "sample_valid_plan.json").read_text())["semesters"],
        "courses": courses,
        "requirements": requirements,
        "template": template,
        "nontech_rules": nontech_rules,
        "concentrations": concentrations,
        "minors": minors,
        "minor_global_rules": minor_global_rules,
    }
