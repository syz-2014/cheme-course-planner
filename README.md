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

## What it does

- Build a semester-by-semester plan by picking courses into 8 semester
  slots (defaults to a standard 4-year template).
- Validate the plan and see: total credits, major-required course
  progress, technical elective breakdown, nontechnical credit tracking,
  Core sequence / art-or-music status, foundational requirements
  (math/physics/chemistry/lab/PE), and course recommendations based on
  what's still missing and stated interests.
- Mark courses as satisfied by AP/placement/transfer credit or a waiver --
  these count toward every requirement they'd satisfy, but (since we don't
  track how many real Columbia points, if any, they carry) they don't
  inflate credit totals.
- Get warnings for: duplicate courses across semesters, prerequisite
  violations, semesters under/over the SEAS full-time credit range
  (12-21 credits), and courses scheduled in a semester their published
  offering pattern doesn't match.
- Save/load a plan as a JSON file (there's no backend, so this is how a
  plan survives between sessions).

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
- **Prerequisites: ~2% of the catalog** has prerequisite data -- only the
  major-required courses that were hand-curated. Prerequisite checking is
  real but only meaningfully exercised for those; electives largely won't
  flag a prerequisite violation even if one exists. There's no
  comprehensive source for this short of manual entry.
- **True cross-department cross-listing** (a course offered under two
  departments' subject codes) isn't available from any source reachable
  without a Columbia login (Vergil is UNI-gated); the `aliases` mechanism
  only covers legacy/alternate id spellings for the *same* course, not
  cross-listings.

### Not implemented

- **Concentrations/minors.** ChemE's own elective specializations (Climate/
  Environment/Energy, Biotech/Biopharma, Data & Computational Science,
  Advanced Materials) and any minor tracks aren't modeled at all -- no
  schema, no requirement rules, no UI.
- **Grades / pass-fail.** The plan doesn't record grades, so GPA and
  pass/fail eligibility rules (e.g. only two nontechnical electives and PE
  may be taken P/F) aren't checked.
- Automated tests. `data/sample_valid_plan.json` is a hand-built fixture,
  not yet backed by a test suite.

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

## Project structure

```
App.py                   Streamlit UI
src/
  load_data.py            Loads + merges the three course catalogs
  validator.py             Validation engine
data/
  courses_core.json
  courses_tech_electives.json
  courses_globalcore.json
  requirements.json        Degree requirement definitions
  nontech_rules.json       Nontechnical-elective subject policy
  template.json            Default 8-semester plan skeleton
  sample_valid_plan.json   Fixture plan
  raw/                     Source documents + pipeline caches
scripts/                  Data pipeline (see above)
```

## Author

- [Sophie Zhu](https://github.com/syz-2014)
