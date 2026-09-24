"""
Serializes/parses a course plan (semesters + credit overrides + AP/
placement/transfer/waiver overrides) to and from JSON, CSV, and Excel
bytes, for the app's download/upload buttons.

Each function here works with plain data (dicts/lists/bytes) and doesn't
touch the course catalog or Streamlit -- App.py is responsible for
resolving aliases and validating course ids against the catalog after
parsing, exactly as it already does for JSON.
"""

import csv
import io
import json

import openpyxl

CSV_FIELDNAMES = ["type", "semester", "course_id", "course_title", "credit_override"]

XLSX_PLAN_SHEET = "Plan"
XLSX_OVERRIDES_SHEET = "Credit Overrides"
XLSX_AP_SHEET = "AP-Placement-Transfer-Waiver"


def _course_title(catalog, course_id):
    return (catalog.get(course_id) or {}).get("title") or ""


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def plan_to_json_bytes(plan, credit_overrides, prerequisite_overrides):
    payload = {
        "plan": plan,
        "credit_overrides": credit_overrides,
        "prerequisite_overrides": sorted(prerequisite_overrides),
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def plan_from_json_bytes(data: bytes):
    payload = json.loads(data.decode("utf-8"))
    return (
        payload.get("plan", {}),
        payload.get("credit_overrides", {}),
        list(payload.get("prerequisite_overrides", [])),
    )


# ---------------------------------------------------------------------------
# CSV -- one flat table; "type" distinguishes a planned course from an
# AP/placement/transfer/waiver entry (which has no semester).
# ---------------------------------------------------------------------------

def plan_to_csv_bytes(plan, credit_overrides, prerequisite_overrides, catalog):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()

    for semester, course_ids in plan.items():
        for course_id in course_ids:
            writer.writerow({
                "type": "course",
                "semester": semester,
                "course_id": course_id,
                "course_title": _course_title(catalog, course_id),
                "credit_override": credit_overrides.get(course_id, ""),
            })

    for course_id in sorted(prerequisite_overrides):
        writer.writerow({
            "type": "ap_credit",
            "semester": "",
            "course_id": course_id,
            "course_title": _course_title(catalog, course_id),
            "credit_override": "",
        })

    return buf.getvalue().encode("utf-8")


def plan_from_csv_bytes(data: bytes, semesters):
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    plan = {s: [] for s in semesters}
    credit_overrides = {}
    prerequisite_overrides = []

    for row in reader:
        course_id = (row.get("course_id") or "").strip()
        if not course_id:
            continue

        row_type = (row.get("type") or "course").strip().lower()

        if row_type == "ap_credit":
            prerequisite_overrides.append(course_id)
            continue

        semester = (row.get("semester") or "").strip()
        if semester in plan:
            plan[semester].append(course_id)

        override = (row.get("credit_override") or "").strip()
        if override:
            try:
                credit_overrides[course_id] = float(override)
            except ValueError:
                pass

    return plan, credit_overrides, prerequisite_overrides


# ---------------------------------------------------------------------------
# Excel -- one sheet per concern, since a workbook can hold that naturally
# ---------------------------------------------------------------------------

def plan_to_xlsx_bytes(plan, credit_overrides, prerequisite_overrides, catalog):
    wb = openpyxl.Workbook()

    ws_plan = wb.active
    ws_plan.title = XLSX_PLAN_SHEET
    ws_plan.append(["Semester", "Course ID", "Course Title"])
    for semester, course_ids in plan.items():
        for course_id in course_ids:
            ws_plan.append([semester, course_id, _course_title(catalog, course_id)])

    ws_overrides = wb.create_sheet(XLSX_OVERRIDES_SHEET)
    ws_overrides.append(["Course ID", "Credits"])
    for course_id, credits in sorted(credit_overrides.items()):
        ws_overrides.append([course_id, credits])

    ws_ap = wb.create_sheet(XLSX_AP_SHEET)
    ws_ap.append(["Course ID", "Course Title"])
    for course_id in sorted(prerequisite_overrides):
        ws_ap.append([course_id, _course_title(catalog, course_id)])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def plan_from_xlsx_bytes(data: bytes, semesters):
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)

    plan = {s: [] for s in semesters}
    credit_overrides = {}
    prerequisite_overrides = []

    if XLSX_PLAN_SHEET in wb.sheetnames:
        for row in wb[XLSX_PLAN_SHEET].iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not row[1]:
                continue
            semester, course_id = row[0], row[1]
            if semester in plan:
                plan[semester].append(course_id)

    if XLSX_OVERRIDES_SHEET in wb.sheetnames:
        for row in wb[XLSX_OVERRIDES_SHEET].iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or row[1] is None:
                continue
            try:
                credit_overrides[row[0]] = float(row[1])
            except (TypeError, ValueError):
                pass

    if XLSX_AP_SHEET in wb.sheetnames:
        for row in wb[XLSX_AP_SHEET].iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            prerequisite_overrides.append(row[0])

    return plan, credit_overrides, prerequisite_overrides
