from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attainment.engine import AttainmentEngine
from app.modules.attainment.exceptions import AttainmentConfigNotFound, AttainmentNotComputed
from app.modules.attainment.models import AttainmentConfig
from app.modules.attainment.repository import (
    AttainmentConfigRepository,
    COAttainmentResultRepository,
    POAttainmentResultRepository,
)
from app.modules.attainment.schemas import AttainmentConfigUpdate


class AttainmentConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AttainmentConfigRepository(session)

    async def get_config(
        self, org_id: UUID, program_id: UUID | None = None
    ) -> AttainmentConfig:
        """
        Try program-specific config first, then org-wide default.
        If neither exists, create the org-wide default with 50/50 thresholds.
        """
        if program_id is not None:
            config = await self._repo.get_for_program(org_id, program_id)
            if config is not None:
                return config

        # Try org-wide default
        config = await self._repo.get_for_org(org_id)
        if config is not None:
            return config

        default_config = AttainmentConfig(
            organization_id=org_id,
            program_id=None,
            threshold_co_score_pct=Decimal("50.00"),
        )
        result = await self._repo.create(default_config)
        await self._session.commit()
        return result

    async def update_config(
        self, org_id: UUID, program_id: UUID | None, data: AttainmentConfigUpdate
    ) -> AttainmentConfig:
        """Get or create config for (org_id, program_id), then update fields."""
        if program_id is not None:
            config = await self._repo.get_for_program(org_id, program_id)
            if config is None:
                # Create program-specific config
                config = AttainmentConfig(
                    organization_id=org_id,
                    program_id=program_id,
                    threshold_co_score_pct=Decimal("50.00"),
                )
                config = await self._repo.create(config)
        else:
            config = await self._repo.get_for_org(org_id)
            if config is None:
                config = AttainmentConfig(
                    organization_id=org_id,
                    program_id=None,
                    threshold_co_score_pct=Decimal("50.00"),
                )
                config = await self._repo.create(config)

        update_data = data.model_dump(exclude_none=True)
        result = await self._repo.update(config, update_data)
        await self._session.commit()
        return result


class AttainmentResultService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._co_repo = COAttainmentResultRepository(session)
        self._po_repo = POAttainmentResultRepository(session)

    async def get_summary(self, org_id: UUID, section_offering_id: UUID) -> dict:
        """
        Returns dict with co_results and po_results lists.
        Raises AttainmentNotComputed if no CO results exist for this offering.
        """
        co_results = await self._co_repo.list_by_offering(section_offering_id)
        if not co_results:
            raise AttainmentNotComputed(
                f"No attainment results computed for offering {section_offering_id}"
            )
        po_results = await self._po_repo.list_by_offering(section_offering_id)
        return {
            "section_offering_id": section_offering_id,
            "co_results": co_results,
            "po_results": po_results,
        }

    async def trigger_recompute(self, org_id: UUID, section_offering_id: UUID) -> dict:
        """
        Instantiate AttainmentEngine and call compute_for_section_offering.
        Commits after computation and returns summary.
        """
        engine = AttainmentEngine(self._session)
        await engine.compute_for_section_offering(section_offering_id, org_id)
        await self._session.commit()
        return await self.get_summary(org_id, section_offering_id)
