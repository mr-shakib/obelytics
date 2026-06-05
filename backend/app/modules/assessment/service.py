from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.exceptions import (
    AssessmentLockedError,
    AssessmentNotFoundError,
    COWeightConflictError,
    COWeightNotFoundError,
    EnrollmentConflictError,
    EnrollmentNotFoundError,
    InvalidCOError,
    InvalidMarkError,
    MarkConflictError,
    MarkImmutableError,
    MarkNotFoundError,
    NoMarksEnteredError,
    ResultPublicationNotFoundError,
    ResultStateError,
    StudentIdConflictError,
    StudentNotFoundError,
    WeightageNotHundredError,
)
from app.modules.assessment.models import (
    Assessment,
    AssessmentCOWeight,
    ResultPublication,
    Student,
    StudentEnrollment,
    StudentMark,
)
from app.modules.assessment.repository import (
    AssessmentCOWeightRepository,
    AssessmentRepository,
    EnrollmentRepository,
    MarkRepository,
    ResultPublicationRepository,
    StudentRepository,
)
from app.modules.assessment.schemas import (
    AssessmentCOWeightCreate,
    AssessmentCreate,
    AssessmentUpdate,
    EnrollmentCreate,
    MarkCreate,
    MarkUpdate,
    StudentCreate,
    StudentUpdate,
)
from app.modules.obe.models import CourseOutcome


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StudentRepository(session)

    async def list_active(self, org_id: UUID, program_id: UUID | None = None) -> list[Student]:
        return await self._repo.list_active(org_id, program_id)

    async def get(self, student_id: UUID, org_id: UUID) -> Student:
        student = await self._repo.get_by_id(student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        return student

    async def create(self, body: StudentCreate, org_id: UUID) -> Student:
        existing = await self._repo.find_by_student_id_number(body.student_id_number, org_id)
        if existing:
            raise StudentIdConflictError()
        student = Student(
            organization_id=org_id,
            student_id_number=body.student_id_number,
            full_name=body.full_name,
            email=body.email,
            program_id=body.program_id,
            batch_id=body.batch_id,
            status="ACTIVE",
        )
        result = await self._repo.create(student)
        await self._session.commit()
        return result

    async def update(self, student_id: UUID, body: StudentUpdate, org_id: UUID) -> Student:
        student = await self._repo.get_by_id(student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(student, data)
        await self._session.commit()
        return result


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EnrollmentRepository(session)
        self._student_repo = StudentRepository(session)

    async def list_by_offering(self, offering_id: UUID, org_id: UUID) -> list[StudentEnrollment]:
        return await self._repo.list_by_offering(offering_id)

    async def list_by_student(self, student_id: UUID, org_id: UUID) -> list[StudentEnrollment]:
        student = await self._student_repo.get_by_id(student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        return await self._repo.list_by_student(student_id)

    async def enroll(self, body: EnrollmentCreate, org_id: UUID) -> StudentEnrollment:
        student = await self._student_repo.get_by_id(body.student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        existing = await self._repo.find_by_student_offering(body.student_id, body.section_offering_id)
        if existing:
            raise EnrollmentConflictError()
        enrollment = StudentEnrollment(
            organization_id=org_id,
            student_id=body.student_id,
            section_offering_id=body.section_offering_id,
            status="ACTIVE",
        )
        result = await self._repo.create(enrollment)
        await self._session.commit()
        return result


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AssessmentRepository(session)
        self._result_repo = ResultPublicationRepository(session)
        self._co_weight_repo = AssessmentCOWeightRepository(session)

    async def list_by_offering(self, offering_id: UUID, org_id: UUID) -> list[Assessment]:
        return await self._repo.list_by_offering(offering_id)

    async def get(self, assessment_id: UUID, org_id: UUID) -> Assessment:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        return assessment

    async def create(self, body: AssessmentCreate, org_id: UUID) -> Assessment:
        assessment = Assessment(
            organization_id=org_id,
            section_offering_id=body.section_offering_id,
            assessment_type_id=body.assessment_type_id,
            name=body.name,
            total_marks=body.total_marks,
            weightage_percent=body.weightage_percent,
            status="CONFIGURED",
        )
        result = await self._repo.create(assessment)

        # Auto-create ResultPublication if first assessment for this offering
        existing_pub = await self._result_repo.get_by_offering(body.section_offering_id)
        if existing_pub is None:
            pub = ResultPublication(
                organization_id=org_id,
                section_offering_id=body.section_offering_id,
                status="DRAFT",
            )
            await self._result_repo.create(pub)

        await self._session.commit()
        return result

    async def update(self, assessment_id: UUID, body: AssessmentUpdate, org_id: UUID) -> Assessment:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        if assessment.status != "CONFIGURED":
            raise AssessmentLockedError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(assessment, data)
        await self._session.commit()
        return result

    async def open_marks(self, assessment_id: UUID, org_id: UUID) -> Assessment:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        if assessment.status != "CONFIGURED":
            raise AssessmentLockedError()

        # Check result publication is not PUBLISHED
        pub = await self._result_repo.get_by_offering(assessment.section_offering_id)
        if pub is not None and pub.status == "PUBLISHED":
            raise MarkImmutableError()

        # Validate sum of weightage = 100
        total_weight = await self._repo.sum_weightage(assessment.section_offering_id)
        if Decimal(str(total_weight)) != Decimal("100"):
            raise WeightageNotHundredError()

        assessment.status = "MARKS_OPEN"
        result = await self._repo.update(assessment, {})
        await self._session.commit()
        return result

    async def add_co_weight(
        self, assessment_id: UUID, co_weight_body: AssessmentCOWeightCreate, org_id: UUID
    ) -> AssessmentCOWeight:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        if assessment.status == "LOCKED":
            raise AssessmentLockedError()

        # Validate CO is PUBLISHED
        co_result = await self._session.execute(
            select(CourseOutcome).where(
                CourseOutcome.id == co_weight_body.course_outcome_id
            )
        )
        co = co_result.scalar_one_or_none()
        if co is None or co.status != "PUBLISHED":
            raise InvalidCOError()

        # Check for duplicate
        existing = await self._co_weight_repo.find_by_assessment_co(
            assessment_id, co_weight_body.course_outcome_id
        )
        if existing:
            raise COWeightConflictError()

        weight = AssessmentCOWeight(
            assessment_id=assessment_id,
            course_outcome_id=co_weight_body.course_outcome_id,
            contribution_percent=co_weight_body.contribution_percent,
        )
        result = await self._co_weight_repo.create(weight)
        await self._session.commit()
        return result

    async def remove_co_weight(
        self, assessment_id: UUID, co_weight_id: UUID, org_id: UUID
    ) -> None:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        if assessment.status == "LOCKED":
            raise AssessmentLockedError()

        weight = await self._co_weight_repo.get_by_id(co_weight_id)
        if weight is None or weight.assessment_id != assessment_id:
            raise COWeightNotFoundError()

        await self._co_weight_repo.delete(weight)
        await self._session.commit()

    async def list_co_weights(self, assessment_id: UUID, org_id: UUID) -> list[AssessmentCOWeight]:
        assessment = await self._repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        return await self._co_weight_repo.list_by_assessment(assessment_id)


class MarksService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarkRepository(session)
        self._assessment_repo = AssessmentRepository(session)
        self._result_repo = ResultPublicationRepository(session)

    async def list_by_assessment(self, assessment_id: UUID, org_id: UUID) -> list[StudentMark]:
        # Verify assessment exists for this org
        assessment = await self._assessment_repo.get_by_id(assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()
        return await self._repo.list_by_assessment(assessment_id)

    async def get_mark(self, mark_id: UUID, org_id: UUID) -> StudentMark:
        mark = await self._repo.get_by_id(mark_id, org_id)
        if mark is None:
            raise MarkNotFoundError()
        return mark

    async def enter_mark(self, body: MarkCreate, org_id: UUID, user_id: UUID) -> StudentMark:
        # Load assessment
        assessment = await self._assessment_repo.get_by_id(body.assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()

        # Guard: assessment must be MARKS_OPEN
        if assessment.status != "MARKS_OPEN":
            raise AssessmentLockedError()

        # Guard: result publication must not be PUBLISHED
        pub = await self._result_repo.get_by_offering(assessment.section_offering_id)
        if pub is not None and pub.status == "PUBLISHED":
            raise MarkImmutableError()

        # Guard: is_absent XOR marks_obtained
        if body.is_absent and body.marks_obtained is not None:
            raise InvalidMarkError("Cannot set marks_obtained when is_absent is True")
        if not body.is_absent and body.marks_obtained is None:
            raise InvalidMarkError("marks_obtained is required when is_absent is False")

        # Guard: marks_obtained <= total_marks
        if body.marks_obtained is not None:
            if Decimal(str(body.marks_obtained)) > Decimal(str(assessment.total_marks)):
                raise InvalidMarkError(
                    f"marks_obtained ({body.marks_obtained}) cannot exceed total_marks ({assessment.total_marks})"
                )

        # Check duplicate
        existing = await self._repo.find_by_assessment_enrollment(
            body.assessment_id, body.student_enrollment_id
        )
        if existing:
            raise MarkConflictError()

        mark = StudentMark(
            organization_id=org_id,
            assessment_id=body.assessment_id,
            student_enrollment_id=body.student_enrollment_id,
            marks_obtained=body.marks_obtained,
            is_absent=body.is_absent,
            entered_by_user_id=user_id,
        )
        result = await self._repo.create(mark)
        await self._session.commit()
        return result

    async def update_mark(self, mark_id: UUID, body: MarkUpdate, org_id: UUID) -> StudentMark:
        mark = await self._repo.get_by_id(mark_id, org_id)
        if mark is None:
            raise MarkNotFoundError()

        # Load assessment to check status
        assessment = await self._assessment_repo.get_by_id(mark.assessment_id, org_id)
        if assessment is None:
            raise AssessmentNotFoundError()

        # Guard: assessment must be MARKS_OPEN
        if assessment.status != "MARKS_OPEN":
            raise AssessmentLockedError()

        # Guard: result publication must not be PUBLISHED
        pub = await self._result_repo.get_by_offering(assessment.section_offering_id)
        if pub is not None and pub.status == "PUBLISHED":
            raise MarkImmutableError()

        # Determine new values (fall back to existing if not provided)
        new_is_absent = body.is_absent if body.is_absent is not None else mark.is_absent
        new_marks_obtained = body.marks_obtained if body.marks_obtained is not None else mark.marks_obtained

        # If absent flag being set to True, clear marks
        if new_is_absent:
            new_marks_obtained = None
        elif new_marks_obtained is None:
            raise InvalidMarkError("marks_obtained is required when is_absent is False")

        # Guard: marks_obtained <= total_marks
        if new_marks_obtained is not None:
            if Decimal(str(new_marks_obtained)) > Decimal(str(assessment.total_marks)):
                raise InvalidMarkError(
                    f"marks_obtained ({new_marks_obtained}) cannot exceed total_marks ({assessment.total_marks})"
                )

        data = {
            "is_absent": new_is_absent,
            "marks_obtained": new_marks_obtained,
        }
        result = await self._repo.update(mark, data)
        await self._session.commit()
        return result


class ResultPublicationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ResultPublicationRepository(session)
        self._mark_repo = MarkRepository(session)
        self._assessment_repo = AssessmentRepository(session)

    async def get_by_offering(self, offering_id: UUID, org_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        return pub

    async def submit(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        if pub.status != "DRAFT":
            raise ResultStateError(f"Cannot submit: result publication is in status '{pub.status}'")

        # Guard: at least one mark must exist for this offering
        mark_count = await self._mark_repo.count_by_offering(offering_id)
        if mark_count == 0:
            raise NoMarksEnteredError()

        data = {
            "status": "SUBMITTED",
            "submitted_by_user_id": user_id,
            "submitted_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        await self._session.commit()
        return result

    async def approve_ml(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        if pub.status != "SUBMITTED":
            raise ResultStateError(f"Cannot approve (ML): result publication is in status '{pub.status}'")

        data = {
            "status": "ML_APPROVED",
            "ml_approved_by_user_id": user_id,
            "ml_approved_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        await self._session.commit()
        return result

    async def reject_ml(
        self, offering_id: UUID, org_id: UUID, user_id: UUID, comment: str
    ) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        if pub.status != "SUBMITTED":
            raise ResultStateError(f"Cannot reject (ML): result publication is in status '{pub.status}'")

        data = {
            "status": "DRAFT",
            "ml_rejection_comment": comment,
        }
        result = await self._repo.update(pub, data)
        await self._session.commit()
        return result

    async def approve_pc(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        if pub.status != "ML_APPROVED":
            raise ResultStateError(f"Cannot approve (PC): result publication is in status '{pub.status}'")

        data = {
            "status": "PC_APPROVED",
            "pc_approved_by_user_id": user_id,
            "pc_approved_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        await self._session.commit()
        return result

    async def publish(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is None or pub.organization_id != org_id:
            raise ResultPublicationNotFoundError()
        if pub.status != "PC_APPROVED":
            raise ResultStateError(f"Cannot publish: result publication is in status '{pub.status}'")

        data = {
            "status": "PUBLISHED",
            "published_by_user_id": user_id,
            "published_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)

        # Lock all assessments for this offering
        assessments = await self._assessment_repo.list_by_offering(offering_id)
        for a in assessments:
            a.status = "LOCKED"
            await self._assessment_repo.update(a, {})

        await self._session.commit()
        return result
