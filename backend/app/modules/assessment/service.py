import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import anyio
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
    BulkPublishScopeError,
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
    CourseEndReport,
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
from app.modules.curriculum.models import AcademicTerm, Batch, Course, Curriculum, FacultyAssignment, ModuleLeaderAssignment, Section, SectionOffering
from app.modules.curriculum.repository import (
    FacultyAssignmentRepository,
    ModuleLeaderAssignmentRepository,
    SectionOfferingRepository,
)
from app.modules.curriculum.service import _assert_module_leader
from app.modules.iam.models import User
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome, ProgramOutcome
from app.modules.org.models import Department, Program
from app.modules.org.repository import OrgRepository

TEMPLATES_DIR = Path(__file__).parent / "templates"


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StudentRepository(session)

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None, batch_id: UUID | None = None, search: str | None = None
    ) -> list[Student]:
        return await self._repo.list_active(org_id, program_id, batch_id, search)

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

    async def delete(self, student_id: UUID, org_id: UUID) -> None:
        student = await self._repo.get_by_id(student_id, org_id)
        if student is None:
            raise StudentNotFoundError()
        await self._repo.delete(student)
        await self._session.commit()

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
        report_result = await self._session.execute(
            select(CourseEndReport).where(CourseEndReport.section_offering_id == offering_id)
        )
        report = report_result.scalar_one_or_none()
        if report is not None and report.organization_id == org_id and report.status == "SUBMITTED":
            report.status = "DRAFT"
            report.submitted_at = None
            self._session.add(report)
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

        return result

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

    async def bulk_approve_pc(
        self,
        org_id: UUID,
        user_id: UUID,
        course_id: UUID | None = None,
        batch_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        program_ids: list[UUID] | None = None,
    ) -> int:
        """Program Coordinator approves every ML_APPROVED section result for a course
        (or, when `course_id` is omitted, every course in a given batch+term) and
        publishes them in one action: locks assessments, records the approval and
        publication, notifies the submitter, and triggers CO/PO attainment computation
        so enrolled students can see their results.

        When `course_id` is omitted, both `batch_id` and `academic_term_id` are
        required — this is the "publish this whole semester" action and must not
        silently fan out to every course in the org."""
        if course_id is None and (batch_id is None or academic_term_id is None):
            raise BulkPublishScopeError()

        query = (
            select(ResultPublication)
            .join(SectionOffering, SectionOffering.id == ResultPublication.section_offering_id)
            .where(
                ResultPublication.organization_id == org_id,
                ResultPublication.status == "ML_APPROVED",
            )
        )
        if course_id is not None:
            query = query.where(SectionOffering.course_id == course_id)
        if batch_id is not None:
            query = query.where(SectionOffering.batch_id == batch_id)
        if academic_term_id is not None:
            query = query.where(SectionOffering.academic_term_id == academic_term_id)
        if program_ids is not None:
            query = query.join(Curriculum, Curriculum.id == SectionOffering.curriculum_id).where(
                Curriculum.program_id.in_(program_ids)
            )

        pubs = (await self._session.execute(query)).scalars().all()

        now = datetime.now(timezone.utc)
        offering_ids: list[UUID] = []
        for pub in pubs:
            pub.status = "PUBLISHED"
            pub.pc_approved_by_user_id = user_id
            pub.pc_approved_at = now
            pub.published_by_user_id = user_id
            pub.published_at = now
            self._session.add(pub)
            offering_ids.append(pub.section_offering_id)

            # Lock all assessments for this offering
            assessments = await self._assessment_repo.list_by_offering(pub.section_offering_id)
            for a in assessments:
                a.status = "LOCKED"
                await self._assessment_repo.update(a, {})

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
                    body="The results for your section have been approved by the Program Coordinator and published.",
                    entity_type="result_publication",
                    entity_id=pub.id,
                )

        await self._session.commit()

        # Trigger attainment computation for each published offering
        from app.modules.attainment.engine import AttainmentEngine
        engine = AttainmentEngine(self._session)
        for offering_id in offering_ids:
            await engine.compute_for_section_offering(offering_id, org_id)
        await self._session.commit()

        return len(pubs)

    async def list_submissions(
        self,
        org_id: UUID,
        acting_user_id: UUID | None = None,
        status: str | None = None,
        course_id: UUID | None = None,
        batch_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        program_ids: list[UUID] | None = None,
    ) -> list[dict]:
        """
        List section result submissions for review. When `acting_user_id` is set
        (Module Leader), restricted to the batch/term/course combinations the
        user currently leads. Otherwise (PC/SA), returns all sections in the org,
        further restricted to `program_ids` when given (a Program Coordinator
        scoped to specific programs rather than the whole org).
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

        if batch_id is not None:
            query = query.where(SectionOffering.batch_id == batch_id)

        if academic_term_id is not None:
            query = query.where(SectionOffering.academic_term_id == academic_term_id)

        if program_ids is not None:
            query = query.join(Curriculum, Curriculum.id == SectionOffering.curriculum_id).where(
                Curriculum.program_id.in_(program_ids)
            )

        query = query.order_by(
            AcademicTerm.year.desc(), AcademicTerm.season, Batch.name, Course.code, Section.name
        )
        result = await self._session.execute(query)
        rows = result.all()

        offering_ids = [row.section_offering_id for row in rows]
        counts: dict[UUID, int] = {}
        end_report_statuses: dict[UUID, str] = {}
        end_report_drive_links: dict[UUID, str | None] = {}
        if offering_ids:
            count_result = await self._session.execute(
                select(StudentEnrollment.section_offering_id, func.count(StudentEnrollment.id))
                .where(StudentEnrollment.section_offering_id.in_(offering_ids))
                .group_by(StudentEnrollment.section_offering_id)
            )
            counts = dict(count_result.all())

            er_rows = (await self._session.execute(
                select(CourseEndReport.section_offering_id, CourseEndReport.status, CourseEndReport.course_drive_link)
                .where(CourseEndReport.section_offering_id.in_(offering_ids))
            )).all()
            for er_row in er_rows:
                end_report_statuses[er_row[0]] = er_row[1]
                end_report_drive_links[er_row[0]] = er_row[2]

        return [
            {
                **row._mapping,
                "status": row.status or "DRAFT",
                "end_report_status": end_report_statuses.get(row.section_offering_id),
                "course_drive_link": end_report_drive_links.get(row.section_offering_id),
                "student_count": counts.get(row.section_offering_id, 0),
            }
            for row in rows
        ]


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

    async def _load_thresholds(self, org_id: UUID, curriculum_id: UUID) -> Decimal:
        """Attainment threshold is set per-curriculum by the Program Coordinator.
        Falls back to 50% only when the curriculum can't be found."""
        from app.modules.curriculum.models import Curriculum

        curriculum = (await self._session.execute(
            select(Curriculum).where(Curriculum.id == curriculum_id)
        )).scalar_one_or_none()

        if curriculum is not None:
            return Decimal(str(curriculum.threshold_co_score_pct))

        return Decimal("50.00")

    async def get_grade_distribution(self, offering_id: UUID, org_id: UUID) -> dict[str, int]:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        questions = await self._question_repo.list_by_offering(offering_id)
        if not questions:
            return {g: 0 for g in GRADES}

        total_max = sum(Decimal(str(q.max_marks)) for q in questions)
        if total_max <= 0:
            return {g: 0 for g in GRADES}

        enrollment_rows = await self._enrollment_repo.list_with_students_by_offering(offering_id)
        marks = await self._mark_repo.list_by_offering(offering_id)
        mark_map = {(m.question_id, m.student_enrollment_id): m for m in marks}

        grade_counts = {g: 0 for g in GRADES}
        for enrollment, _ in enrollment_rows:
            obtained = Decimal("0")
            for q in questions:
                mark = mark_map.get((q.id, enrollment.id))
                if mark is not None and not mark.is_absent and mark.marks_obtained is not None:
                    obtained += Decimal(str(mark.marks_obtained))
            pct = float(obtained / total_max * Decimal("100"))
            grade = _pct_to_grade(pct)
            grade_counts[grade] += 1

        return grade_counts

    async def get_attainment(self, offering_id: UUID, org_id: UUID) -> MarksheetAttainmentResponse:
        offering = await self._offering_repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()

        threshold_co_score_pct = await self._load_thresholds(
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
                (Decimal(str(above)) / Decimal(str(total_students)) * Decimal("100")) >= threshold_co_score_pct
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
            if mapping_set is None:
                fallback_result = await self._session.execute(
                    select(COPOMappingSet).where(
                        COPOMappingSet.course_id == offering.course_id,
                    ).order_by(COPOMappingSet.created_at.desc()).limit(1)
                )
                mapping_set = fallback_result.scalar_one_or_none()
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
            contributing = sum(
                1 for e in entries if e.course_outcome_id in all_co_ids
            )
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
                contributing_co_ids = po_contributing_cos.get(po_id, set())
                total_obtained = sum(
                    (student_co_obtained[enrollment.id].get(co_id, Decimal("0"))
                     for co_id in contributing_co_ids),
                    Decimal("0"),
                )
                total_max = po_total_max.get(po_id, Decimal("0"))
                student_po_pct = (total_obtained / total_max * Decimal("100")) if total_max > 0 else Decimal("0")
                po = po_map.get(po_id)
                label = po.code if po else str(po_id)
                po_results[label] = student_po_pct >= threshold_co_score_pct
                if po_results[label]:
                    po_threshold_pass_count[po_id] += 1
                po_marks[label] = round(total_obtained, 2)
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

        po_attainment_by_po = {
            po_id: (
                Decimal(str(po_threshold_pass_count[po_id]))
                / Decimal(str(total_students)) * Decimal("100")
                if total_students > 0 else Decimal("0")
            )
            for po_id in po_entries_by_po
        }

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
                    is_attained=po_attainment_by_po[po_id] > Decimal("50"),
                )
            )

        def _natural(s: str) -> list:
            return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]

        co_previews.sort(key=lambda c: _natural(c.co_code))
        po_previews.sort(key=lambda p: _natural(p.po_code))

        return MarksheetAttainmentResponse(
            threshold_co_score_pct=threshold_co_score_pct,
            cos=co_previews,
            pos=po_previews,
            students=students,
        )

    async def get_results_for_student(self, student_id: UUID, org_id: UUID) -> list[dict]:
        """Published course results for a single student: per-course overall grade plus
        the student's own CO and PO attainment. Only PUBLISHED section offerings appear."""
        rows = (await self._session.execute(
            select(StudentEnrollment, SectionOffering, Course, AcademicTerm)
            .join(SectionOffering, SectionOffering.id == StudentEnrollment.section_offering_id)
            .join(ResultPublication, ResultPublication.section_offering_id == SectionOffering.id)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.organization_id == org_id,
                ResultPublication.status == "PUBLISHED",
            )
            .order_by(AcademicTerm.year.desc(), Course.code)
        )).all()

        if not rows:
            return []

        offering_ids = [offering.id for _, offering, _, _ in rows]
        course_ids = list({offering.course_id for _, offering, _, _ in rows})
        curriculum_ids = list({offering.curriculum_id for _, offering, _, _ in rows if offering.curriculum_id})

        # Batch-fetch all data needed for attainment computation
        all_co_result = await self._session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id.in_(course_ids))
        )
        cos_by_course: dict[UUID, list[CourseOutcome]] = defaultdict(list)
        for co in all_co_result.scalars().all():
            cos_by_course[co.course_id].append(co)

        all_questions = (await self._session.execute(
            select(MarksheetQuestion).where(MarksheetQuestion.section_offering_id.in_(offering_ids))
        )).scalars().all()
        questions_by_offering: dict[UUID, list[MarksheetQuestion]] = defaultdict(list)
        for q in all_questions:
            questions_by_offering[q.section_offering_id].append(q)

        all_marks = (await self._session.execute(
            select(MarksheetMark).where(MarksheetMark.organization_id == org_id)
        )).scalars().all()
        mark_map_by_offering: dict[UUID, dict[tuple[UUID, UUID], MarksheetMark]] = {}
        for m in all_marks:
            # Filter to relevant offerings by checking question_id
            for off_id, qs in questions_by_offering.items():
                if any(q.id == m.question_id for q in qs):
                    if off_id not in mark_map_by_offering:
                        mark_map_by_offering[off_id] = {}
                    mark_map_by_offering[off_id][(m.question_id, m.student_enrollment_id)] = m

        # Batch-fetch mapping sets and entries
        mapping_sets_result = await self._session.execute(
            select(COPOMappingSet).where(
                and_(
                    COPOMappingSet.curriculum_id.in_(curriculum_ids),
                    COPOMappingSet.course_id.in_(course_ids),
                )
            )
        )
        mapping_sets = mapping_sets_result.scalars().all()
        best_mapping: dict[tuple[UUID, UUID], COPOMappingSet] = {}
        for ms in mapping_sets:
            key = (ms.curriculum_id, ms.course_id)
            if key not in best_mapping or ms.created_at > best_mapping[key].created_at:
                best_mapping[key] = ms

        mapping_set_ids = [ms.id for ms in best_mapping.values()]
        all_entries: list[COPOMappingEntry] = []
        if mapping_set_ids:
            entries_result = await self._session.execute(
                select(COPOMappingEntry).where(COPOMappingEntry.mapping_set_id.in_(mapping_set_ids))
            )
            all_entries = list(entries_result.scalars().all())
        entries_by_ms: dict[UUID, list[COPOMappingEntry]] = defaultdict(list)
        for e in all_entries:
            entries_by_ms[e.mapping_set_id].append(e)

        # Batch-fetch POs
        po_ids = {e.program_outcome_id for e in all_entries}
        po_map: dict[UUID, ProgramOutcome] = {}
        if po_ids:
            po_result = await self._session.execute(
                select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids))
            )
            po_map = {po.id: po for po in po_result.scalars().all()}

        # Batch-fetch program_ids for curricula
        program_id_by_curriculum: dict[UUID, UUID] = {}
        if curriculum_ids:
            cur_result = await self._session.execute(
                select(Curriculum.id, Curriculum.program_id).where(Curriculum.id.in_(curriculum_ids))
            )
            for cid, pid in cur_result.all():
                if pid:
                    program_id_by_curriculum[cid] = pid

        # Batch-fetch thresholds
        threshold_by_curriculum: dict[UUID, Decimal] = {}
        for cur_id in curriculum_ids:
            threshold_by_curriculum[cur_id] = await self._load_thresholds(org_id, cur_id)

        # Fetch the student's enrollments to match against
        student_enrollment_ids = {enrollment.id for enrollment, _, _, _ in rows}

        results: list[dict] = []
        for enrollment, offering, course, term in rows:
            threshold = float(threshold_by_curriculum.get(offering.curriculum_id, Decimal("60")))
            cos = cos_by_course.get(offering.course_id, [])
            questions = questions_by_offering.get(offering.id, [])
            co_questions = [q for q in questions if q.course_outcome_id is not None]
            mark_map = mark_map_by_offering.get(offering.id, {})

            # Compute CO attainment for this student
            co_max_marks: dict[UUID, Decimal] = defaultdict(Decimal)
            for q in co_questions:
                co_max_marks[q.course_outcome_id] += Decimal(str(q.max_marks))

            co_obtained: dict[UUID, Decimal] = defaultdict(Decimal)
            for q in co_questions:
                mark = mark_map.get((q.id, enrollment.id))
                if mark is not None and not mark.is_absent and mark.marks_obtained is not None:
                    co_obtained[q.course_outcome_id] += Decimal(str(mark.marks_obtained))

            co_code_map = {co.id: co.code for co in cos}
            co_stmt_map = {co.id: co.statement for co in cos}

            co_results = []
            for co_id, max_marks in co_max_marks.items():
                code = co_code_map.get(co_id, str(co_id))
                pct = float(co_obtained[co_id] / max_marks * Decimal("100")) if max_marks > 0 else 0.0
                co_results.append({
                    "co_code": code,
                    "co_statement": co_stmt_map.get(co_id, ""),
                    "attainment_percentage": round(pct, 2),
                    "threshold": threshold,
                    "is_threshold_met": pct >= threshold,
                })

            # Compute PO attainment for this student
            ms_key = (offering.curriculum_id, offering.course_id)
            mapping_set = best_mapping.get(ms_key)
            entries = entries_by_ms.get(mapping_set.id, []) if mapping_set else []

            po_entries: dict[UUID, list[COPOMappingEntry]] = defaultdict(list)
            for entry in entries:
                if entry.course_outcome_id in {co.id for co in cos}:
                    po_entries[entry.program_outcome_id].append(entry)

            po_results = []
            for po_id, po_ents in po_entries.items():
                contributing_co_ids = {e.course_outcome_id for e in po_ents if e.course_outcome_id in co_max_marks}
                total_obtained = sum(
                    (co_obtained.get(co_id, Decimal("0")) for co_id in contributing_co_ids),
                    Decimal("0"),
                )
                total_max = sum(
                    (co_max_marks[co_id] for co_id in contributing_co_ids),
                    Decimal("0"),
                )
                student_po_pct = float(total_obtained / total_max * Decimal("100")) if total_max > 0 else 0.0
                po = po_map.get(po_id)
                po_results.append({
                    "po_code": po.code if po else str(po_id),
                    "po_statement": po.statement if po else None,
                    "attainment_percentage": round(student_po_pct, 2),
                    "threshold": threshold,
                    "is_threshold_met": student_po_pct >= threshold,
                })

            po_results.sort(key=lambda p: p["po_code"])

            results.append({
                "course_code": course.code,
                "course_title": course.title,
                "term_name": term.name,
                "result_status": "PUBLISHED",
                "co_results": co_results,
                "po_results": po_results,
            })

        return results

    async def _get_active_program_outcomes(self, org_id: UUID) -> list[dict]:
        """All active program outcomes for the organization, in definition order.
        Program outcomes here aren't scoped by program_id in practice, so this is
        org-wide — used so result views can show every PO (e.g. all 12) rather than
        only the ones a student's published courses happen to map to so far."""
        pos = (await self._session.execute(
            select(ProgramOutcome)
            .where(
                ProgramOutcome.organization_id == org_id,
                ProgramOutcome.status == "ACTIVE",
                ProgramOutcome.program_id.is_(None),
            )
            .order_by(ProgramOutcome.order_index)
        )).scalars().all()
        return [{"po_code": po.code, "po_statement": po.statement} for po in pos]

    async def get_results_bundle_for_student(self, student_id: UUID, org_id: UUID) -> dict:
        """Published course results for a student plus the full active PO list."""
        results = await self.get_results_for_student(student_id, org_id)
        program_outcomes = await self._get_active_program_outcomes(org_id)
        return {"results": results, "program_outcomes": program_outcomes}

    async def get_public_results_by_uid(self, uid: str) -> dict | None:
        """Public result lookup by student ID number (no authentication). Returns the
        student's name plus their published CO/PO attainment, or None if no matching
        active student exists."""
        student = (await self._session.execute(
            select(Student)
            .where(Student.student_id_number == uid, Student.status != "WITHDRAWN")
            .limit(1)
        )).scalar_one_or_none()
        if student is None:
            return None
        results = await self.get_results_for_student(student.id, student.organization_id)
        program_outcomes = await self._get_active_program_outcomes(student.organization_id)
        return {
            "student_id_number": student.student_id_number,
            "full_name": student.full_name,
            "results": results,
            "program_outcomes": program_outcomes,
        }

    async def _build_student_po_report_context(self, student: Student) -> dict:
        org_id = student.organization_id
        results = await self.get_results_for_student(student.id, org_id)
        program_outcomes = await self._get_active_program_outcomes(org_id)

        org_repo = OrgRepository(self._session)
        org = await org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        program_acronym = ""
        department_name = ""
        department_logo_url = None
        if student.batch_id:
            batch = (await self._session.execute(
                select(Batch).where(Batch.id == student.batch_id)
            )).scalar_one_or_none()
            if batch and batch.curriculum_id:
                curriculum = (await self._session.execute(
                    select(Curriculum).where(Curriculum.id == batch.curriculum_id)
                )).scalar_one_or_none()
                if curriculum and curriculum.program_id:
                    prog = (await self._session.execute(
                        select(Program).where(Program.id == curriculum.program_id)
                    )).scalar_one_or_none()
                    if prog:
                        program_acronym = prog.acronym
                        dept = (await self._session.execute(
                            select(Department).where(Department.id == prog.department_id)
                        )).scalar_one_or_none()
                        if dept:
                            department_name = f"{dept.name} ({dept.short_name})"
                            if dept.logo_file_key:
                                department_logo_url = await presigned_get_url(
                                    settings.MINIO_BUCKET_LOGOS, dept.logo_file_key
                                )

        # Aggregate PO attainment across all published courses, same rule the UI
        # uses: a PO with no contributing course shows as "no data yet", not as
        # "not attained" — those are different things for a formal transcript.
        contributions: dict[str, list[dict]] = defaultdict(list)
        threshold_by_code: dict[str, float] = {}
        po_statement_by_code: dict[str, str | None] = {}
        for course in results:
            for po in course["po_results"]:
                code = po["po_code"]
                contributions[code].append({"course_code": course["course_code"], "pct": po["attainment_percentage"]})
                threshold_by_code[code] = po["threshold"]
                po_statement_by_code[code] = po.get("po_statement")

        fallback_threshold = next(iter(threshold_by_code.values()), 50.0)

        po_summary = []
        for po in program_outcomes:
            code = po["po_code"]
            contribs = contributions.get(code, [])
            threshold = threshold_by_code.get(code, fallback_threshold)
            avg_pct = sum(c["pct"] for c in contribs) / len(contribs) if contribs else 0.0
            po_summary.append({
                "po_code": code,
                "po_statement": po.get("po_statement") or po_statement_by_code.get(code),
                "avg_pct": round(avg_pct, 1),
                "threshold": threshold,
                "is_attained": bool(contribs) and avg_pct >= threshold,
                "has_data": bool(contribs),
                "contributing_courses": ", ".join(c["course_code"] for c in contribs) if contribs else "—",
            })

        attained_po_count = sum(1 for p in po_summary if p["is_attained"])
        all_cos = [co for course in results for co in course["co_results"]]
        met_co_count = sum(1 for co in all_cos if co["is_threshold_met"])

        return {
            "student": {
                "full_name": student.full_name,
                "student_id_number": student.student_id_number,
            },
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
            "program_acronym": program_acronym,
            "department_name": department_name,
            "department_logo_url": department_logo_url,
            "generated_at": datetime.now(timezone.utc).strftime("%d %B %Y"),
            "courses": results,
            "po_summary": po_summary,
            "attained_po_count": attained_po_count,
            "total_po_count": len(po_summary),
            "met_co_count": met_co_count,
            "total_co_count": len(all_cos),
        }

    async def build_student_po_report_context(self, student_id: UUID, org_id: UUID) -> dict | None:
        student = (await self._session.execute(
            select(Student).where(Student.id == student_id, Student.organization_id == org_id)
        )).scalar_one_or_none()
        if student is None:
            return None
        return await self._build_student_po_report_context(student)

    async def build_student_po_report_context_by_uid(self, uid: str) -> dict | None:
        student = (await self._session.execute(
            select(Student)
            .where(Student.student_id_number == uid, Student.status != "WITHDRAWN")
            .limit(1)
        )).scalar_one_or_none()
        if student is None:
            return None
        return await self._build_student_po_report_context(student)

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

        section_teacher_name = (await self._session.execute(
            select(User.full_name)
            .join(FacultyAssignment, FacultyAssignment.user_id == User.id)
            .where(
                FacultyAssignment.section_offering_id == offering_id,
                FacultyAssignment.role_in_course == "SECTION_TEACHER",
                FacultyAssignment.removed_at.is_(None),
            )
            .limit(1)
        )).scalar_one_or_none() or ""

        module_leader_name = (await self._session.execute(
            select(User.full_name)
            .join(ModuleLeaderAssignment, ModuleLeaderAssignment.user_id == User.id)
            .where(
                ModuleLeaderAssignment.organization_id == org_id,
                ModuleLeaderAssignment.batch_id == offering.batch_id,
                ModuleLeaderAssignment.academic_term_id == offering.academic_term_id,
                ModuleLeaderAssignment.course_id == offering.course_id,
                ModuleLeaderAssignment.removed_at.is_(None),
            )
            .limit(1)
        )).scalar_one_or_none() or ""

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
            "section_teacher_name": section_teacher_name,
            "module_leader_name": module_leader_name,
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


async def render_marksheet_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("marksheet_report.html").render(**context)

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)


async def render_marksheet_course_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("marksheet_course_report.html").render(**context)

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)


async def render_end_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("end_report.html").render(**context)

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)


async def render_student_po_report_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("student_po_report.html").render(**context)

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)


def build_drive_links_workbook(rows: list[dict]) -> bytes:
    """Builds an .xlsx (Section, Status, Students, Submitted At, Drive Link)
    for the Program Coordinator's drive-links export."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Drive Links"

    headers = ["Section", "Status", "Students", "Submitted At", "Drive Link"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in sorted(rows, key=lambda r: r["section_name"]):
        submitted_at = row["submitted_at"]
        ws.append([
            row["section_name"],
            row["status"],
            row["student_count"],
            submitted_at.strftime("%Y-%m-%d %H:%M") if submitted_at else "",
            row.get("course_drive_link") or "",
        ])

    widths = [12, 14, 10, 18, 60]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]

GRADE_THRESHOLDS = [
    (80, "A+"), (75, "A"), (70, "A-"), (65, "B+"), (60, "B"),
    (55, "B-"), (50, "C+"), (45, "C"), (40, "D"),
]


def _pct_to_grade(pct: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if pct >= threshold:
            return grade
    return "F"


class CourseEndReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, section_offering_id: UUID, org_id: UUID, user_id: UUID) -> CourseEndReport:
        result = await self._session.execute(
            select(CourseEndReport).where(CourseEndReport.section_offering_id == section_offering_id)
        )
        report = result.scalar_one_or_none()
        if report:
            return report
        report = CourseEndReport(
            organization_id=org_id,
            section_offering_id=section_offering_id,
            created_by_user_id=user_id,
            grade_distribution={},
            co_attainment={},
            unattained_co_explanations=[],
            status="DRAFT",
        )
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)
        return report

    async def get(self, section_offering_id: UUID) -> CourseEndReport | None:
        result = await self._session.execute(
            select(CourseEndReport).where(CourseEndReport.section_offering_id == section_offering_id)
        )
        return result.scalar_one_or_none()

    async def save_draft(self, section_offering_id: UUID, body, org_id: UUID, user_id: UUID) -> CourseEndReport:
        report = await self.get(section_offering_id)
        if report is None:
            report = CourseEndReport(
                organization_id=org_id,
                section_offering_id=section_offering_id,
                created_by_user_id=user_id,
            )
            self._session.add(report)
        elif report.status == "SUBMITTED":
            from app.modules.assessment.exceptions import ResultAlreadySubmittedError
            raise ResultAlreadySubmittedError()
        report.grade_distribution = body.grade_distribution
        report.co_attainment = body.co_attainment
        report.unattained_co_explanations = [e.model_dump() for e in body.unattained_co_explanations]
        report.teacher_feedback = body.teacher_feedback
        report.course_drive_link = body.course_drive_link or None
        await self._session.flush()
        await self._session.refresh(report)
        return report

    async def submit(self, section_offering_id: UUID, body, org_id: UUID, user_id: UUID) -> CourseEndReport:
        report = await self.get(section_offering_id)
        if report is None:
            report = CourseEndReport(
                organization_id=org_id,
                section_offering_id=section_offering_id,
                created_by_user_id=user_id,
            )
            self._session.add(report)
        elif report.status == "SUBMITTED":
            from app.modules.assessment.exceptions import ResultAlreadySubmittedError
            raise ResultAlreadySubmittedError()

        # Drive link is required for submission
        drive_link = (body.course_drive_link or "").strip()
        if not drive_link or "drive.google.com" not in drive_link:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A valid Google Drive link is required to submit the end report.",
            )

        report.grade_distribution = body.grade_distribution
        report.co_attainment = body.co_attainment
        report.unattained_co_explanations = [e.model_dump() for e in body.unattained_co_explanations]
        report.teacher_feedback = body.teacher_feedback
        report.course_drive_link = drive_link
        report.status = "SUBMITTED"
        report.submitted_at = datetime.now(timezone.utc)

        pub_result = await self._session.execute(
            select(ResultPublication).where(ResultPublication.section_offering_id == section_offering_id)
        )
        pub = pub_result.scalar_one_or_none()
        if pub is not None and pub.status == "DRAFT":
            pub.status = "SUBMITTED"
            pub.submitted_by_user_id = user_id
            pub.submitted_at = datetime.now(timezone.utc)
        elif pub is None:
            pub = ResultPublication(
                organization_id=org_id,
                section_offering_id=section_offering_id,
                status="SUBMITTED",
                submitted_by_user_id=user_id,
                submitted_at=datetime.now(timezone.utc),
            )
            self._session.add(pub)

        await self._session.commit()
        await self._session.refresh(report)
        return report

    async def _get_co_threshold(self, org_id: UUID, curriculum_id: UUID | None = None) -> float:
        """CO attainment threshold (%) for a curriculum, set by the Program Coordinator.
        Defaults to 50 when the curriculum can't be resolved."""
        if curriculum_id is not None:
            curriculum = (await self._session.execute(
                select(Curriculum).where(Curriculum.id == curriculum_id)
            )).scalar_one_or_none()
            if curriculum is not None:
                return float(curriculum.threshold_co_score_pct)
        return 50.0

    async def _build_co_outcome_rows(
        self, curriculum_id: UUID | None, course_id: UUID
    ) -> list[dict]:
        """Build the Section-1 CO table rows (code, statement, and the PO / learning
        domain / knowledge profile / complex problem / complex activity mappings).
        Shared by the per-section and combined end reports so both render mappings."""
        co_rows: list = []
        if curriculum_id is not None:
            co_rows = list((await self._session.execute(
                select(CourseOutcome)
                .where(
                    CourseOutcome.curriculum_id == curriculum_id,
                    CourseOutcome.course_id == course_id,
                )
                .order_by(CourseOutcome.code)
            )).scalars().all())
        if not co_rows:
            all_rows = list((await self._session.execute(
                select(CourseOutcome)
                .where(CourseOutcome.course_id == course_id)
                .order_by(CourseOutcome.code)
            )).scalars().all())
            seen: set[str] = set()
            co_rows = []
            for co in all_rows:
                if co.code not in seen:
                    seen.add(co.code)
                    co_rows.append(co)

        co_ids = [co.id for co in co_rows]

        from app.modules.obe.models import CourseOutcomeBloomLevel, COKPMapping, COCPMapping, COCAMapping
        from app.modules.ref_data.models import BloomLevel, ComplexProblem, ComplexActivity, KnowledgeProfile

        bloom_links = list((await self._session.execute(
            select(CourseOutcomeBloomLevel).where(CourseOutcomeBloomLevel.course_outcome_id.in_(co_ids))
        )).scalars().all()) if co_ids else []
        bloom_ids = {bl.bloom_level_id for bl in bloom_links}
        bloom_map: dict = {}
        if bloom_ids:
            bloom_map = {b.id: b.code for b in (await self._session.execute(
                select(BloomLevel).where(BloomLevel.id.in_(bloom_ids))
            )).scalars().all()}

        mapping_set = None
        if co_ids:
            if curriculum_id is not None:
                mapping_set = (await self._session.execute(
                    select(COPOMappingSet).where(
                        and_(COPOMappingSet.curriculum_id == curriculum_id, COPOMappingSet.course_id == course_id)
                    )
                )).scalar_one_or_none()
            if mapping_set is None:
                mapping_set = (await self._session.execute(
                    select(COPOMappingSet).where(COPOMappingSet.course_id == course_id)
                    .order_by(COPOMappingSet.created_at.desc()).limit(1)
                )).scalar_one_or_none()

        po_by_co: dict[UUID, list[str]] = defaultdict(list)
        if mapping_set:
            entries = (await self._session.execute(
                select(COPOMappingEntry).where(COPOMappingEntry.mapping_set_id == mapping_set.id)
            )).scalars().all()
            po_ids = {e.program_outcome_id for e in entries}
            po_map = {}
            if po_ids:
                po_map = {po.id: po.code for po in (await self._session.execute(
                    select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids))
                )).scalars().all()}
            for e in entries:
                code = po_map.get(e.program_outcome_id)
                if code and code not in po_by_co[e.course_outcome_id]:
                    po_by_co[e.course_outcome_id].append(code)

        kp_by_co: dict[UUID, list[str]] = defaultdict(list)
        cp_by_co: dict[UUID, list[str]] = defaultdict(list)
        ca_by_co: dict[UUID, list[str]] = defaultdict(list)
        if co_ids:
            kp_rows = (await self._session.execute(
                select(COKPMapping).where(COKPMapping.course_outcome_id.in_(co_ids))
            )).scalars().all()
            kp_ids = {r.knowledge_profile_id for r in kp_rows}
            kp_map = {k.id: k.code for k in (await self._session.execute(
                select(KnowledgeProfile).where(KnowledgeProfile.id.in_(kp_ids))
            )).scalars().all()} if kp_ids else {}
            for r in kp_rows:
                c = kp_map.get(r.knowledge_profile_id)
                if c:
                    kp_by_co[r.course_outcome_id].append(c)

            cp_rows = (await self._session.execute(
                select(COCPMapping).where(COCPMapping.course_outcome_id.in_(co_ids))
            )).scalars().all()
            cp_ids = {r.complex_problem_id for r in cp_rows}
            cp_map = {k.id: k.code for k in (await self._session.execute(
                select(ComplexProblem).where(ComplexProblem.id.in_(cp_ids))
            )).scalars().all()} if cp_ids else {}
            for r in cp_rows:
                c = cp_map.get(r.complex_problem_id)
                if c:
                    cp_by_co[r.course_outcome_id].append(c)

            ca_rows = (await self._session.execute(
                select(COCAMapping).where(COCAMapping.course_outcome_id.in_(co_ids))
            )).scalars().all()
            ca_ids = {r.complex_activity_id for r in ca_rows}
            ca_map = {k.id: k.code for k in (await self._session.execute(
                select(ComplexActivity).where(ComplexActivity.id.in_(ca_ids))
            )).scalars().all()} if ca_ids else {}
            for r in ca_rows:
                c = ca_map.get(r.complex_activity_id)
                if c:
                    ca_by_co[r.course_outcome_id].append(c)

        bloom_by_co: dict[UUID, list[str]] = defaultdict(list)
        for bl in bloom_links:
            c = bloom_map.get(bl.bloom_level_id)
            if c:
                bloom_by_co[bl.course_outcome_id].append(c)

        return [
            {
                "code": co.code,
                "statement": co.statement,
                "pos": ", ".join(sorted(po_by_co.get(co.id, []))) or "—",
                "learning_domains": ", ".join(sorted(bloom_by_co.get(co.id, []))) or "—",
                "knowledge_profile": ", ".join(sorted(kp_by_co.get(co.id, []))) or "—",
                "complex_problem": ", ".join(sorted(cp_by_co.get(co.id, []))) or "—",
                "complex_activity": ", ".join(sorted(ca_by_co.get(co.id, []))) or "—",
            }
            for co in co_rows
        ]

    async def build_end_report_context(self, section_offering_id: UUID, org_id: UUID) -> dict:
        report = await self.get(section_offering_id)
        if report is None:
            from app.modules.assessment.exceptions import EndReportNotFoundError
            raise EndReportNotFoundError()

        row = (await self._session.execute(
            select(
                Course.code.label("course_code"),
                Course.title.label("course_title"),
                Course.credits.label("credits"),
                Course.theory_hours.label("theory_hours"),
                Course.lab_hours.label("lab_hours"),
                AcademicTerm.name.label("term_name"),
                AcademicTerm.year.label("term_year"),
                AcademicTerm.season.label("term_season"),
                Section.name.label("section_name"),
                Batch.name.label("batch_name"),
                SectionOffering.curriculum_id,
                SectionOffering.course_id,
            )
            .select_from(SectionOffering)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .where(SectionOffering.id == section_offering_id)
        )).first()

        if row is None:
            raise SectionOfferingNotFoundError()

        program_acronym = ""
        department_name = ""
        curriculum_row = (await self._session.execute(
            select(Curriculum).where(Curriculum.id == row.curriculum_id)
        )).scalar_one_or_none()
        if curriculum_row:
            prog = (await self._session.execute(
                select(Program).where(Program.id == curriculum_row.program_id)
            )).scalar_one_or_none()
            if prog:
                program_acronym = prog.acronym
                dept = (await self._session.execute(
                    select(Department).where(Department.id == prog.department_id)
                )).scalar_one_or_none()
                if dept:
                    department_name = f"{dept.name} ({dept.short_name})"

        teacher_info = None
        if report.created_by_user_id:
            user = (await self._session.execute(
                select(User).where(User.id == report.created_by_user_id)
            )).scalar_one_or_none()
            if user:
                teacher_info = {
                    "full_name": user.full_name,
                    "designation": user.designation or "",
                    "email": user.email or "",
                }

        course_outcomes = await self._build_co_outcome_rows(row.curriculum_id, row.course_id)

        grade_distribution = report.grade_distribution or {}
        total_students = sum(grade_distribution.get(g, 0) for g in GRADES)

        co_attainment = report.co_attainment or {}
        co_attainment_entries = [
            {"code": code, "pct": pct}
            for code, pct in co_attainment.items()
        ]

        threshold = float((await self._get_co_threshold(org_id, row.curriculum_id)))
        unattained = report.unattained_co_explanations or []
        # All COs attained when attainment data exists and none falls below threshold.
        all_co_attained = bool(co_attainment) and all(
            float(pct) >= threshold for pct in co_attainment.values()
        )
        empty_explanation_rows = 0 if all_co_attained else max(0, 2 - len(unattained))

        feedback_text = report.teacher_feedback or ""
        feedback_lines = [line.strip() for line in feedback_text.split("\n") if line.strip()] if feedback_text else []

        org_repo = OrgRepository(self._session)
        org = await org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        conduct_hours = row.theory_hours + row.lab_hours
        if conduct_hours == 0:
            conduct_hours = row.credits

        return {
            "section": {
                "course_code": row.course_code,
                "course_title": row.course_title,
                "credits": row.credits,
                "conduct_hours": conduct_hours,
                "term_name": row.term_name,
                "term_year": row.term_year,
                "term_season": row.term_season,
                "section_name": row.section_name,
                "batch_name": row.batch_name,
            },
            "program_acronym": program_acronym,
            "department_name": department_name,
            "teacher": teacher_info,
            "ml": None,
            "course_outcomes": course_outcomes,
            "grades": GRADES,
            "grade_distribution": grade_distribution,
            "total_students": total_students,
            "co_attainment_entries": co_attainment_entries,
            "unattained_co_explanations": unattained,
            "empty_explanation_rows": empty_explanation_rows,
            "all_co_attained": all_co_attained,
            "feedback_lines": feedback_lines,
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
        }

    async def list_pending_for_ml(self, org_id: UUID) -> list[dict]:
        from app.modules.curriculum.models import SectionOffering, Course, Batch, AcademicTerm, Section
        result = await self._session.execute(
            select(CourseEndReport, Course, SectionOffering, Section, Batch, AcademicTerm)
            .join(SectionOffering, CourseEndReport.section_offering_id == SectionOffering.id)
            .join(Course, SectionOffering.course_id == Course.id)
            .join(Section, SectionOffering.section_id == Section.id)
            .join(Batch, SectionOffering.batch_id == Batch.id)
            .join(AcademicTerm, SectionOffering.academic_term_id == AcademicTerm.id)
            .where(CourseEndReport.organization_id == org_id)
            .where(CourseEndReport.status == "SUBMITTED")
            .order_by(CourseEndReport.submitted_at.desc())
        )
        rows = result.all()
        return [
            {
                "id": str(report.id),
                "section_offering_id": str(report.section_offering_id),
                "course_code": course.code,
                "course_title": course.title,
                "section_name": section.name,
                "batch_name": batch.name,
                "term_name": term.name,
                "term_season": term.season,
                "term_year": term.year,
                "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
                "teacher_feedback": report.teacher_feedback,
            }
            for report, course, offering, section, batch, term in rows
        ]

    async def get_combined_data(
        self, course_id: UUID, batch_id: UUID, academic_term_id: UUID, org_id: UUID,
    ) -> dict:
        rows = (await self._session.execute(
            select(SectionOffering, Section, CourseEndReport)
            .join(Section, Section.id == SectionOffering.section_id)
            .outerjoin(CourseEndReport, CourseEndReport.section_offering_id == SectionOffering.id)
            .where(
                SectionOffering.organization_id == org_id,
                SectionOffering.course_id == course_id,
                SectionOffering.batch_id == batch_id,
                SectionOffering.academic_term_id == academic_term_id,
            )
            .order_by(Section.name)
        )).all()

        sections = []
        combined_grade: dict[str, int] = {g: 0 for g in GRADES}
        co_attainment_sums: dict[str, float] = defaultdict(float)
        co_attainment_counts: dict[str, int] = defaultdict(int)
        all_unattained: list[dict] = []
        section_feedbacks: list[dict] = []
        total_submitted = 0

        for offering, section, report in rows:
            is_submitted = report is not None and report.status == "SUBMITTED"
            sections.append({
                "section_name": section.name,
                "section_offering_id": str(offering.id),
                "end_report_status": report.status if report else None,
            })
            if not is_submitted:
                continue
            total_submitted += 1
            gd = report.grade_distribution or {}
            for g in GRADES:
                combined_grade[g] += gd.get(g, 0)
            for co_code, pct in (report.co_attainment or {}).items():
                co_attainment_sums[co_code] += float(pct)
                co_attainment_counts[co_code] += 1
            for exp in (report.unattained_co_explanations or []):
                all_unattained.append({**exp, "section_name": section.name})
            if report.teacher_feedback:
                section_feedbacks.append({
                    "section_name": section.name,
                    "feedback": report.teacher_feedback,
                })

        co_attainment_avg = {
            code: round(co_attainment_sums[code] / co_attainment_counts[code], 1)
            for code in co_attainment_sums
        }

        curriculum_id = rows[0][0].curriculum_id if rows else None
        threshold = await self._get_co_threshold(org_id, curriculum_id)
        unattained_cos = sorted(
            code for code, pct in co_attainment_avg.items() if float(pct) < threshold
        )

        course_row = (await self._session.execute(
            select(Course.code, Course.title, Course.credits, Course.theory_hours, Course.lab_hours)
            .where(Course.id == course_id)
        )).first()
        batch_row = (await self._session.execute(select(Batch.name).where(Batch.id == batch_id))).scalar_one()
        term_row = (await self._session.execute(
            select(AcademicTerm.name, AcademicTerm.season, AcademicTerm.year)
            .where(AcademicTerm.id == academic_term_id)
        )).first()

        return {
            "course_code": course_row.code if course_row else "",
            "course_title": course_row.title if course_row else "",
            "credits": course_row.credits if course_row else 0,
            "batch_name": batch_row,
            "term_name": term_row.name if term_row else "",
            "term_season": term_row.season if term_row else "",
            "term_year": term_row.year if term_row else 0,
            "sections": sections,
            "total_sections": len(sections),
            "submitted_sections": total_submitted,
            "combined_grade_distribution": combined_grade,
            "combined_co_attainment": co_attainment_avg,
            "all_unattained_explanations": all_unattained,
            "section_feedbacks": section_feedbacks,
            "co_threshold": threshold,
            "unattained_cos": unattained_cos,
        }

    async def build_combined_end_report_context(
        self, course_id: UUID, batch_id: UUID, academic_term_id: UUID, org_id: UUID,
        ml_feedback: str = "", unattained_justifications: list[dict] | None = None,
    ) -> dict:
        data = await self.get_combined_data(course_id, batch_id, academic_term_id, org_id)

        first_offering_id = None
        for s in data["sections"]:
            if s["end_report_status"] == "SUBMITTED":
                first_offering_id = UUID(s["section_offering_id"])
                break
        if first_offering_id is None and data["sections"]:
            first_offering_id = UUID(data["sections"][0]["section_offering_id"])

        program_acronym = ""
        department_name = ""
        curriculum_id = None
        if first_offering_id:
            curriculum_id = (await self._session.execute(
                select(SectionOffering.curriculum_id).where(SectionOffering.id == first_offering_id)
            )).scalar_one_or_none()
            if curriculum_id:
                curriculum_row = (await self._session.execute(
                    select(Curriculum).where(Curriculum.id == curriculum_id)
                )).scalar_one_or_none()
                if curriculum_row:
                    prog = (await self._session.execute(
                        select(Program).where(Program.id == curriculum_row.program_id)
                    )).scalar_one_or_none()
                    if prog:
                        program_acronym = prog.acronym
                        dept = (await self._session.execute(
                            select(Department).where(Department.id == prog.department_id)
                        )).scalar_one_or_none()
                        if dept:
                            department_name = f"{dept.name} ({dept.short_name})"

        org_repo = OrgRepository(self._session)
        org = await org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        ml_user = (await self._session.execute(
            select(User)
            .join(ModuleLeaderAssignment, ModuleLeaderAssignment.user_id == User.id)
            .where(
                ModuleLeaderAssignment.organization_id == org_id,
                ModuleLeaderAssignment.batch_id == batch_id,
                ModuleLeaderAssignment.academic_term_id == academic_term_id,
                ModuleLeaderAssignment.course_id == course_id,
                ModuleLeaderAssignment.removed_at.is_(None),
            )
            .limit(1)
        )).scalar_one_or_none()
        ml_info = {
            "full_name": ml_user.full_name,
            "designation": getattr(ml_user, "designation", "") or "",
            "email": ml_user.email or "",
        } if ml_user else None

        course_outcomes = await self._build_co_outcome_rows(curriculum_id, course_id)

        co_attainment_entries = [
            {"code": code, "pct": pct}
            for code, pct in data["combined_co_attainment"].items()
        ]

        total_students = sum(data["combined_grade_distribution"].get(g, 0) for g in GRADES)
        # Combined report is authored by the Module Leader: section teachers' CO
        # justifications are excluded. Instead the ML justifies each unattained CO
        # (combined attainment below threshold). When every CO is attained, the
        # template prints "All COs attained" rather than empty cells.
        unattained_cos: list[str] = data["unattained_cos"]
        all_co_attained = bool(data["combined_co_attainment"]) and not unattained_cos
        justification_map = {
            (j.get("co_code") or "").strip(): j
            for j in (unattained_justifications or [])
        }
        unattained: list[dict] = [
            {
                "co_code": code,
                "reason": (justification_map.get(code, {}).get("reason") or "").strip(),
                "suggestion": (justification_map.get(code, {}).get("suggestion") or "").strip(),
            }
            for code in unattained_cos
        ]
        empty_explanation_rows = 0 if (all_co_attained or unattained) else 2

        ml_feedback_lines = [l.strip() for l in ml_feedback.split("\n") if l.strip()] if ml_feedback else []

        conduct_hours = 0
        if data["credits"]:
            conduct_hours = data["credits"]

        section_names = ", ".join(s["section_name"] for s in data["sections"])

        return {
            "section": {
                "course_code": data["course_code"],
                "course_title": data["course_title"],
                "credits": data["credits"],
                "conduct_hours": conduct_hours,
                "term_name": data["term_name"],
                "term_year": data["term_year"],
                "term_season": data["term_season"],
                "section_name": f"Combined ({section_names})",
                "batch_name": data["batch_name"],
            },
            "program_acronym": program_acronym,
            "department_name": department_name,
            "teacher": None,
            "ml": ml_info,
            "course_outcomes": course_outcomes,
            "grades": GRADES,
            "grade_distribution": data["combined_grade_distribution"],
            "total_students": total_students,
            "co_attainment_entries": co_attainment_entries,
            "unattained_co_explanations": unattained,
            "empty_explanation_rows": empty_explanation_rows,
            "all_co_attained": all_co_attained,
            "feedback_lines": ml_feedback_lines,
            # Section teacher feedback is excluded from the combined report — the ML's
            # overall feedback above is the only commentary shown.
            "section_feedbacks": [],
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
            "is_combined": True,
        }
