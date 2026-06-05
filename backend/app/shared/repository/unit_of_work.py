from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.shared.events.base_event import DomainEvent
from app.shared.events import bus


class UnitOfWork:
    def __init__(self) -> None:
        self._session: AsyncSession | None = None
        self._events: list[DomainEvent] = []

    @property
    def session(self) -> AsyncSession:
        assert self._session is not None, "UoW session not started — use as async context manager"
        return self._session

    def register_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    async def __aenter__(self) -> "UnitOfWork":
        self._session = AsyncSessionLocal()
        self._events = []
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()
        await self._dispatch_events()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
        self._events.clear()

    async def _dispatch_events(self) -> None:
        events = list(self._events)
        self._events.clear()
        for event in events:
            await bus.publish(event)


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    async with UnitOfWork() as uow:
        yield uow
