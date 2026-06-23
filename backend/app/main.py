import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.middleware.correlation_id import CorrelationIDMiddleware
from app.core.middleware.timing import TimingMiddleware
from app.core.redis_client import close_redis, get_redis
from app.modules.accreditation.router import router as accreditation_router
from app.modules.approval.router import router as approval_router
from app.modules.assessment.router import router as assessment_router
from app.modules.attainment.router import router as attainment_router
from app.modules.audit.router import router as audit_router
from app.modules.curriculum.router import router as curriculum_router
from app.modules.iam.router.admin_router import router as admin_router
from app.modules.iam.router.auth_router import router as auth_router
from app.modules.iam.router.role_router import router as role_router
from app.modules.iam.router.user_router import router as user_router
from app.modules.notification.router import router as notification_router
from app.modules.obe.router import router as obe_router
from app.modules.org.router import router as org_router
from app.modules.ref_data.router import router as ref_data_router
from app.modules.reporting.router import router as reporting_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Middleware — outermost added last, processed first on request
    app.add_middleware(TimingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health (no auth)
    @app.get("/health/live", tags=["Health"])
    async def liveness():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        errors: dict[str, str] = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            errors["db"] = str(exc)
        try:
            redis = await get_redis()
            await redis.ping()
        except Exception as exc:
            errors["redis"] = str(exc)
        if errors:
            raise HTTPException(status_code=503, detail=errors)
        return {"status": "ok", "db": "ok", "redis": "ok"}

    # Phase 1 — IAM
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(user_router, prefix=settings.API_V1_PREFIX)
    app.include_router(role_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_router, prefix=settings.API_V1_PREFIX)

    # Phase 2 — Organization + Reference Data
    app.include_router(org_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ref_data_router, prefix=settings.API_V1_PREFIX)

    # Phase 3 — Curriculum
    app.include_router(curriculum_router, prefix=settings.API_V1_PREFIX)

    # Phase 4 — OBE
    app.include_router(obe_router, prefix=settings.API_V1_PREFIX)

    # Phase 5 — Assessment
    app.include_router(assessment_router, prefix=settings.API_V1_PREFIX)

    # Phase 6 — Attainment
    app.include_router(attainment_router, prefix=settings.API_V1_PREFIX)

    # Phase 7 — Approval
    app.include_router(approval_router, prefix=settings.API_V1_PREFIX)

    # Phase 8 — Audit + Notifications
    app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
    app.include_router(notification_router, prefix=settings.API_V1_PREFIX)

    # Phase 9 — Reporting + Accreditation
    app.include_router(reporting_router, prefix=settings.API_V1_PREFIX)
    app.include_router(accreditation_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
