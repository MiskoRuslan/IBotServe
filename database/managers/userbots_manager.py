from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.userbots import Userbot
from database.managers.base_manager import BaseManager


class UserBotsManager(BaseManager[Userbot]):
    """Менеджер для роботи з юзерботами"""

    def __init__(self):
        super().__init__(Userbot)

    async def get_by_phone(
        self,
        db: AsyncSession,
        phone_number: str
    ) -> Optional[Userbot]:
        """
        Отримати юзербота за номером телефону

        Args:
            db: Async database session
            phone_number: Номер телефону

        Returns:
            Об'єкт Userbot або None
        """
        result = await db.execute(
            select(self.model).where(self.model.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        db: AsyncSession,
        username: str
    ) -> Optional[Userbot]:
        """
        Отримати юзербота за username

        Args:
            db: Async database session
            username: Username (без @)

        Returns:
            Об'єкт Userbot або None
        """
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
        """
        Знайти юзербота за телефоном або username

        Args:
            db: Async database session
            phone_number: Номер телефону (опціонально)
            username: Username (опціонально)

        Returns:
            Об'єкт Userbot або None
        """
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
        """
        Отримати всіх юзерботів, які мають номер телефону

        Args:
            db: Async database session
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список юзерботів з номерами телефонів
        """
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
        """
        Пошук юзерботів за ім'ям

        Args:
            db: Async database session
            query: Пошуковий запит
            limit: Максимальна кількість результатів

        Returns:
            Список знайдених юзерботів
        """
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
        """
        Масове створення юзерботів

        Args:
            db: Async database session
            userbots_data: Список словників з даними юзерботів

        Returns:
            Список створених юзерботів
        """
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
        """
        Оновити дані юзербота з Telegram або створити якщо не існує

        Args:
            db: Async database session
            phone_number: Номер телефону
            name: Ім'я з Telegram
            username: Username з Telegram

        Returns:
            Оновлений або створений Userbot
        """
        existing = await self.get_by_phone(db, phone_number)

        if existing:
            # Оновити існуючого
            update_data = {}
            if name:
                update_data['name'] = name
            if username:
                update_data['username'] = username

            if update_data:
                return await self.update(db, existing.id, **update_data)
            return existing
        else:
            # Створити нового
            return await self.create(
                db,
                phone_number=phone_number,
                name=name,
                username=username
            )
