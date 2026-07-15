from fastapi import HTTPException, status


class CurriculumNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found")


class CurriculumLockedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Curriculum cannot be modified in this state",
        )


class TermNotStartedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="This semester has not been started yet — start it from the batch page first",
        )


class TermCompletedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="This semester is completed — new section offerings cannot be created in it",
        )


class CurriculumHasDependentDataError(HTTPException):
    def __init__(self, blockers: list[str]):
        detail = (
            "Cannot delete this curriculum — it still has: " + ", ".join(blockers)
            + ". Remove or reassign those first, or archive the curriculum instead."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class CurriculumCodeConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A curriculum with this code already exists for this program",
        )


class CourseNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")


class CourseCodeConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with this code already exists",
        )


class CycleDetectedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Adding this prerequisite would create a circular dependency",
        )


class PrerequisiteNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Prerequisite not found")


class BatchNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")


class BatchNameConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A batch with this name already exists in this curriculum",
        )


class BatchHasDependentDataError(HTTPException):
    def __init__(self, blockers: list[str]):
        detail = (
            "Cannot delete this batch — it still has: " + ", ".join(blockers)
            + ". Remove or reassign those first, or archive the batch instead."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class AcademicTermNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Academic term not found")


class AcademicTermConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="An academic term for this year and season already exists",
        )


class SectionNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")


class SectionConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A section with this name already exists",
        )


class SectionOfferingNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Section offering not found")


class SectionOfferingConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A section offering for this batch, course, term, and section already exists",
        )


class SectionOfferingHasDependentsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This section has related data (enrollments, assessments, marks, "
                "results, or reports). Confirm a cascade delete to remove it along "
                "with all dependent records."
            ),
        )


class FacultyAssignmentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty assignment not found")


class FacultyAssignmentConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="This faculty member is already assigned to this offering with the same role",
        )


class ModuleLeaderAssignmentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Module leader assignment not found")


class ModuleLeaderScopeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage sections and section teachers for courses you lead",
        )
