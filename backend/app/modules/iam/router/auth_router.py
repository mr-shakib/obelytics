from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.iam.models import User
from app.modules.iam.schemas import (
    ChangePasswordBody,
    LoginRequest,
    PasswordResetConfirmBody,
    PasswordResetRequestBody,
    RefreshRequest,
    TokenResponse,
)
from app.modules.iam.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    svc = AuthService(db)
    return await svc.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    svc = AuthService(db)
    return await svc.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    svc = AuthService(db)
    await svc.logout(body.refresh_token)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordBody,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    await svc.change_password(current_user.id, body.current_password, body.new_password)


@router.post("/password-reset-request", status_code=204)
async def request_password_reset(
    body: PasswordResetRequestBody, db: Annotated[AsyncSession, Depends(get_db)]
):
    svc = AuthService(db)
    await svc.request_password_reset(body.email)


@router.post("/password-reset-confirm", status_code=204)
async def confirm_password_reset(
    body: PasswordResetConfirmBody, db: Annotated[AsyncSession, Depends(get_db)]
):
    svc = AuthService(db)
    await svc.confirm_password_reset(body.token, body.new_password)
