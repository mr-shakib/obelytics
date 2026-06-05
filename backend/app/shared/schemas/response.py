from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def ok(data: T) -> ApiResponse[T]:
    return ApiResponse(success=True, data=data)


def error(code: str, message: str, field: str | None = None) -> ErrorResponse:
    return ErrorResponse(
        success=False,
        error=ErrorDetail(code=code, message=message, field=field),
    )
