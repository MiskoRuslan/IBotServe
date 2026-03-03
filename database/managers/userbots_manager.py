from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.userbots import Userbot
from database.managers.base_manager import BaseManager


class UserBotsManager(BaseManager[Userbot]):

    def __init__(self):
        super().__init__(Userbot)

    async def get_by_phone(
        self,
        db: AsyncSession,
        phone_number: str
    ) -> Optional[Userbot]:
        result = await db.execute(
            select(self.model).where(self.model.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        db: AsyncSession,
        username: str
    ) -> Optional[Userbot]:
        result = await db.execute(
            select(self.model).where(self.model.username == username)
        )
        return result.scalar_one_or_none()

    async def find_by_phone_or_username(
        self,
        db: AsyncSession,
        phone_number: Optional[str] = None,
        username: Optional[str] = None
    ) -> Optional[Userbot]:
        if not phone_number and not username:
            return None

        conditions = []
        if phone_number:
            conditions.append(self.model.phone_number == phone_number)
        if username:
            conditions.append(self.model.username == username)

        result = await db.execute(
            select(self.model).where(or_(*conditions))
        )
        return result.scalar_one_or_none()

    async def get_all_with_phone(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Userbot]:
        result = await db.execute(
            select(self.model)
            .where(self.model.phone_number.isnot(None))
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def search_by_name(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> List[Userbot]:
        result = await db.execute(
            select(self.model)
            .where(self.model.name.ilike(f"%{query}%"))
            .limit(limit)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def bulk_create(
        self,
        db: AsyncSession,
        userbots_data: List[dict]
    ) -> List[Userbot]:
        instances = []
        for data in userbots_data:
            instance = self.model(**data)
            db.add(instance)
            instances.append(instance)

        await db.flush()
        for instance in instances:
            await db.refresh(instance)

        return instances

    async def update_from_telegram(
        self,
        db: AsyncSession,
        phone_number: str,
        name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Optional[Userbot]:
        existing = await self.get_by_phone(db, phone_number)

        if existing:
            update_data = {}
            if name:
                update_data['name'] = name
            if username:
                update_data['username'] = username

            if update_data:
                return await self.update(db, existing.id, **update_data)
            return existing
        else:
            return await self.create(
                db,
                phone_number=phone_number,
                name=name,
                username=username
            )
