# Columbia ChemE Course Planner

A Streamlit app for planning a Columbia Chemical Engineering B.S. degree
semester by semester, and checking that plan against the major's actual
requirements: required courses, math/physics/chemistry foundations,
technical electives (thermo/transport/engineering/advanced STEM buckets),
the nontechnical requirement (Core sequence, art/music, electives), natural
science lab, physical education, prerequisites, and per-semester credit
load.

Originally started as a final project for COMS W2132 (Intermediate
Computing in Python); this document describes what's actually built today
rather than the original project pitch.

## Quick start

```bash
pip install -r requirements.txt
streamlit run App.py
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

`tests/` covers the validation engine and the data-loading/alias-merge logic:
small synthetic-catalog unit tests for individual checks (duplicate/
repeatable-course handling, alias resolution, the nontech "custom" policy
fix, offering-term mismatch detection, minor/concentration group types),
plus a handful of integration tests against the real catalog and
`data/sample_valid_plan.json`. Runs automatically on every push via GitHub
Actions (`.github/workflows/tests.yml`).

## What it does

- Build a semester-by-semester plan by picking courses into 8 semester
  slots (defaults to a standard 4-year template).
- Validate the plan and see: total credits, major-required course
  progress, technical elective breakdown, nontechnical credit tracking,
  Core sequence / art-or-music status, and foundational requirements
  (math/physics/chemistry/lab/PE).
- Mark courses as satisfied by AP/placement/transfer credit or a waiver --
  these count toward every requirement they'd satisfy, but (since we don't
  track how many real Columbia points, if any, they carry) they don't
  inflate credit totals.
- Get warnings for: duplicate courses across semesters, prerequisite
  violations, semesters under/over the SEAS full-time credit range
  (12-21 credits), and courses scheduled in a semester their published
  offering pattern doesn't match.
- Save/load a plan as JSON, CSV, or Excel (there's no backend, so this is
  how a plan survives between sessions) -- pick the format from a radio
  button; import auto-detects it from the uploaded file's extension.
- Track progress toward ChemE's 4 elective specializations (shown
  automatically) and toward any of Columbia Engineering's 49 minors
  (pick which ones to track from a sidebar list) -- both purely
  informational, neither gates graduation in this app.
- A "Requirements Reference" panel lists the actual courses behind math
  foundation, physics, chemistry, and Advanced STEM technical electives,
  plus Columbia's official AP/IB/A-level credit chart -- each with a link
  to the bulletin page it's sourced from. Every requirement, concentration,
  and minor result in the Validation Results also links to its own source.

## Architecture

- **Data layer** (`data/`) -- JSON course catalogs and requirement
  definitions. See [Data model](#data-model) below.
- **Validation engine** (`src/validator.py`) -- pure functions that take a
  plan + the catalogs and return errors, warnings, and a `progress` dict
  covering every requirement category.
- **UI** (`App.py`) -- Streamlit app that renders the plan editor and the
  validation results.
- **Data pipeline** (`scripts/`) -- one-off/rerunnable scripts that build
  the JSON catalogs from raw sources (see below). These aren't run by the
  app itself; they're how `data/*.json` got built and how you'd refresh
  them.

## Data model

Three course catalogs, merged at load time by `src/load_data.py`:

| File | Built by | Source |
|---|---|---|
| `data/courses_core.json` | hand-curated | Columbia Engineering Bulletin |
| `data/courses_tech_electives.json` | `scripts/loading_tech.py` | `data/raw/Electives Course List-New Study Plan.xlsx` |
| `data/courses_globalcore.json` | `scripts/load_global_core.py` | `data/raw/global_core_requirement.pdf` |

`data/requirements.json` encodes the actual degree requirements (major
required courses, math foundation, physics/chemistry sequences, technical
elective sub-buckets, nontechnical requirement incl. Core sequence and
art/music, natural science lab, physical education). `data/nontech_rules.json`
encodes which subjects count toward the nontechnical elective requirement,
by department policy (`all` / `none` / `only` / `all_except` / `custom`).

Each course entry may carry:
- `credits`, `prerequisites`, `corequisites`, `category_tags` -- the core
  fields the validator checks against.
- `aliases` -- alternate/legacy ids for the same course (e.g. a pre-"UN"
  numbering). The loader merges an aliased duplicate into its canonical
  entry instead of treating it as a second course; the validator resolves
  a plan's course ids through this before checking anything.
- `terms_checked` / `terms_offered` -- which term(s) (`Fall2026`,
  `Spring2027`) a course was found scheduled in, and which term pages were
  actually checked for its subject, per `scripts/fetch_offering_terms.py`.
- `repeat_rules` -- for repeatable courses (currently just
  `CHEN_E3900`, Undergraduate Research), how many instances count toward
  the technical elective requirement and when the department's thesis
  requirement kicks in.
- `credits_source` -- which backfill pass supplied a missing credit value.

Requirements, concentrations, and minors also carry a `source_url` field
pointing at the bulletin page they were transcribed from, added by
`scripts/add_source_links.py`. `data/ap_credit_chart.json` (same script)
is Columbia Engineering's official AP/IB/A-level credit chart -- reference
data only, since several rows are contingent on a grade in a specific
follow-on course, which this app has no way to verify.

### Known data coverage limits

Both the credit and offering-term backfills are sourced from *schedule*
data (the Engineering Bulletin's current course listings, and Columbia's
live Directory of Classes) -- they only know about courses actually being
taught this academic year, not the full historical set of approved
courses. As of the last data pipeline run:

- **Credits: ~40% of the catalog** has a real value; the rest rely on the
  in-app credit override (enter it once, it's remembered for the session
  and exported with the plan). This is treated as the intended long-term
  answer for the remainder, not a gap to keep chasing.
- **Prerequisites: ~7% of the catalog** has prerequisite data -- the
  hand-curated major-required courses, plus a bulletin-sourced backfill
  (`scripts/backfill_prerequisites.py`) for courses whose "Prerequisites:
  ..." clause named other courses unambiguously (AND-only, no "or"
  between two real courses, no PDF line-wrap truncation). Deliberately
  conservative: a course description with no clean course-code match
  (prose like "Instructor's permission", an "or"-alternative between two
  courses) is left with empty `prerequisites` and the raw clause
  preserved as a note instead of guessed at -- a wrong prerequisite is
  worse than a missing one. Same schedule-based ceiling as credits, so
  most electives still won't flag a real violation.
- **True cross-department cross-listing** (a course offered under two
  departments' subject codes) isn't available from any source reachable
  without a Columbia login (Vergil is UNI-gated); the `aliases` mechanism
  only covers legacy/alternate id spellings for the *same* course, not
  cross-listings.

### Not implemented

- **Grades / pass-fail.** The plan doesn't record grades, so GPA and
  pass/fail eligibility rules (e.g. only two nontechnical electives and PE
  may be taken P/F, minors require a 2.0 GPA and no P/F courses) aren't
  checked anywhere, including within `data/minors.json`'s own rules.

### Concentrations and minors: what to trust

`data/concentrations.json` (ChemE's 4 elective specializations) is high
confidence -- sourced from a single clean bulletin table each, fully
structured, every referenced course resolves.

`data/minors.json` (all 49 non-ChemE Engineering minors) is a first pass,
not verified against advisors. 43 of 49 have a real group-based structure
(required courses, choose-one/choose-N, subject/level-range rules); 6
(Aerospace, Architecture, Art History, Catalan, Greek/Latin, MESAAS) have
requirements that don't reduce to a checkable rule at all and are marked
`"unstructured": true` with the bulletin's description preserved instead
of a guessed structure. Several structured minors also have individual
`free_form` groups for a specific clause that couldn't be resolved to a
course list. None of this is enforced as a real requirement -- minors are
purely informational in the UI, selected per-viewing from a sidebar picker.

## Data pipeline scripts

Run from the project root. Each is idempotent -- rerunning just refreshes
whatever it covers.

- `scripts/loading_tech.py` -- builds `courses_tech_electives.json` from
  the electives spreadsheet.
- `scripts/load_global_core.py` -- builds `courses_globalcore.json` from
  the Global Core PDF.
- `scripts/backfill_credits.py` -- fills missing `credits` from the
  Engineering Bulletin PDF, then from `data/raw/doc_of_classes_credits.json`
  (built by `scripts/fetch_doc_credits.py`, which hits Columbia's live
  Directory of Classes for a given set of subjects).
- `scripts/fetch_offering_terms.py` + `scripts/backfill_terms.py` -- same
  idea for `terms_offered`/`terms_checked`, also via the Directory of
  Classes.
- `scripts/backfill_prerequisites.py` -- fills missing `prerequisites`
  from the Engineering Bulletin PDF's "Prerequisites: ..." clauses. Adds
  any referenced course that's a real, current Columbia course simply
  missing from our scoped catalog; retired pre-2015 course codes (single-
  letter V/C/W prefixes) are remapped to their modern UN/GU equivalent
  when one exists in the catalog, and left unresolved (note only) when it
  doesn't, rather than inventing an unsatisfiable phantom prerequisite.
- `scripts/add_specialization_data.py` -- writes `data/concentrations.json`
  (ChemE's 4 elective specializations) from the ChemE bulletin page, and
  adds any course catalog entries they reference that were missing.
- `scripts/add_minors_data.py` -- writes `data/minors.json` (all 49
  non-ChemE Engineering minors) from each minor's own bulletin page, same
  missing-course backfill as above.
- `scripts/add_source_links.py` -- adds `source_url` to every requirement,
  concentration, and minor, and writes `data/ap_credit_chart.json`.

## Project structure

```
App.py                   Streamlit UI
src/
  load_data.py            Loads + merges the course catalogs
  validator.py             Validation engine
  plan_io.py               Plan <-> JSON/CSV/Excel bytes (save/load)
data/
  courses_core.json
  courses_tech_electives.json
  courses_globalcore.json
  requirements.json        Degree requirement definitions
  nontech_rules.json       Nontechnical-elective subject policy
  concentrations.json      ChemE's 4 elective specializations
  minors.json              All 49 non-ChemE Engineering minors
  ap_credit_chart.json     Official AP/IB/A-level credit chart (reference only)
  template.json            Default 8-semester plan skeleton
  sample_valid_plan.json   Fixture plan
  raw/                     Source documents + pipeline caches
scripts/                  Data pipeline (see above)
tests/                    pytest suite (see "Running the tests")
.github/workflows/        CI: runs the test suite on every push
```

## Author

- [Sophie Zhu](https://github.com/syz-2014)
