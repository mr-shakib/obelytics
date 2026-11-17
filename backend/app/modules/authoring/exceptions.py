from fastapi import HTTPException, status


class AuthoringUnavailableError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI writing help is not available: {reason}.",
        )


class AuthoringModelError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The AI model could not make a suggestion: {reason}. Please try again.",
        )


class SuggestionNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")


class NothingToMapError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


class MappingRuleError(HTTPException):
    """Applying the chosen links would break a mapping rule (K, CEP or CEA)."""

    def __init__(self, problems: list[str]):
        super().__init__(
            status_code=422,
            detail="These links break the mapping rules: " + " ".join(problems),
        )


class ApplyPermissionError(HTTPException):
    def __init__(self, what: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Applying these links also adds {what}, which you do not have permission to manage",
        )
