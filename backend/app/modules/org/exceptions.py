from fastapi import HTTPException, status


class OrgNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")


class DepartmentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")


class DepartmentShortNameConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this short name already exists",
        )


class DepartmentArchivedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department is already archived",
        )


class DepartmentHasDependentDataError(HTTPException):
    def __init__(self, blockers: list[str]):
        detail = (
            "Cannot delete this department — it still has: " + ", ".join(blockers)
            + ". Remove or reassign those first, or archive the department instead."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ProgramNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")


class ProgramAcronymConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A program with this acronym already exists",
        )


class ProgramArchivedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Program is already archived",
        )


class ProgramHasDependentDataError(HTTPException):
    def __init__(self, blockers: list[str]):
        detail = (
            "Cannot delete this program — it still has: " + ", ".join(blockers)
            + ". Remove or reassign those first, or archive the program instead."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
