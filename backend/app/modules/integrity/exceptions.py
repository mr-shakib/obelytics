from fastapi import HTTPException, status


class SectionOfferingNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Section offering not found")


class SectionAccessDeniedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only audit sections you teach or courses you lead",
        )


class UnsupportedPaperTypeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload the question paper as a PDF, Word (.docx), JPEG, PNG or WebP file",
        )


class PaperTooLargeError(HTTPException):
    def __init__(self, max_bytes: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The file is larger than {max_bytes // (1024 * 1024)} MB",
        )


class PaperTooManyPagesError(HTTPException):
    def __init__(self, max_pages: int):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A question paper can have at most {max_pages} pages",
        )


class PaperUnreadableError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)


class JobAlreadyRunningError(HTTPException):
    def __init__(self, kind: str | None):
        what = {"READ_PAPER": "reading the paper", "AUDIT": "running the audit"}.get(kind or "")
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Already {what} for this exam. Wait for it to finish."
                if what else "Something is already running for this exam. Wait for it to finish."
            ),
        )


class JobSubmissionError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The background worker could not be reached. Try again in a minute.",
        )


class QuestionNotInSectionError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more questions do not belong to this section and exam",
        )


class NoQuestionTextError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add the question wording (upload the paper or type it) before running the audit",
        )


class QuestionAuditNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Question audit not found")


class OverrideReasonRequiredError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Give a reason when you disagree with the AI judgment",
        )
