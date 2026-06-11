from fastapi import HTTPException, status


class PONotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Program outcome not found")


class POArchivedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Program outcome is already archived",
        )


class POHasActiveMappingsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot archive: PO is referenced in mapping entries",
        )


class POCodeConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A program outcome with this code already exists for this program",
        )


class CONotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Course outcome not found")


class COStateError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class CONotEditableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course outcome cannot be edited in its current state",
        )


class MappingSetNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping set not found")


class MappingSetPublishedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mapping set is already published",
        )


class MappingEntryConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mapping entry already exists",
        )


class MappingEntryWeightError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Weight must be 1, 2, or 3",
        )


class SubMappingNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")


class SubMappingConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mapping already exists",
        )


class SubMappingNotApprovableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot approve mapping in current CO state",
        )


class MappingSetValidationError(HTTPException):
    def __init__(self, issues: list[dict]):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "CO-PO mapping has unresolved CEP/CEA requirements",
                "issues": issues,
            },
        )
