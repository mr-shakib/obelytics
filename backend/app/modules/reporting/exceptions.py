from fastapi import HTTPException, status


class ReportRunNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Report run not found")


class UnknownReportDefinitionError(HTTPException):
    def __init__(self, definition_id: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown report definition: {definition_id}",
        )
