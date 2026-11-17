"""Workforce: merging near-duplicate skills, importing real postings, a student's verified skills."""
from datetime import UTC, datetime

import pytest

from app.modules.workforce.analysis import aggregate, canonical_key
from app.modules.workforce.importing import (
    ImportFailedError,
    _check_url,
    read_csv,
    read_page,
)
from app.modules.workforce.service import build_student_skills


def _skill(name, required=True):
    return {"name": name, "category": "technical", "required": required}


# ── Merging near-duplicate skill names ───────────────────────────────────────

def test_aliases_and_filler_words_fold_into_one_skill():
    assert canonical_key("JS") == canonical_key("JavaScript") == "javascript"
    assert canonical_key("Strong communication") == "communication"
    assert canonical_key("Experience with Docker") == "docker"
    assert canonical_key("REST API") == canonical_key("RESTful APIs") == "rest apis"


def test_generic_suffix_folds_only_when_the_head_skill_is_also_asked_for():
    demands = {d.name: d for d in aggregate([
        ("A", [_skill("Python")]),
        ("B", [_skill("Python scripting")]),
        ("C", [_skill("Competitive programming")]),
    ])}
    assert demands["Python"].postings == 2
    assert demands["Python"].aliases == ["Python scripting"]
    # "competitive" alone was never asked for, so the phrase stays a skill of its own
    assert "Competitive programming" in demands


def test_a_posting_counts_once_after_merging():
    demands = aggregate([
        ("A", [_skill("JavaScript"), _skill("JS", required=False)]),
        ("B", [_skill("javascript")]),
    ])
    assert len(demands) == 1
    assert demands[0].postings == 2 and demands[0].required == 2


def test_plural_folds_into_singular():
    demands = aggregate([("A", [_skill("Microservice")]), ("B", [_skill("Microservices")])])
    assert [(d.name, d.postings) for d in demands] == [("Microservice", 2)]


# ── Reading pages and CSV files ──────────────────────────────────────────────

JOB_LD = """<html><head><title>Ignored | Board</title>
<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [
 {"@type": "Organization", "name": "Board"},
 {"@type": "JobPosting", "title": "Junior Data Engineer",
  "hiringOrganization": {"@type": "Organization", "name": "Example Ltd"},
  "description": "<p>Build ETL pipelines in Python and SQL.</p><ul><li>Airflow</li><li>Docker</li></ul>"}
]}</script></head><body><nav>Menu</nav><p>Page text</p></body></html>"""


def test_job_posting_structured_data_is_preferred():
    posting = read_page(JOB_LD, "https://jobs.example.com/1")
    assert posting.title == "Junior Data Engineer"
    assert posting.employer == "Example Ltd"
    assert "ETL pipelines in Python and SQL" in posting.text and "<p>" not in posting.text
    assert posting.source == "https://jobs.example.com/1"


def test_plain_page_falls_back_to_visible_text():
    html = """<html><head><title>Backend Developer - Example Careers</title><style>p{}</style></head>
    <body><nav>Home About</nav><main><h1>Backend Developer</h1>
    <p>You will design REST APIs, write tests and deploy services with Docker on Linux.</p>
    <script>track()</script></main></body></html>"""
    posting = read_page(html, "https://careers.example.com/backend")
    assert posting.title == "Backend Developer"
    assert "design REST APIs" in posting.text
    assert "track()" not in posting.text and "Home About" not in posting.text


def test_page_without_a_description_is_refused():
    with pytest.raises(ImportFailedError):
        read_page("<html><head><title>Login</title></head><body>Sign in</body></html>", "https://x.example")


def test_csv_columns_are_matched_by_common_names_and_bad_rows_reported():
    data = (
        "Job Title;Company;Job Description;Link\n"
        "QA Engineer;Example Ltd;Write automated tests with Selenium and Python for web apps.;https://e.x/1\n"
        "Too short;Example Ltd;tiny;\n"
    ).encode()
    postings, skipped = read_csv(data)
    assert [(p.title, p.employer, p.source) for p in postings] == [("QA Engineer", "Example Ltd", "https://e.x/1")]
    assert len(skipped) == 1 and "Row 3" in skipped[0]


def test_csv_without_a_description_column_is_refused():
    with pytest.raises(ImportFailedError):
        read_csv(b"name,salary\nA,1\n")


# ── Fetching only public addresses ───────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://localhost/admin",
    "http://127.0.0.1:80/",
    "http://10.0.0.5/jobs",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "file:///etc/passwd",
    "ftp://jobs.example.com/x",
    "http://example.com:8080/",
    "http://user:pw@example.com/",
])
async def test_private_and_odd_addresses_are_refused(url):
    with pytest.raises(ImportFailedError):
        await _check_url(url)


# ── A student's verified skills ──────────────────────────────────────────────

SKILLS = [
    {"skill": "SQL", "category": "technical", "postings": 6, "required": 5, "program_outcomes": ["PO3"],
     "outcomes": [{"course_code": "CSE202", "co_code": "CO2", "statement": "Write SQL queries."}]},
    {"skill": "Git", "category": "technical", "postings": 4, "required": 4, "program_outcomes": [],
     "outcomes": []},
    {"skill": "Testing", "category": "technical", "postings": 3, "required": 1, "program_outcomes": ["PO5"],
     "outcomes": [{"course_code": "CSE301", "co_code": "CO1", "statement": "Test software."}]},
]
RESULTS = [
    {"course_code": "CSE202", "course_title": "Databases",
     "co_results": [{"co_code": "CO2", "co_statement": "Write SQL queries.", "attainment_percentage": 72.0,
                     "threshold": 50, "is_threshold_met": True}]},
    {"course_code": "CSE301", "course_title": "Software Engineering",
     "co_results": [{"co_code": "CO1", "co_statement": "Test software.", "attainment_percentage": 41.0,
                     "threshold": 50, "is_threshold_met": False}]},
]


def test_student_skills_follow_their_own_results():
    when = datetime(2026, 11, 17, tzinfo=UTC)
    response = build_student_skills(SKILLS, RESULTS, posting_count=10, analysed_at=when, top_n=2)
    status = {s.skill: s.status for s in response.skills}
    assert status == {"SQL": "verified", "Git": "not_yet", "Testing": "developing"}
    sql = response.skills[0]
    assert sql.evidence[0].course_title == "Databases" and sql.evidence[0].attainment_pct == 72.0
    assert response.summary.model_dump() == {
        "verified": 1, "developing": 1, "not_yet": 1, "top_n": 2, "top_verified": 1,
    }


def test_no_results_means_nothing_is_verified():
    response = build_student_skills(SKILLS, [], posting_count=10, analysed_at=None)
    assert {s.status for s in response.skills} == {"not_yet"}
