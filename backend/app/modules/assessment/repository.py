from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import (
    Assessment,
    AssessmentCOWeight,
    ResultPublication,
    Student,
    StudentEnrollment,
    StudentMark,
)


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, student_id: UUID, org_id: UUID) -> Student | None:
        result = await self._session.execute(
            select(Student).where(
                and_(Student.id == student_id, Student.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self, org_id: UUID, program_id: UUID | None = None) -> list[Student]:
        stmt = select(Student).where(
            and_(Student.organization_id == org_id, Student.status == "ACTIVE")
        )
        if program_id:
            stmt = stmt.where(Student.program_id == program_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_student_id_number(self, sid_number: str, org_id: UUID) -> Student | None:
        result = await self._session.execute(
            select(Student).where(
                and_(
                    Student.student_id_number == sid_number,
                    Student.organization_id == org_id,
                    Student.status != "WITHDRAWN",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: Student) -> Student:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: Student, data: dict) -> Student:
        for key, value in data.items():
            if value is not None:
                setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class EnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, enrollment_id: UUID, org_id: UUID) -> StudentEnrollment | None:
        result = await self._session.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.id == enrollment_id,
                    StudentEnrollment.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_offering(self, offering_id: UUID) -> list[StudentEnrollment]:
        result = await self._session.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.section_offering_id == offering_id
            )
        )
        return list(result.scalars().all())

    async def list_by_student(self, student_id: UUID) -> list[StudentEnrollment]:
        result = await self._session.execute(
            select(StudentEnrollment).where(StudentEnrollment.student_id == student_id)
        )
        return list(result.scalars().all())

    async def find_by_student_offering(
        self, student_id: UUID, offering_id: UUID
    ) -> StudentEnrollment | None:
        result = await self._session.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.section_offering_id == offering_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: StudentEnrollment) -> StudentEnrollment:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, assessment_id: UUID, org_id: UUID) -> Assessment | None:
        result = await self._session.execute(
            select(Assessment).where(
                and_(Assessment.id == assessment_id, Assessment.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_offering(self, offering_id: UUID) -> list[Assessment]:
        result = await self._session.execute(
            select(Assessment).where(Assessment.section_offering_id == offering_id)
        )
        return list(result.scalars().all())

    async def sum_weightage(self, offering_id: UUID) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Assessment.weightage_percent), 0))
            .where(Assessment.section_offering_id == offering_id)
        )
        return result.scalar()

    async def create(self, obj: Assessment) -> Assessment:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: Assessment, data: dict) -> Assessment:
        for key, value in data.items():
            if value is not None:
                setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class AssessmentCOWeightRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_assessment(self, assessment_id: UUID) -> list[AssessmentCOWeight]:
        result = await self._session.execute(
            select(AssessmentCOWeight).where(AssessmentCOWeight.assessment_id == assessment_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, weight_id: UUID) -> AssessmentCOWeight | None:
        result = await self._session.execute(
            select(AssessmentCOWeight).where(AssessmentCOWeight.id == weight_id)
        )
        return result.scalar_one_or_none()

    async def find_by_assessment_co(
        self, assessment_id: UUID, co_id: UUID
    ) -> AssessmentCOWeight | None:
        result = await self._session.execute(
            select(AssessmentCOWeight).where(
                and_(
                    AssessmentCOWeight.assessment_id == assessment_id,
                    AssessmentCOWeight.course_outcome_id == co_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: AssessmentCOWeight) -> AssessmentCOWeight:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: AssessmentCOWeight) -> None:
        await self._session.delete(obj)
        await self._session.flush()


class MarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mark_id: UUID, org_id: UUID) -> StudentMark | None:
        result = await self._session.execute(
            select(StudentMark).where(
                and_(StudentMark.id == mark_id, StudentMark.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_assessment(self, assessment_id: UUID) -> list[StudentMark]:
        result = await self._session.execute(
            select(StudentMark).where(StudentMark.assessment_id == assessment_id)
        )
        return list(result.scalars().all())

    async def find_by_assessment_enrollment(
        self, assessment_id: UUID, enrollment_id: UUID
    ) -> StudentMark | None:
        result = await self._session.execute(
            select(StudentMark).where(
                and_(
                    StudentMark.assessment_id == assessment_id,
                    StudentMark.student_enrollment_id == enrollment_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def count_by_offering(self, offering_id: UUID) -> int:
        """Count all marks for all assessments in this offering."""
        result = await self._session.execute(
            select(func.count(StudentMark.id))
            .join(Assessment, StudentMark.assessment_id == Assessment.id)
            .where(Assessment.section_offering_id == offering_id)
        )
        return result.scalar() or 0

    async def create(self, obj: StudentMark) -> StudentMark:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: StudentMark, data: dict) -> StudentMark:
        for key, value in data.items():
            if value is not None:
                setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class ResultPublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_offering(self, offering_id: UUID) -> ResultPublication | None:
        result = await self._session.execute(
            select(ResultPublication).where(
                ResultPublication.section_offering_id == offering_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, pub_id: UUID, org_id: UUID) -> ResultPublication | None:
        result = await self._session.execute(
            select(ResultPublication).where(
                and_(
                    ResultPublication.id == pub_id,
                    ResultPublication.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ResultPublication) -> ResultPublication:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: ResultPublication, data: dict) -> ResultPublication:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj
