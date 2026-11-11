"""Evidence-weighted attainment: the official CO figure next to the same figure
computed without questions the audit contradicts."""
import uuid
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import MarksheetMark, Student, StudentEnrollment
from app.modules.assessment.service import MarksheetService
from app.modules.integrity.evidence import (
    CONTRADICTED,
    SUPPORTED,
    UNVERIFIED,
    QuestionInput,
    co_attainment,
    evidence_status,
)
from app.modules.integrity.models import QuestionAudit
from tests.conftest import TEST_ORG_ID
from tests.integration.test_integrity_audit import BASE, _scenario

# ── Pure calculation ──────────────────────────────────────────────────────────


def test_evidence_status_follows_the_audit_and_the_teacher():
    assert evidence_status(None, None) == UNVERIFIED
    assert evidence_status("ABSTAINED", "PENDING") == UNVERIFIED
    assert evidence_status("ALIGNED", "PENDING") == SUPPORTED
    assert evidence_status("PARTIAL", "ACCEPTED") == SUPPORTED  # right CO, other Bloom level
    assert evidence_status("MISALIGNED", "PENDING") == CONTRADICTED
    assert evidence_status("MISALIGNED", "ACCEPTED") == CONTRADICTED
    assert evidence_status("MISALIGNED", "OVERRIDDEN") == SUPPORTED  # the teacher decides


def test_contradicted_questions_are_left_out_of_the_evidence_figure():
    co = uuid.uuid4()
    q1, q2 = uuid.uuid4(), uuid.uuid4()
    students = [uuid.uuid4() for _ in range(4)]
    # Students do well on q2 (which really tests another CO) and poorly on q1.
    marks = {}
    for s in students:
        marks[(q1, s)] = Decimal("1")
        marks[(q2, s)] = Decimal("5")
    questions = [QuestionInput(q1, co, Decimal("5"), SUPPORTED), QuestionInput(q2, co, Decimal("5"), CONTRADICTED)]

    official = co_attainment(questions, marks, students, Decimal("50"))[co]
    backed = co_attainment(questions, marks, students, Decimal("50"), evidence_only=True)[co]

    assert (official.average_pct, official.is_attained) == (Decimal("60.00"), True)
    assert (backed.average_pct, backed.is_attained) == (Decimal("20.00"), False)
    assert backed.max_marks == Decimal("5")


def test_a_co_with_only_contradicted_questions_has_no_evidence():
    co, q = uuid.uuid4(), uuid.uuid4()
    result = co_attainment([QuestionInput(q, co, Decimal("5"), CONTRADICTED)], {}, [uuid.uuid4()],
                           Decimal("50"), evidence_only=True)
    assert co not in result


# ── Endpoint ──────────────────────────────────────────────────────────────────

async def _students_with_marks(db: AsyncSession, s: dict, marks_by_label: dict[str, list[str | None]]) -> None:
    """marks_by_label: question label → one mark per student (None = absent)."""
    count = len(next(iter(marks_by_label.values())))
    enrollments = []
    for i in range(count):
        student = Student(organization_id=TEST_ORG_ID, student_id_number=f"EV-{uuid.uuid4().hex[:8]}",
                          full_name=f"Evidence Student {i}", email=f"ev{i}@student.example.edu",
                          program_id=s["program_id"], batch_id=s["batch_id"])
        db.add(student)
        await db.flush()
        enrollment = StudentEnrollment(organization_id=TEST_ORG_ID, student_id=student.id,
                                       section_offering_id=s["offering_id"])
        db.add(enrollment)
        await db.flush()
        enrollments.append(enrollment.id)
    for label, values in marks_by_label.items():
        for enrollment_id, value in zip(enrollments, values):
            db.add(MarksheetMark(
                organization_id=TEST_ORG_ID, question_id=s["question_ids"][label],
                student_enrollment_id=enrollment_id,
                marks_obtained=None if value is None else Decimal(value), is_absent=value is None,
            ))
    await db.commit()


def _audit(s, label, alignment, ai_co, review="PENDING", reason=None):
    return QuestionAudit(
        organization_id=TEST_ORG_ID, question_id=s["question_ids"][label], alignment=alignment,
        ai_course_outcome_id=s["cos"].get(ai_co), confidence=Decimal("0.9"), model="fake",
        prompt_version="audit-v3", review_status=review, override_reason=reason,
    )


async def test_evidence_view_matches_official_attainment_until_the_audit_disagrees(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3"), ("Q2", "CO1", "C1"), ("Q3", "CO2", "C3")])
    await _students_with_marks(db_session, s, {
        "Q1": ["1", "2", "1", None],
        "Q2": ["5", "5", "4", "5"],
        "Q3": ["4", "3", "1", "2"],
    })
    url = f"{BASE}/sections/{s['offering_id']}/evidence"

    body = (await client.get(url, headers=auth_headers)).json()
    official = await MarksheetService(db_session).get_attainment(s["offering_id"], TEST_ORG_ID)
    by_code = {o["course_outcome"]["code"]: o for o in body["outcomes"]}
    for co in official.cos:
        reported = by_code[co.co_code]["reported"]
        assert Decimal(str(reported["average_pct"])) == co.average_attainment_pct
        assert (reported["students_above"], reported["is_attained"]) == (co.students_above_threshold, co.is_attained)
        assert by_code[co.co_code]["evidence"] == reported  # nothing audited yet
        assert by_code[co.co_code]["verdict"] == "UNCHANGED"
    assert body["total_students"] == 4

    # The audit says Q2 ("identify…") tests CO2, not CO1; Q3 is fine.
    audit = _audit(s, "Q2", "MISALIGNED", "CO2")
    db_session.add_all([audit, _audit(s, "Q3", "ALIGNED", "CO2")])
    await db_session.commit()
    body = (await client.get(url, headers=auth_headers)).json()
    co1 = next(o for o in body["outcomes"] if o["course_outcome"]["code"] == "CO1")
    assert co1["reported"]["is_attained"] is True
    assert co1["evidence"]["max_marks"] == 5.0  # Q1 only
    assert co1["evidence"]["is_attained"] is False
    assert co1["verdict"] == "NOT_SUPPORTED"
    assert co1["judged_marks_share"] == 0.5
    q2 = next(q for q in co1["questions"] if q["label"] == "Q2")
    assert (q2["status"], q2["ai_course_outcome"]["code"]) == ("CONTRADICTED", "CO2")
    assert body["summary"]["not_supported"] == 1
    assert body["summary"]["contradicted_pending_review"] == 1

    # The teacher disagrees with the AI, with a reason: their mapping stands.
    audit.review_status, audit.override_reason = "OVERRIDDEN", "Students must compare the derivatives."
    await db_session.commit()
    body = (await client.get(url, headers=auth_headers)).json()
    co1 = next(o for o in body["outcomes"] if o["course_outcome"]["code"] == "CO1")
    assert co1["verdict"] == "UNCHANGED"


async def test_a_co_whose_questions_all_test_something_else_has_no_evidence(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3"), ("Q2", "CO2", "C3")])
    await _students_with_marks(db_session, s, {"Q1": ["5", "4"], "Q2": ["5", "5"]})
    db_session.add(_audit(s, "Q2", "MISALIGNED", "CO1", review="ACCEPTED"))
    await db_session.commit()
    body = (await client.get(f"{BASE}/sections/{s['offering_id']}/evidence", headers=auth_headers)).json()
    co2 = next(o for o in body["outcomes"] if o["course_outcome"]["code"] == "CO2")
    assert (co2["evidence"], co2["verdict"]) == (None, "NO_EVIDENCE")
    assert body["summary"]["not_supported"] == 1


async def test_evidence_view_respects_section_access(
    client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    resp = await client.get(f"{BASE}/sections/{s['offering_id']}/evidence", headers=teacher_auth_headers)
    assert resp.status_code == 403
