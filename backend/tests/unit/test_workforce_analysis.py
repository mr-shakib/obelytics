"""Code-side work of the workforce analysis: counting demand and checking the model's claims."""
from app.modules.workforce.analysis import CourseOutcomeRow, aggregate, build_result, clean_skills


def _row(ref, pos=()):
    course, co = ref.split("/")
    return CourseOutcomeRow(ref=ref, co_id=f"id-{ref}", co_code=co, course_id=f"c-{course}",
                            course_code=course, course_title=course, statement="...", po_codes=list(pos))


def test_clean_skills_dedupes_and_defaults():
    skills = clean_skills([
        {"name": " SQL. ", "category": "technical", "required": True},
        {"name": "sql", "category": "technical", "required": False},
        {"name": "Teamwork", "category": "people", "required": False},
        {"name": "", "category": "technical"},
        "junk",
    ])
    assert skills == [
        {"name": "SQL", "category": "technical", "required": True},
        {"name": "Teamwork", "category": "technical", "required": False},
    ]


def test_aggregate_counts_postings_per_skill_most_first():
    demands = aggregate([
        ("Backend", [{"name": "SQL", "category": "technical", "required": True},
                     {"name": "Docker", "category": "technical", "required": False}]),
        ("Data", [{"name": "sql", "category": "technical", "required": True}]),
    ])
    assert [(d.name, d.postings, d.required) for d in demands] == [("SQL", 2, 2), ("Docker", 1, 0)]
    assert demands[0].titles == ["Backend", "Data"]


def test_build_result_checks_references_and_weights_by_demand():
    demands = aggregate([
        ("A", [{"name": "SQL", "category": "technical", "required": True},
               {"name": "Docker", "category": "technical", "required": True}]),
        ("B", [{"name": "SQL", "category": "technical", "required": True},
               {"name": "Kubernetes", "category": "technical", "required": True}]),
    ])
    outcomes = [_row("CSE202/CO1", ["PO1", "PO3"]), _row("CSE305/CO2", ["PO5"])]
    result = build_result(
        demands,
        [
            {"skill": "SQL", "coverage": "covered", "outcomes": ["CSE202/CO1", "XYZ/CO9"], "reason": "r",
             "suggested_course": "CSE305"},
            {"skill": "Docker", "coverage": "partial", "outcomes": ["NOPE/CO1"], "reason": "r",
             "suggested_course": "CSE305"},
            {"skill": "Imaginary", "coverage": "covered", "outcomes": [], "reason": "r"},
        ],
        outcomes,
        {"CSE305": {"id": "c-CSE305", "code": "CSE305", "title": "Cloud"}},
        [{"code": "PO1", "statement": "s"}, {"code": "PO5", "statement": "s"}],
        posting_count=2,
    )
    skills = {s["skill"]: s for s in result["skills"]}
    assert [o["ref"] for o in skills["SQL"]["outcomes"]] == ["CSE202/CO1"]  # made-up ref dropped
    assert skills["SQL"]["program_outcomes"] == ["PO1", "PO3"]
    assert skills["SQL"]["suggested_course"] is None  # covered: nothing to add
    # Claimed partial coverage with no real CO is a gap.
    assert skills["Docker"]["coverage"] == "gap" and skills["Docker"]["notes"]
    assert skills["Docker"]["suggested_course"]["code"] == "CSE305"
    assert skills["Kubernetes"]["coverage"] == "unjudged"
    # SQL (2 postings) covered, Docker (1) gap, Kubernetes not judged → 2 / 3
    assert result["summary"]["coverage_pct"] == 66.7
    assert {p["code"]: p["demand"] for p in result["program_outcomes"]} == {"PO1": 2, "PO5": 0}
