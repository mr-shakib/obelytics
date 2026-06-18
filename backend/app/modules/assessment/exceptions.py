from fastapi import HTTPException, status


class StudentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")


class StudentIdConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this ID number already exists in this organization",
        )


class EnrollmentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")


class EnrollmentConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this section offering",
        )


class AssessmentNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")


class AssessmentLockedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is locked",
        )


class WeightageNotHundredError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Total weightage must equal 100% before opening marks",
        )


class COWeightNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="CO weight not found")


class COWeightConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="CO weight already exists for this assessment and course outcome",
        )


class InvalidCOError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CO must be PUBLISHED to be referenced in assessment weights",
        )


class MarkNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Mark not found")


class MarkConflictError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mark already exists for this assessment and enrollment",
        )


class MarkImmutableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marks are locked after result publication",
        )


class InvalidMarkError(HTTPException):
    def __init__(self, detail: str = "Invalid mark data"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class ResultPublicationNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Result publication not found")


class ResultStateError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class NoMarksEnteredError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot submit results: no marks have been entered",
        )


class MarksheetQuestionNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Marksheet question not found")


class MarksheetSectionTeacherScopeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage marks for sections you are assigned to teach",
        )


class MarksheetLockedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="This section's results have been submitted and are locked. Ask your Module Leader to unlock the section to make changes.",
        )


class ResultAlreadySubmittedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="This end report has already been submitted",
        )


class EndReportNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="End report not found")
