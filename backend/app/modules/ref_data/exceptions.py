from fastapi import HTTPException, status


class RefDataNotFoundError(HTTPException):
    def __init__(self, item: str = "Record"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"{item} not found")


class RefDataConflictError(HTTPException):
    def __init__(self, detail: str = "A record with this value already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
