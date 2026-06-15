from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import presigned_get_url
from app.modules.audit.writer import write_audit_log
from app.modules.notification.writer import write_notification
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
    MarksheetLockedError,
    MarksheetQuestionNotFoundError,
    MarksheetSectionTeacherScopeError,
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
    MarksheetMark,
    MarksheetQuestion,
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
    MarksheetMarkRepository,
    MarksheetQuestionRepository,
    ResultPublicationRepository,
    StudentRepository,
)
from app.modules.assessment.schemas import (
    AssessmentCOWeightCreate,
    AssessmentCreate,
    AssessmentUpdate,
    COAttainmentPreview,
    EnrollmentBulkCreate,
    EnrollmentBulkResponse,
    EnrollmentCreate,
    MarkCreate,
    MarksheetAttainmentResponse,
    MarksheetCellUpdate,
    MarksheetGridResponse,
    MarksheetMarkCell,
    MarksheetQuestionInput,
    MarksheetQuestionResponse,
    MarksheetStudentRow,
    MarkUpdate,
    POAttainmentPreview,
    StudentAttainmentRow,
    StudentBulkImportError,
    StudentBulkImportItem,
    StudentBulkImportResponse,
    StudentCreate,
    StudentUpdate,
)
from app.modules.curriculum.exceptions import SectionOfferingNotFoundError
from app.modules.curriculum.models import AcademicTerm, Batch, Course, Section, SectionOffering
from app.modules.curriculum.repository import (
    FacultyAssignmentRepository,
    ModuleLeaderAssignmentRepository,
    SectionOfferingRepository,
)
from app.modules.curriculum.service import _assert_module_leader
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome, ProgramOutcome
from app.modules.org.repository import OrgRepository

TEMPLATES_DIR = Path(__file__).parent / "templates"


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StudentRepository(session)

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None, search: str | None = None
    ) -> list[Student]:
        return await self._repo.list_active(org_id, program_id, search)

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

    async def bulk_import(
        self, items: list[StudentBulkImportItem], org_id: UUID
    ) -> StudentBulkImportResponse:
        created = 0
        updated = 0
        errors: list[StudentBulkImportError] = []
        seen_sids: set[str] = set()

        for index, item in enumerate(items):
            row = index + 1
            sid = item.student_id_number.strip()
            name = item.full_name.strip()
            if not sid or not name:
                errors.append(
                    StudentBulkImportError(
                        row=row, student_id_number=sid, message="Student ID and name are required"
                    )
                )
                continue
            if sid in seen_sids:
                errors.append(
                    StudentBulkImportError(
                        row=row, student_id_number=sid, message="Duplicate student ID in this import"
                    )
                )
                continue
            seen_sids.add(sid)

            existing = await self._repo.find_by_student_id_number(sid, org_id)
            if existing:
                await self._repo.update(
                    existing,
                    {
                        "full_name": name,
                        "email": item.email,
                        "program_id": item.program_id,
                        "batch_id": item.batch_id,
                    },
                )
                updated += 1
            else:
                await self._repo.create(
                    Student(
                        organization_id=org_id,
                        student_id_number=sid,
                        full_name=name,
                        email=item.email,
                        program_id=item.program_id,
                        batch_id=item.batch_id,
                        status="ACTIVE",
                    )
                )
                created += 1

        await self._session.commit()
        return StudentBulkImportResponse(created=created, updated=updated, errors=errors)


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EnrollmentRepository(session)
        self._student_repo = StudentRepository(session)
        self._offering_repo = SectionOfferingRepository(session)

    async def list_by_offering(self, offering_id: UUID, org_id: UUID) -> list[StudentEnrollment]:
        return await self._repo.list_by_offering(offering_id)

    async def list_roster(
        self, offering_id: UUID, org_id: UUID
    ) -> list[tuple[StudentEnrollment, Student]]:
        return await self._repo.list_with_students_by_offering(offering_id)

    async def list_by_student(self, student_id: UUID, org_id: UUID) -> list[StudentEnrollment]:
        student = await self._student_repo.get_by_id(student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        return await self._repo.list_by_student(student_id)

    async def enroll(
        self, body: EnrollmentCreate, org_id: UUID, acting_user_id: UUID | None = None
    ) -> StudentEnrollment:
        if acting_user_id is not None:
            await _assert_section_teacher(self._session, body.section_offering_id, acting_user_id)
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

    async def bulk_enroll(
        self, body: EnrollmentBulkCreate, org_id: UUID, acting_user_id: UUID | None = None
    ) -> EnrollmentBulkResponse:
        if acting_user_id is not None:
            await _assert_section_teacher(self._session, body.section_offering_id, acting_user_id)
        offering = await self._offering_repo.get_by_id(body.section_offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        enrolled = 0
        already_enrolled = 0
        not_found = 0
        for student_id in body.student_ids:
            student = await self._student_repo.get_by_id(student_id, org_id)
            if student is None:
                not_found += 1
                continue
            existing = await self._repo.find_by_student_offering(student_id, body.section_offering_id)
            if existing:
                already_enrolled += 1
                continue
            await self._repo.create(
                StudentEnrollment(
                    organization_id=org_id,
                    student_id=student_id,
                    section_offering_id=body.section_offering_id,
                    status="ACTIVE",
                )
            )
            enrolled += 1

        await self._session.commit()
        return EnrollmentBulkResponse(
            enrolled=enrolled, already_enrolled=already_enrolled, not_found=not_found
        )

    async def unenroll(
        self, enrollment_id: UUID, org_id: UUID, acting_user_id: UUID | None = None
    ) -> None:
        enrollment = await self._repo.get_by_id(enrollment_id, org_id)
        if enrollment is None:
            raise EnrollmentNotFoundError()
        if acting_user_id is not None:
            await _assert_section_teacher(self._session, enrollment.section_offering_id, acting_user_id)
        await self._repo.delete(enrollment)
        await self._session.commit()


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
        self._marksheet_mark_repo = MarksheetMarkRepository(session)
        self._assessment_repo = AssessmentRepository(session)
        self._offering_repo = SectionOfferingRepository(session)

    async def get_by_offering(self, offering_id: UUID, org_id: UUID) -> ResultPublication:
        pub = await self._repo.get_by_offering(offering_id)
        if pub is not None:
            if pub.organization_id != org_id:
                raise ResultPublicationNotFoundError()
            return pub

        # Lazily create a DRAFT result publication for marksheet-only offerings,
        # which never go through AssessmentService.create.
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise ResultPublicationNotFoundError()
        pub = ResultPublication(
            organization_id=org_id,
            section_offering_id=offering_id,
            status="DRAFT",
        )
        pub = await self._repo.create(pub)
        await self._session.commit()
        return pub

    async def submit(
        self, offering_id: UUID, org_id: UUID, user_id: UUID, acting_user_id: UUID | None = None
    ) -> ResultPublication:
        pub = await self.get_by_offering(offering_id, org_id)
        if acting_user_id is not None:
            await _assert_section_teacher(self._session, offering_id, acting_user_id)
        if pub.status != "DRAFT":
            raise ResultStateError(f"Cannot submit: result publication is in status '{pub.status}'")

        # Guard: at least one mark must exist for this offering
        mark_count = await self._mark_repo.count_by_offering(offering_id)
        marksheet_mark_count = await self._marksheet_mark_repo.count_by_offering(offering_id)
        if mark_count == 0 and marksheet_mark_count == 0:
            raise NoMarksEnteredError()

        data = {
            "status": "SUBMITTED",
            "submitted_by_user_id": user_id,
            "submitted_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        write_audit_log(
            self._session,
            entity_type="result_publication",
            entity_id=pub.id,
            action="RESULT_SUBMITTED",
            org_id=org_id,
            actor_user_id=user_id,
            before_status="DRAFT",
            after_status="SUBMITTED",
        )
        await self._session.commit()
        return result

    async def approve_ml(
        self, offering_id: UUID, org_id: UUID, user_id: UUID, acting_user_id: UUID | None = None
    ) -> ResultPublication:
        pub = await self.get_by_offering(offering_id, org_id)
        if acting_user_id is not None:
            offering = await self._offering_repo.get_by_id(offering_id, org_id)
            if offering is None:
                raise ResultPublicationNotFoundError()
            await _assert_module_leader(
                self._session, offering.batch_id, offering.academic_term_id, offering.course_id, acting_user_id
            )
        if pub.status != "SUBMITTED":
            raise ResultStateError(f"Cannot approve (ML): result publication is in status '{pub.status}'")

        data = {
            "status": "ML_APPROVED",
            "ml_approved_by_user_id": user_id,
            "ml_approved_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        write_audit_log(
            self._session,
            entity_type="result_publication",
            entity_id=pub.id,
            action="RESULT_ML_APPROVED",
            org_id=org_id,
            actor_user_id=user_id,
            before_status="SUBMITTED",
            after_status="ML_APPROVED",
        )
        if pub.submitted_by_user_id:
            write_notification(
                self._session,
                org_id=org_id,
                recipient_user_id=pub.submitted_by_user_id,
                notification_type="RESULT_ML_APPROVED",
                title="Results approved by Module Leader",
                body="Your submitted results have been approved by the Module Leader.",
                entity_type="result_publication",
                entity_id=pub.id,
            )
        await self._session.commit()
        return result

    async def reject_ml(
        self, offering_id: UUID, org_id: UUID, user_id: UUID, comment: str, acting_user_id: UUID | None = None
    ) -> ResultPublication:
        pub = await self.get_by_offering(offering_id, org_id)
        if acting_user_id is not None:
            offering = await self._offering_repo.get_by_id(offering_id, org_id)
            if offering is None:
                raise ResultPublicationNotFoundError()
            await _assert_module_leader(
                self._session, offering.batch_id, offering.academic_term_id, offering.course_id, acting_user_id
            )
        if pub.status != "SUBMITTED":
            raise ResultStateError(f"Cannot reject (ML): result publication is in status '{pub.status}'")

        data = {
            "status": "DRAFT",
            "ml_rejection_comment": comment,
        }
        result = await self._repo.update(pub, data)
        write_audit_log(
            self._session,
            entity_type="result_publication",
            entity_id=pub.id,
            action="RESULT_ML_REJECTED",
            org_id=org_id,
            actor_user_id=user_id,
            before_status="SUBMITTED",
            after_status="DRAFT",
        )
        if pub.submitted_by_user_id:
            write_notification(
                self._session,
                org_id=org_id,
                recipient_user_id=pub.submitted_by_user_id,
                notification_type="RESULT_ML_REJECTED",
                title="Results rejected by Module Leader",
                body=f"Rejection comment: {comment}",
                entity_type="result_publication",
                entity_id=pub.id,
            )
        await self._session.commit()
        return result

    async def approve_pc(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self.get_by_offering(offering_id, org_id)
        if pub.status != "ML_APPROVED":
            raise ResultStateError(f"Cannot approve (PC): result publication is in status '{pub.status}'")

        data = {
            "status": "PC_APPROVED",
            "pc_approved_by_user_id": user_id,
            "pc_approved_at": datetime.now(timezone.utc),
        }
        result = await self._repo.update(pub, data)
        write_audit_log(
            self._session,
            entity_type="result_publication",
            entity_id=pub.id,
            action="RESULT_PC_APPROVED",
            org_id=org_id,
            actor_user_id=user_id,
            before_status="ML_APPROVED",
            after_status="PC_APPROVED",
        )
        await self._session.commit()
        return result

    async def publish(self, offering_id: UUID, org_id: UUID, user_id: UUID) -> ResultPublication:
        pub = await self.get_by_offering(offering_id, org_id)
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

        write_audit_log(
            self._session,
            entity_type="result_publication",
            entity_id=pub.id,
            action="RESULT_PUBLISHED",
            org_id=org_id,
            actor_user_id=user_id,
            before_status="PC_APPROVED",
            after_status="PUBLISHED",
        )
        if pub.submitted_by_user_id:
            write_notification(
                self._session,
                org_id=org_id,
                recipient_user_id=pub.submitted_by_user_id,
                notification_type="RESULT_PUBLISHED",
                title="Results have been officially published",
                body="The results for your section have been published.",
                entity_type="result_publication",
                entity_id=pub.id,
            )

        await self._session.commit()

        # Trigger attainment computation
        from app.modules.attainment.engine import AttainmentEngine
        engine = AttainmentEngine(self._session)
        await engine.compute_for_section_offering(offering_id, org_id)
        await self._session.commit()

    async def bulk_approve_ml(
        self,
        org_id: UUID,
        course_id: UUID,
        user_id: UUID,
        acting_user_id: UUID | None = None,
        batch_id: UUID | None = None,
        academic_term_id: UUID | None = None,
    ) -> int:
        """
        Approve (ML) every currently-SUBMITTED section result for a course,
        sending them on to the Program Coordinator in one action. When
        `acting_user_id` is set (Module Leader), restricted to the batch/term
        combinations for this course that the user currently leads. When
        `batch_id`/`academic_term_id` are set, further restricted to that
        single semester offering of the course.
        """
        query = (
            select(ResultPublication)
            .join(SectionOffering, SectionOffering.id == ResultPublication.section_offering_id)
            .where(
                ResultPublication.organization_id == org_id,
                SectionOffering.course_id == course_id,
                ResultPublication.status == "SUBMITTED",
            )
        )

        if batch_id is not None:
            query = query.where(SectionOffering.batch_id == batch_id)
        if academic_term_id is not None:
            query = query.where(SectionOffering.academic_term_id == academic_term_id)

        if acting_user_id is not None:
            ml_repo = ModuleLeaderAssignmentRepository(self._session)
            assignments = await ml_repo.list_for_user(org_id, acting_user_id)
            tuples = [(a.batch_id, a.academic_term_id) for a in assignments if a.course_id == course_id]
            if not tuples:
                return 0
            query = query.where(
                tuple_(SectionOffering.batch_id, SectionOffering.academic_term_id).in_(tuples)
            )

        result = await self._session.execute(query)
        pubs = result.scalars().all()

        now = datetime.now(timezone.utc)
        for pub in pubs:
            pub.status = "ML_APPROVED"
            pub.ml_approved_by_user_id = user_id
            pub.ml_approved_at = now
            self._session.add(pub)
            write_audit_log(
                self._session,
                entity_type="result_publication",
                entity_id=pub.id,
                action="RESULT_ML_APPROVED",
                org_id=org_id,
                actor_user_id=user_id,
                before_status="SUBMITTED",
                after_status="ML_APPROVED",
            )
            if pub.submitted_by_user_id:
                write_notification(
                    self._session,
                    org_id=org_id,
                    recipient_user_id=pub.submitted_by_user_id,
                    notification_type="RESULT_ML_APPROVED",
                    title="Results approved by Module Leader",
                    body="Your submitted results have been approved by the Module Leader.",
                    entity_type="result_publication",
                    entity_id=pub.id,
                )

        await self._session.commit()
        return len(pubs)

    async def list_submissions(
        self,
        org_id: UUID,
        acting_user_id: UUID | None = None,
        status: str | None = None,
        course_id: UUID | None = None,
    ) -> list[dict]:
        """
        List section result submissions for review. When `acting_user_id` is set
        (Module Leader), restricted to the batch/term/course combinations the
        user currently leads; otherwise (PC/SA) returns all sections in the org.
        """
        query = (
            select(
                SectionOffering.id.label("section_offering_id"),
                SectionOffering.course_id,
                Course.code.label("course_code"),
                Course.title.label("course_title"),
                SectionOffering.batch_id,
                Batch.name.label("batch_name"),
                SectionOffering.academic_term_id,
                AcademicTerm.name.label("term_name"),
                AcademicTerm.year.label("term_year"),
                AcademicTerm.season.label("term_season"),
                SectionOffering.section_id,
                Section.name.label("section_name"),
                ResultPublication.id.label("result_publication_id"),
                ResultPublication.status,
                ResultPublication.submitted_at,
                ResultPublication.ml_rejection_comment,
            )
            .select_from(SectionOffering)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .outerjoin(ResultPublication, ResultPublication.section_offering_id == SectionOffering.id)
            .where(SectionOffering.organization_id == org_id)
        )

        if acting_user_id is not None:
            ml_repo = ModuleLeaderAssignmentRepository(self._session)
            assignments = await ml_repo.list_for_user(org_id, acting_user_id)
            if not assignments:
                return []
            tuples = [(a.batch_id, a.academic_term_id, a.course_id) for a in assignments]
            query = query.where(
                tuple_(SectionOffering.batch_id, SectionOffering.academic_term_id, SectionOffering.course_id).in_(
                    tuples
                )
            )

        if status is not None:
            query = query.where(func.coalesce(ResultPublication.status, "DRAFT") == status)

        if course_id is not None:
            query = query.where(SectionOffering.course_id == course_id)

        query = query.order_by(
            AcademicTerm.year.desc(), AcademicTerm.season, Batch.name, Course.code, Section.name
        )
        result = await self._session.execute(query)
        rows = result.all()

        offering_ids = [row.section_offering_id for row in rows]
        counts: dict[UUID, int] = {}
        if offering_ids:
            count_result = await self._session.execute(
                select(StudentEnrollment.section_offering_id, func.count(StudentEnrollment.id))
                .where(StudentEnrollment.section_offering_id.in_(offering_ids))
                .group_by(StudentEnrollment.section_offering_id)
            )
            counts = dict(count_result.all())

        return [
            {
                **row._mapping,
                "status": row.status or "DRAFT",
                "student_count": counts.get(row.section_offering_id, 0),
            }
            for row in rows
        ]

        return result


async def _assert_section_teacher(session: AsyncSession, section_offering_id: UUID, user_id: UUID) -> None:
    """Restrict an action to the user currently assigned as section teacher for this offering."""
    repo = FacultyAssignmentRepository(session)
    assignment = await repo.find_active(section_offering_id, user_id, "SECTION_TEACHER")
    if assignment is None:
        raise MarksheetSectionTeacherScopeError()


class MarksheetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._question_repo = MarksheetQuestionRepository(session)
        self._mark_repo = MarksheetMarkRepository(session)
        self._enrollment_repo = EnrollmentRepository(session)
        self._offering_repo = SectionOfferingRepository(session)
        self._result_repo = ResultPublicationRepository(session)

    async def _assert_not_locked(self, offering_id: UUID, org_id: UUID) -> None:
        pub = await self._result_repo.get_by_offering(offering_id)
        if pub is not None and pub.organization_id == org_id and pub.status != "DRAFT":
            raise MarksheetLockedError()

    async def list_questions(
        self, offering_id: UUID, exam_type: str, org_id: UUID
    ) -> list[MarksheetQuestion]:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()
        return await self._question_repo.list_by_offering(offering_id, exam_type)

    async def replace_questions(
        self,
        offering_id: UUID,
        exam_type: str,
        org_id: UUID,
        items: list[MarksheetQuestionInput],
        acting_user_id: UUID | None,
    ) -> list[MarksheetQuestion]:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()
        if acting_user_id is not None:
            await _assert_section_teacher(self._session, offering_id, acting_user_id)
        await self._assert_not_locked(offering_id, org_id)

        existing = await self._question_repo.list_by_offering(offering_id, exam_type)
        existing_by_id = {q.id: q for q in existing}
        input_ids = {item.id for item in items if item.id is not None}

        for q in existing:
            if q.id not in input_ids:
                await self._question_repo.delete(q)

        result: list[MarksheetQuestion] = []
        for item in items:
            if item.id is not None and item.id in existing_by_id:
                updated = await self._question_repo.update(
                    existing_by_id[item.id],
                    {
                        "label": item.label,
                        "max_marks": item.max_marks,
                        "course_outcome_id": item.course_outcome_id,
                        "order_index": item.order_index,
                    },
                )
                result.append(updated)
            else:
                created = await self._question_repo.create(
                    MarksheetQuestion(
                        organization_id=org_id,
                        section_offering_id=offering_id,
                        exam_type=exam_type,
                        label=item.label,
                        max_marks=item.max_marks,
                        course_outcome_id=item.course_outcome_id,
                        order_index=item.order_index,
                    )
                )
                result.append(created)

        await self._session.commit()
        result.sort(key=lambda q: q.order_index)
        return result

    async def get_grid(self, offering_id: UUID, exam_type: str, org_id: UUID) -> MarksheetGridResponse:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        questions = await self._question_repo.list_by_offering(offering_id, exam_type)
        enrollment_rows = await self._enrollment_repo.list_with_students_by_offering(offering_id)
        marks = await self._mark_repo.list_by_offering(offering_id, exam_type)
        mark_map = {(m.question_id, m.student_enrollment_id): m for m in marks}

        students: list[MarksheetStudentRow] = []
        for enrollment, student in enrollment_rows:
            cells: dict[str, MarksheetMarkCell] = {}
            total = Decimal("0")
            for q in questions:
                mark = mark_map.get((q.id, enrollment.id))
                if mark is None:
                    cells[str(q.id)] = MarksheetMarkCell()
                else:
                    cells[str(q.id)] = MarksheetMarkCell(
                        mark_id=mark.id,
                        marks_obtained=mark.marks_obtained,
                        is_absent=mark.is_absent,
                    )
                    if not mark.is_absent and mark.marks_obtained is not None:
                        total += Decimal(str(mark.marks_obtained))
            students.append(
                MarksheetStudentRow(
                    enrollment_id=enrollment.id,
                    student_id_number=student.student_id_number,
                    full_name=student.full_name,
                    marks=cells,
                    total=total,
                )
            )

        return MarksheetGridResponse(
            section_offering_id=offering_id,
            exam_type=exam_type,
            questions=[MarksheetQuestionResponse.model_validate(q) for q in questions],
            students=students,
        )

    async def upsert_mark(
        self,
        body: MarksheetCellUpdate,
        org_id: UUID,
        user_id: UUID,
        acting_user_id: UUID | None,
    ) -> MarksheetMark:
        question = await self._question_repo.get_by_id(body.question_id)
        if question is None or question.organization_id != org_id:
            raise MarksheetQuestionNotFoundError()

        if acting_user_id is not None:
            await _assert_section_teacher(self._session, question.section_offering_id, acting_user_id)
        await self._assert_not_locked(question.section_offering_id, org_id)

        enrollment = await self._enrollment_repo.get_by_id(body.student_enrollment_id, org_id)
        if enrollment is None or enrollment.section_offering_id != question.section_offering_id:
            raise EnrollmentNotFoundError()

        if body.is_absent and body.marks_obtained is not None:
            raise InvalidMarkError("Cannot set marks_obtained when is_absent is True")
        if not body.is_absent and body.marks_obtained is None:
            raise InvalidMarkError("marks_obtained is required when is_absent is False")
        if body.marks_obtained is not None and Decimal(str(body.marks_obtained)) > Decimal(str(question.max_marks)):
            raise InvalidMarkError(
                f"marks_obtained ({body.marks_obtained}) cannot exceed max_marks ({question.max_marks})"
            )

        existing = await self._mark_repo.find_by_question_enrollment(question.id, enrollment.id)
        data = {
            "marks_obtained": body.marks_obtained,
            "is_absent": body.is_absent,
            "entered_by_user_id": user_id,
        }
        if existing:
            result = await self._mark_repo.update(existing, data)
        else:
            result = await self._mark_repo.create(
                MarksheetMark(
                    organization_id=org_id,
                    question_id=question.id,
                    student_enrollment_id=enrollment.id,
                    **data,
                )
            )

        await self._session.commit()
        return result

    async def _load_thresholds(self, org_id: UUID, curriculum_id: UUID) -> tuple[Decimal, Decimal]:
        from app.modules.attainment.repository import AttainmentConfigRepository
        from app.modules.curriculum.models import Curriculum

        config_repo = AttainmentConfigRepository(self._session)

        curr_result = await self._session.execute(
            select(Curriculum).where(Curriculum.id == curriculum_id)
        )
        curriculum = curr_result.scalar_one_or_none()

        if curriculum is not None:
            config = await config_repo.get_for_program(org_id, curriculum.program_id)
            if config is not None:
                return Decimal(str(config.threshold_co_score_pct)), Decimal(str(config.threshold_student_pct))

        config = await config_repo.get_for_org(org_id)
        if config is not None:
            return Decimal(str(config.threshold_co_score_pct)), Decimal(str(config.threshold_student_pct))

        return Decimal("50.00"), Decimal("50.00")

    async def get_attainment(self, offering_id: UUID, org_id: UUID) -> MarksheetAttainmentResponse:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        threshold_co_score_pct, threshold_student_pct = await self._load_thresholds(
            org_id, offering.curriculum_id
        )

        questions = await self._question_repo.list_by_offering(offering_id)
        co_questions = [q for q in questions if q.course_outcome_id is not None]

        enrollment_rows = await self._enrollment_repo.list_with_students_by_offering(offering_id)
        marks = await self._mark_repo.list_by_offering(offering_id)
        mark_map = {(m.question_id, m.student_enrollment_id): m for m in marks}

        co_max_marks: dict[UUID, Decimal] = defaultdict(Decimal)
        for q in co_questions:
            co_max_marks[q.course_outcome_id] += Decimal(str(q.max_marks))
        all_co_ids = set(co_max_marks.keys())

        student_co_pct: dict[UUID, dict[UUID, Decimal]] = {}
        student_co_obtained: dict[UUID, dict[UUID, Decimal]] = {}
        for enrollment, _ in enrollment_rows:
            co_obtained: dict[UUID, Decimal] = defaultdict(Decimal)
            for q in co_questions:
                mark = mark_map.get((q.id, enrollment.id))
                if mark is not None and not mark.is_absent and mark.marks_obtained is not None:
                    co_obtained[q.course_outcome_id] += Decimal(str(mark.marks_obtained))
            student_co_obtained[enrollment.id] = co_obtained
            student_co_pct[enrollment.id] = {
                co_id: (co_obtained[co_id] / co_max_marks[co_id] * Decimal("100"))
                if co_max_marks[co_id] > 0 else Decimal("0")
                for co_id in all_co_ids
            }

        total_students = len(enrollment_rows)

        co_map: dict[UUID, CourseOutcome] = {}
        if all_co_ids:
            co_result = await self._session.execute(
                select(CourseOutcome).where(CourseOutcome.id.in_(all_co_ids))
            )
            co_map = {co.id: co for co in co_result.scalars().all()}

        co_avg_attainment: dict[UUID, Decimal] = {}
        co_previews: list[COAttainmentPreview] = []
        for co_id in all_co_ids:
            scores = [student_co_pct[e.id][co_id] for e, _ in enrollment_rows]
            avg = sum(scores) / total_students if total_students > 0 else Decimal("0")
            above = sum(1 for s in scores if s >= threshold_co_score_pct)
            is_attained = (
                (Decimal(str(above)) / Decimal(str(total_students)) * Decimal("100")) >= threshold_student_pct
                if total_students > 0 else False
            )
            co_avg_attainment[co_id] = avg
            co = co_map.get(co_id)
            co_previews.append(
                COAttainmentPreview(
                    course_outcome_id=co_id,
                    co_code=co.code if co else "?",
                    max_marks=co_max_marks[co_id],
                    average_attainment_pct=round(avg, 2),
                    students_above_threshold=above,
                    total_students=total_students,
                    is_attained=is_attained,
                )
            )

        po_entries_by_po: dict[UUID, list[COPOMappingEntry]] = defaultdict(list)
        po_map: dict[UUID, ProgramOutcome] = {}
        if all_co_ids:
            mapping_set_result = await self._session.execute(
                select(COPOMappingSet).where(
                    and_(
                        COPOMappingSet.curriculum_id == offering.curriculum_id,
                        COPOMappingSet.course_id == offering.course_id,
                    )
                )
            )
            mapping_set = mapping_set_result.scalar_one_or_none()
            if mapping_set is not None:
                entries_result = await self._session.execute(
                    select(COPOMappingEntry).where(
                        and_(
                            COPOMappingEntry.mapping_set_id == mapping_set.id,
                            COPOMappingEntry.course_outcome_id.in_(all_co_ids),
                        )
                    )
                )
                for entry in entries_result.scalars().all():
                    po_entries_by_po[entry.program_outcome_id].append(entry)

                if po_entries_by_po:
                    po_result = await self._session.execute(
                        select(ProgramOutcome).where(ProgramOutcome.id.in_(po_entries_by_po.keys()))
                    )
                    po_map = {po.id: po for po in po_result.scalars().all()}

        po_contributing_cos: dict[UUID, set[UUID]] = {}
        po_total_max: dict[UUID, Decimal] = {}
        for po_id, entries in po_entries_by_po.items():
            co_ids = {e.course_outcome_id for e in entries if e.course_outcome_id in all_co_ids}
            po_contributing_cos[po_id] = co_ids
            po_total_max[po_id] = sum((co_max_marks[co_id] for co_id in co_ids), Decimal("0"))

        po_attainment_by_po: dict[UUID, Decimal] = {}
        po_contributing_count: dict[UUID, int] = {}
        for po_id, entries in po_entries_by_po.items():
            weighted_sum = Decimal("0")
            weight_sum = Decimal("0")
            contributing = 0
            for entry in entries:
                if entry.course_outcome_id in co_avg_attainment:
                    w = Decimal(str(entry.weight))
                    weighted_sum += co_avg_attainment[entry.course_outcome_id] * w
                    weight_sum += w
                    contributing += 1
            po_attainment_by_po[po_id] = weighted_sum / weight_sum if weight_sum > 0 else Decimal("0")
            po_contributing_count[po_id] = contributing

        po_threshold_pass_count: dict[UUID, int] = defaultdict(int)

        students: list[StudentAttainmentRow] = []
        for enrollment, student in enrollment_rows:
            co_results: dict[str, bool] = {}
            co_marks: dict[str, Decimal] = {}
            co_pct: dict[str, Decimal] = {}
            for co_id in all_co_ids:
                co = co_map.get(co_id)
                label = co.code if co else str(co_id)
                pct = student_co_pct[enrollment.id][co_id]
                co_results[label] = pct >= threshold_co_score_pct
                co_marks[label] = round(student_co_obtained[enrollment.id][co_id], 2)
                co_pct[label] = round(pct, 2)

            po_results: dict[str, bool] = {}
            po_marks: dict[str, Decimal] = {}
            po_pct: dict[str, Decimal] = {}
            for po_id, entries in po_entries_by_po.items():
                weighted_sum = Decimal("0")
                weight_sum = Decimal("0")
                for entry in entries:
                    if entry.course_outcome_id in all_co_ids:
                        w = Decimal(str(entry.weight))
                        weighted_sum += student_co_pct[enrollment.id][entry.course_outcome_id] * w
                        weight_sum += w
                student_po_pct = weighted_sum / weight_sum if weight_sum > 0 else Decimal("0")
                po = po_map.get(po_id)
                label = po.code if po else str(po_id)
                po_results[label] = student_po_pct >= threshold_co_score_pct
                if po_results[label]:
                    po_threshold_pass_count[po_id] += 1
                po_marks[label] = round(
                    sum((student_co_obtained[enrollment.id][co_id] for co_id in po_contributing_cos[po_id]), Decimal("0")),
                    2,
                )
                po_pct[label] = round(student_po_pct, 2)

            students.append(
                StudentAttainmentRow(
                    enrollment_id=enrollment.id,
                    student_id_number=student.student_id_number,
                    full_name=student.full_name,
                    co_results=co_results,
                    po_results=po_results,
                    co_marks=co_marks,
                    co_pct=co_pct,
                    po_marks=po_marks,
                    po_pct=po_pct,
                )
            )

        po_previews: list[POAttainmentPreview] = []
        for po_id in po_entries_by_po:
            po = po_map.get(po_id)
            po_previews.append(
                POAttainmentPreview(
                    program_outcome_id=po_id,
                    po_code=po.code if po else "?",
                    max_marks=po_total_max[po_id],
                    attainment_pct=round(po_attainment_by_po[po_id], 2),
                    contributing_co_count=po_contributing_count[po_id],
                    students_above_threshold=po_threshold_pass_count[po_id],
                    total_students=total_students,
                    is_attained=po_attainment_by_po[po_id] >= threshold_co_score_pct,
                )
            )

        return MarksheetAttainmentResponse(
            threshold_co_score_pct=threshold_co_score_pct,
            threshold_student_pct=threshold_student_pct,
            cos=co_previews,
            pos=po_previews,
            students=students,
        )

    async def build_report_context(self, offering_id: UUID, org_id: UUID) -> dict:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        info_result = await self._session.execute(
            select(
                Course.code.label("course_code"),
                Course.title.label("course_title"),
                Batch.name.label("batch_name"),
                AcademicTerm.name.label("term_name"),
                AcademicTerm.year.label("term_year"),
                AcademicTerm.season.label("term_season"),
                Section.name.label("section_name"),
            )
            .select_from(SectionOffering)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .where(SectionOffering.id == offering_id)
        )
        info = info_result.one()

        enrollment_rows = await self._enrollment_repo.list_with_students_by_offering(offering_id)
        roster = [
            {"student_id_number": student.student_id_number, "full_name": student.full_name}
            for _, student in enrollment_rows
        ]

        mid_grid = await self.get_grid(offering_id, "MID", org_id)
        final_grid = await self.get_grid(offering_id, "FINAL", org_id)
        attainment = await self.get_attainment(offering_id, org_id)

        org_repo = OrgRepository(self._session)
        org = await org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        return {
            "section": {
                "course_code": info.course_code,
                "course_title": info.course_title,
                "batch_name": info.batch_name,
                "term_name": info.term_name,
                "term_year": info.term_year,
                "term_season": info.term_season,
                "section_name": info.section_name,
            },
            "roster": roster,
            "mid_grid": mid_grid,
            "final_grid": final_grid,
            "attainment": attainment,
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
        }

    async def build_course_report_context(
        self, course_id: UUID, batch_id: UUID, academic_term_id: UUID, org_id: UUID
    ) -> dict:
        result = await self._session.execute(
            select(
                SectionOffering.id.label("section_offering_id"),
                Course.code.label("course_code"),
                Course.title.label("course_title"),
                Batch.name.label("batch_name"),
                AcademicTerm.name.label("term_name"),
                AcademicTerm.year.label("term_year"),
                AcademicTerm.season.label("term_season"),
                Section.name.label("section_name"),
            )
            .select_from(SectionOffering)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .where(
                SectionOffering.organization_id == org_id,
                SectionOffering.course_id == course_id,
                SectionOffering.batch_id == batch_id,
                SectionOffering.academic_term_id == academic_term_id,
            )
            .order_by(Section.name)
        )
        rows = result.all()
        if not rows:
            raise SectionOfferingNotFoundError()

        sections = []
        for row in rows:
            enrollment_rows = await self._enrollment_repo.list_with_students_by_offering(row.section_offering_id)
            roster = [
                {"student_id_number": student.student_id_number, "full_name": student.full_name}
                for _, student in enrollment_rows
            ]
            sections.append({
                "section_name": row.section_name,
                "roster": roster,
                "mid_grid": await self.get_grid(row.section_offering_id, "MID", org_id),
                "final_grid": await self.get_grid(row.section_offering_id, "FINAL", org_id),
                "attainment": await self.get_attainment(row.section_offering_id, org_id),
            })

        first = rows[0]
        org_repo = OrgRepository(self._session)
        org = await org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        return {
            "course": {
                "course_code": first.course_code,
                "course_title": first.course_title,
                "batch_name": first.batch_name,
                "term_name": first.term_name,
                "term_year": first.term_year,
                "term_season": first.term_season,
            },
            "sections": sections,
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
        }


def render_marksheet_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("marksheet_report.html").render(**context)
    return HTML(string=html).write_pdf()


def render_marksheet_course_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("marksheet_course_report.html").render(**context)
    return HTML(string=html).write_pdf()
