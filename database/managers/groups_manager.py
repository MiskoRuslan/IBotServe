from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.groups import Group
from models.userbots import Userbot
from database.managers.base_manager import BaseManager


class GroupsManager(BaseManager[Group]):
    """Менеджер для роботи з групами"""

    def __init__(self):
        super().__init__(Group)

    async def get_by_telegram_id(
        self,
        db: AsyncSession,
        telegram_id: int
    ) -> Optional[Group]:
        """
        Отримати групу за Telegram ID

        Args:
            db: Async database session
            telegram_id: Telegram chat_id

        Returns:
            Об'єкт Group або None
        """
        result = await db.execute(
            select(self.model).where(self.model.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Group]:
        """
        Отримати групу за назвою

        Args:
            db: Async database session
            name: Назва групи

        Returns:
            Об'єкт Group або None
        """
        result = await db.execute(
            select(self.model).where(self.model.name == name)
        )
        return result.scalar_one_or_none()

    async def get_with_members(
        self,
        db: AsyncSession,
        group_id: UUID
    ) -> Optional[Group]:
        """
        Отримати групу разом з учасниками

        Args:
            db: Async database session
            group_id: UUID групи

        Returns:
            Об'єкт Group з завантаженими members або None
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.id == group_id)
            .options(selectinload(self.model.members))
        )
        return result.scalar_one_or_none()

    async def get_by_admin(
        self,
        db: AsyncSession,
        admin_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Group]:
        """
        Отримати всі групи конкретного адміна

        Args:
            db: Async database session
            admin_id: UUID адміна (userbot)
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список груп
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.admin_id == admin_id)
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
    ) -> List[Group]:
        """
        Пошук груп за назвою

        Args:
            db: Async database session
            query: Пошуковий запит
            limit: Максимальна кількість результатів

        Returns:
            Список знайдених груп
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.name.ilike(f"%{query}%"))
            .limit(limit)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_all_with_members(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Group]:
        """
        Отримати всі групи разом з учасниками

        Args:
            db: Async database session
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список груп з завантаженими members
        """
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.members))
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_with_admin(
        self,
        db: AsyncSession,
        name: str,
        admin_id: UUID,
        telegram_id: Optional[int] = None
    ) -> Group:
        """
        Створити групу з адміном

        Args:
            db: Async database session
            name: Назва групи
            admin_id: UUID адміна
            telegram_id: Telegram chat_id (опціонально)

        Returns:
            Створений об'єкт Group
        """
        return await self.create(
            db,
            name=name,
            admin_id=admin_id,
            telegram_id=telegram_id
        )

    async def update_telegram_id(
        self,
        db: AsyncSession,
        group_id: UUID,
        telegram_id: int
    ) -> Optional[Group]:
        """
        Оновити Telegram ID групи

        Args:
            db: Async database session
            group_id: UUID групи
            telegram_id: Новий Telegram chat_id

        Returns:
            Оновлений об'єкт Group або None
        """
        return await self.update(db, group_id, telegram_id=telegram_id)

    async def count_by_admin(
        self,
        db: AsyncSession,
        admin_id: UUID
    ) -> int:
        """
        Підрахувати кількість груп конкретного адміна

        Args:
            db: Async database session
            admin_id: UUID адміна

        Returns:
            Кількість груп
        """
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(self.model.id))
            .where(self.model.admin_id == admin_id)
        )
        return result.scalar() or 0
