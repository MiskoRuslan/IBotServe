from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseManager(Generic[ModelType]):

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        result = await db.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(self.model.id))
        )
        return result.scalar() or 0

    async def update(
        self,
        db: AsyncSession,
        id: UUID,
        **kwargs
    ) -> Optional[ModelType]:
        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
        )
        await db.flush()
        return await self.get_by_id(db, id)

    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        result = await db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await db.flush()
        return result.rowcount > 0

    async def exists(self, db: AsyncSession, id: UUID) -> bool:
        result = await db.execute(
            select(func.count(self.model.id))
            .where(self.model.id == id)
        )
        count = result.scalar()
        return count > 0
