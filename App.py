import hashlib
import json

import streamlit as st

from src.load_data import load_all_data
from src.validator import (
    validate_plan, recommend_courses, count_credits,
    SEMESTER_CREDIT_MIN, SEMESTER_CREDIT_MAX,
    build_alias_index, resolve_course_id
)

TECH_REQUIREMENTS = {
    "thermo": {
        "tag": "thermo_elective",
        "required": 1,
        "label": "Thermodynamics"
    },
    "transport": {
        "tag": "transport_elective",
        "required": 1,
        "label": "Transport"
    },
    "engineering": {
        "tag": "engineering_tech_elective",
        "required": 3,
        "label": "Engineering"
    },
    "advanced_stem": {
        "tag": "advanced_stem_tech_elective",
        "required": 2,
        "label": "Advanced STEM"
    }
}

TAG_LABELS = {
    "thermo_elective": "Thermodynamics elective",
    "transport_elective": "Transport elective",
    "engineering_tech_elective": "Engineering technical elective",
    "advanced_stem_tech_elective": "Advanced STEM elective",
    "math_elective": "Math elective",
    "technical_elective": "Technical elective"
}

st.set_page_config(page_title="ChemE Course Planner", layout="wide")

courses, requirements, template, nontech_rules = load_all_data()

st.title("Columbia Chemical Engineering Course Planner")

st.expander(
    "Program Accreditation, Educational Objectives, and Student Outcomes",
    expanded=False
).markdown("""
**Accreditation**

The Chemical Engineering program is accredited by the Engineering Accreditation Commission of ABET (https://www.abet.org), under the commission's General Criteria and Program Criteria for Chemical, Biochemical, Biomolecular and similarly named engineering programs.

**Program Educational Objectives**  
(Expectations of what graduates are expected to attain within a few years of graduation)

- Careers in industries that require technical expertise in chemical engineering.  
- Leadership positions in industries that require technical expertise in chemical engineering.  
- Graduate-level studies in chemical engineering and related technical or scientific fields (e.g. biomedical or environmental engineering, materials science).  
- Careers outside of engineering that take advantage of an engineering education, such as business, management, finance, law, medicine, or education.  
- A commitment to life-long learning and service within their chosen profession.  

**Student Outcomes**  
(Upon graduation, students are expected to achieve the following)

- An ability to identify, formulate, and solve complex engineering problems by applying principles of engineering, science, and mathematics.  
- An ability to apply engineering design to produce solutions that meet specified needs with consideration of public health, safety, and welfare, as well as global, cultural, social, environmental, and economic factors.  
- An ability to communicate effectively with a range of audiences.  
- An ability to recognize ethical and professional responsibilities in engineering situations and make informed judgments, considering global, economic, environmental, and societal impacts.  
- An ability to function effectively on teams that provide leadership, foster collaboration, establish goals, plan tasks, and meet objectives.  
- An ability to develop and conduct appropriate experimentation, analyze and interpret data, and use engineering judgment to draw conclusions.  
- An ability to acquire and apply new knowledge as needed using appropriate learning strategies.  
""")

st.write(
    "Build a semester-by-semester course plan and check progress toward "
    "major, technical elective, nontechnical, and graduation requirements."
)


def format_course_option(course_id):
    course = courses.get(course_id, {})
    title = course.get("title") or "Untitled"
    return f"{course_id} — {title}"


def course_box(course_id):
    course = courses.get(course_id, {})
    title = course.get("title", "Untitled")
    credits = course.get("credits", "credits unknown")
    tags = course.get("category_tags", [])

    color = "#f5f5f5"

    if "technical_elective" in tags:
        color = "#fff3cd"
    elif "global_core" in tags or "nontechnical" in tags or "nontechnical_core_required" in tags:
        color = "#d4edda"
    elif "math_elective" in tags or "math_foundation" in tags:
        color = "#dbeafe"
    elif "major_required" in tags or "chen_core" in tags:
        color = "#f8d7da"

    return f"""
    <div style="
        border: 2px solid #444;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        background-color: {color};
        text-align: center;
        min-height: 105px;
    ">
        <b>{course_id}</b><br>
        <span style="font-size: 0.85em;">{title}</span><br>
        <span style="font-size: 0.8em;">{credits} credits</span>
    </div>
    """


course_options = sorted(courses.keys())

st.sidebar.header("Planner Settings")

show_sequence_graph = st.sidebar.checkbox(
    "Show semester sequence graph",
    value=False
)

if "plan" not in st.session_state:
    st.session_state.plan = template["semesters"].copy()

if "saved_credit_overrides" not in st.session_state:
    st.session_state.saved_credit_overrides = {}


# -----------------------------
# Save / load plan
# -----------------------------
st.sidebar.subheader("Save / Load Plan")

export_payload = {
    "plan": st.session_state.plan,
    "credit_overrides": st.session_state.saved_credit_overrides,
    "prerequisite_overrides": st.session_state.get("prerequisite_overrides", [])
}

st.sidebar.download_button(
    "Download plan as JSON",
    data=json.dumps(export_payload, indent=2),
    file_name="cheme_course_plan.json",
    mime="application/json"
)

uploaded_plan = st.sidebar.file_uploader(
    "Upload a saved plan (JSON)",
    type="json"
)

if uploaded_plan is not None:
    file_bytes = uploaded_plan.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    if st.session_state.get("_last_imported_plan_hash") != file_hash:
        try:
            imported = json.loads(file_bytes)
        except json.JSONDecodeError:
            imported = None
            st.sidebar.error("That file isn't valid JSON.")

        if imported is not None:
            imported_plan = imported.get("plan", {})
            dropped_courses = []
            alias_index = build_alias_index(courses)

            for semester in st.session_state.plan.keys():
                raw_courses = imported_plan.get(semester, [])
                resolved_courses = [
                    resolve_course_id(c, courses, alias_index) for c in raw_courses
                ]
                valid_courses = [c for c in resolved_courses if c in course_options]
                dropped_courses.extend(
                    c for c in resolved_courses if c not in course_options
                )

                st.session_state.plan[semester] = valid_courses
                st.session_state[semester] = valid_courses

            st.session_state.saved_credit_overrides = imported.get("credit_overrides", {})
            st.session_state["prerequisite_overrides"] = [
                c for c in imported.get("prerequisite_overrides", [])
                if c in course_options
            ]
            st.session_state["_last_imported_plan_hash"] = file_hash

            if dropped_courses:
                st.sidebar.warning(
                    "Ignored unrecognized course id(s) in upload: "
                    f"{', '.join(sorted(set(dropped_courses)))}"
                )

            st.sidebar.success("Plan imported.")
            st.rerun()


st.sidebar.subheader("Recommendation Preferences")

interest_text = st.sidebar.text_input(
    "What topics are you interested in?",
    placeholder="e.g., energy, biotech, polymers, data, environment"
)
interests = [
    item.strip()
    for item in interest_text.split(",")
    if item.strip()
]


# -----------------------------
# Main view
# -----------------------------
if not show_sequence_graph:
    st.header("Semester Plan")

    for semester, course_list in st.session_state.plan.items():
        with st.expander(semester.replace("_", " ").title(), expanded=True):
            selected = st.multiselect(
                "Courses",
                options=course_options,
                default=[c for c in course_list if c in course_options],
                key=semester
            )

            st.session_state.plan[semester] = selected

            if selected:
                semester_credits, _ = count_credits(
                    selected, courses,
                    st.session_state.get("saved_credit_overrides", {})
                )
                if semester_credits < SEMESTER_CREDIT_MIN:
                    st.caption(f"{semester_credits:g} credits (below the "
                               f"{SEMESTER_CREDIT_MIN}-credit full-time minimum)")
                elif semester_credits > SEMESTER_CREDIT_MAX:
                    st.caption(f"{semester_credits:g} credits (exceeds the "
                               f"{SEMESTER_CREDIT_MAX}-credit maximum without approval)")
                else:
                    st.caption(f"{semester_credits:g} credits")

            if selected:
                show_details = st.checkbox(
                    "Show selected course details",
                    value=False,
                    key=f"show_details_{semester}"
                )

                if show_details:
                    for course_id in selected:
                        course = courses.get(course_id, {})
                        st.text(
                            f"{course_id} — {course.get('title', 'Untitled')} "
                            f"({course.get('credits', 'credits unknown')} credits)"
                        )

else:
    st.header("Semester Sequence Visualization")

    semesters = list(st.session_state.plan.keys())
    cols = st.columns(len(semesters))

    for i, semester in enumerate(semesters):
        with cols[i]:
            st.subheader(semester.replace("_", " ").title())

            course_list = st.session_state.plan[semester]

            if course_list:
                for course_id in course_list:
                    st.markdown(
                        course_box(course_id),
                        unsafe_allow_html=True
                    )
            else:
                st.info("No courses selected.")


# -----------------------------
# Missing credit overrides
# -----------------------------
selected_courses_flat = [
    course
    for semester_courses in st.session_state.plan.values()
    for course in semester_courses
]

missing_credit_courses = sorted({
    course_id
    for course_id in selected_courses_flat
    if (
        course_id in courses
        and courses[course_id].get("credits") is None
        and course_id not in st.session_state.saved_credit_overrides
    )
})

if missing_credit_courses:
    st.sidebar.subheader("Missing Credit Information")
    st.sidebar.info(
        "Some selected courses are missing credit values. "
        "Enter and save credits below."
    )

    with st.sidebar.form("missing_credit_form"):
        temporary_credit_inputs = {}

        for course_id in missing_credit_courses:
            title = courses[course_id].get("title", "")

            temporary_credit_inputs[course_id] = st.number_input(
                f"{course_id}: {title}",
                min_value=0.5,
                max_value=6.0,
                value=3.0,
                step=0.5
            )

        saved = st.form_submit_button("Save credit values")

        if saved:
            for course_id, credits in temporary_credit_inputs.items():
                st.session_state.saved_credit_overrides[course_id] = credits

            st.rerun()

credit_overrides = st.session_state.saved_credit_overrides


# -----------------------------
# Prerequisite overrides
# -----------------------------
st.sidebar.subheader("Prerequisite Overrides")

override_courses = st.sidebar.multiselect(
    "Courses already satisfied by AP, placement, transfer credit, or waiver",
    options=course_options,
    default=[],
    key="prerequisite_overrides",
    help="These courses will be treated as completed before semester 1."
)


# -----------------------------
# Validate plan
# -----------------------------
if st.button("Validate Plan"):
    results = validate_plan(
        st.session_state.plan,
        courses,
        requirements,
        nontech_rules,
        prerequisite_overrides=set(override_courses),
        credit_overrides=credit_overrides
    )

    progress = results["progress"]

    st.header("Validation Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Credits",
            progress.get("total_credits", 0),
            f"of {requirements['total_degree_credits']}"
        )

    with col2:
        st.metric(
            "Major Required Courses",
            f"{progress.get('major_required_completed', 0)} / "
            f"{progress.get('major_required_total', 0)}"
        )

    with col3:
        st.metric(
            "Technical Electives",
            f"{progress.get('technical_electives_completed', 0)} / "
            f"{progress.get('technical_electives_required', 7)}"
        )

    if progress.get("math_elective_completed"):
        st.success("Math elective completed.")
    else:
        st.warning("Math elective not completed.")

    missing_major = progress.get("missing_major_required", [])
    if missing_major:
        st.warning("Missing major required courses:")
        st.write(missing_major)
    else:
        st.success("All major required courses completed.")

    if results["warnings"]:
        st.subheader("Warnings")
        for warning in results["warnings"]:
            st.warning(warning)

    if results["errors"]:
        st.subheader("Errors")
        for error in results["errors"]:
            st.error(error)
    else:
        st.success("No major validation errors found.")

    st.subheader("Foundational Requirements")

    math_foundation = progress.get("math_foundation_requirement", {})
    if math_foundation.get("completed"):
        st.success("Math foundation (Calculus I & II, Multivariable Calculus, "
                    "and one of ODE/Applied Math) completed.")
    else:
        missing_required = math_foundation.get("missing_required", [])
        if missing_required:
            st.warning(f"Math foundation missing required course(s): {', '.join(missing_required)}")
        if not math_foundation.get("choose_one_satisfied"):
            options = math_foundation.get("choose_one_of", [])
            st.warning(f"Math foundation: choose one of {', '.join(options)} (not yet satisfied).")

    physics_status = progress.get("physics_requirement", {})
    if physics_status.get("completed"):
        st.success(f"Physics sequence completed: {', '.join(physics_status['sequence_completed'])}")
    else:
        st.warning("Physics sequence not completed. Choose one full sequence.")

    chemistry_status = progress.get("chemistry_requirement", {})
    if chemistry_status.get("completed"):
        st.success(f"Chemistry sequence completed: {', '.join(chemistry_status['sequence_completed'])}")
    else:
        st.warning("Chemistry sequence not completed. Choose one full sequence.")

    nat_sci_lab = progress.get("natural_science_lab_requirement", {})
    st.write(
        f"Natural Science Lab: {nat_sci_lab.get('credits_found', 0):g} / "
        f"{nat_sci_lab.get('credits_min', 3)} credits"
    )
    if nat_sci_lab.get("completed"):
        st.success("Natural science lab requirement satisfied.")
    else:
        st.warning("Natural science lab requirement not yet satisfied.")

    missing_pe = progress.get("missing_physical_education", [])
    if missing_pe:
        st.warning(f"Missing physical education course(s): {', '.join(missing_pe)}")
    else:
        st.success("Physical education requirement satisfied.")

    st.subheader("Technical Elective Breakdown")

    tech = progress.get("tech_breakdown", {})

    for key, config in TECH_REQUIREMENTS.items():
        completed = tech.get(key, 0)
        required = config["required"]
        label = config["label"]

        st.write(f"{label}: {completed} / {required}")

        if completed >= required:
            st.success(f"{label} requirement satisfied.")
        else:
            st.warning(f"Need {required - completed} more {label} elective(s).")

    st.subheader("Nontechnical Requirement")

    nontech_credits = progress.get("nontech_credits", 0)

    st.metric(
        "Nontechnical Credits",
        nontech_credits,
        "of 27 required"
    )

    if progress.get("nontech_completed"):
        st.success("Nontechnical requirement satisfied.")
    else:
        st.warning("Nontechnical requirement not yet satisfied.")

    missing_nontech_required = progress.get("missing_nontech_required_courses", [])
    if missing_nontech_required:
        st.warning(f"Missing required nontechnical course(s): {', '.join(missing_nontech_required)}")
    else:
        st.success("Required nontechnical courses (ENGL_CC1010, ECON_UN1105) completed.")

    elective_credits = progress.get("elective_nontechnical_credits")
    elective_min = progress.get("elective_nontechnical_min")
    elective_max = progress.get("elective_nontechnical_max")
    if elective_credits is not None:
        st.write(
            f"Elective nontechnical credits (beyond required courses, core "
            f"sequence, and art/music): {elective_credits:g}, expected "
            f"{elective_min}-{elective_max}"
        )

    st.subheader("Core Sequence Requirement")

    core_status = progress.get("core_sequence_requirement", {})

    if core_status.get("completed"):
        path = core_status.get("path_completed")

        if path == "literature_humanities":
            st.success("Core sequence completed through Literature Humanities.")
        elif path == "contemporary_civilization":
            st.success("Core sequence completed through Contemporary Civilization.")
        elif path == "global_core":
            st.success("Core sequence completed through Global Core.")
    else:
        st.warning(
            "Core sequence not completed. Choose one path: "
            "Literature Humanities I & II, Contemporary Civilization I & II, "
            "or two approved Global Core courses."
        )

    st.write("Literature Humanities:", core_status.get("lit_hum_completed", False))
    st.write("Contemporary Civilization:", core_status.get("cc_completed", False))
    st.write(
        "Global Core:",
        f"{len(core_status.get('global_core_courses_found', []))} / "
        f"{core_status.get('global_core_courses_required', 2)}"
    )

    st.subheader("Art or Music Humanities")

    art_music = progress.get("art_or_music_humanities", {})

    if art_music.get("completed"):
        st.success("Art/Music Humanities requirement completed.")
        st.write("Course found:", art_music.get("courses_found", []))
    else:
        st.warning("Need either Art Humanities or Music Humanities.")

    st.subheader("Recommended Courses")

    recommendations = recommend_courses(
        courses,
        progress,
        interests=interests
    )

    def explain_recommendation(rec):
        reasons = []

        # Requirement reason
        for tag in rec["matched_requirements"]:
            readable = tag.replace("_", " ").title()
            reasons.append(f"Helps fulfill {readable}")

        # Interest reason
        if rec["matched_interests"]:
            interest_str = ", ".join(rec["matched_interests"])
            reasons.append(f"aligns with your interest in {interest_str}")

        return " and ".join(reasons)


    if recommendations:
        for rec in recommendations:
            explanation = explain_recommendation(rec)

            st.write(
                f"**{rec['course_id']}** — {rec['title']} "
                f"({rec['credits'] if rec['credits'] else 'credits unknown'} credits)"
            )

            st.caption(explanation)
    else:
        st.success("No recommendations needed.")    