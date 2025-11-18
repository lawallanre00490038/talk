# app/db/repositories/base.py
from typing import Any, Generic, Type, TypeVar, Optional
import uuid
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, session: AsyncSession, id: str, *, options: list | None = None) -> Optional[ModelType]:
        """Retrieve an instance by primary key. Accepts optional loader options (e.g., selectinload)."""
        opts = options or []
        result = await session.get(self.model, id, options=opts)
        return result

    async def create(self, session: AsyncSession, *, obj_in: SQLModel) -> ModelType:
        session.add(obj_in)
        await session.commit()
        await session.refresh(obj_in)
        return obj_in

    async def get_all(self, session: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        result = await session.execute(statement)
        return result.scalars().all()
