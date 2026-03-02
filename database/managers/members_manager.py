from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.members import Member
from models.userbots import Userbot
from models.groups import Group
from database.managers.base_manager import BaseManager


class MembersManager(BaseManager[Member]):
    """Менеджер для роботи з учасниками груп"""

    def __init__(self):
        super().__init__(Member)

    async def get_by_userbot_and_group(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        group_id: UUID
    ) -> Optional[Member]:
        """
        Знайти запис про членство в групі

        Args:
            db: Async database session
            userbot_id: UUID юзербота
            group_id: UUID групи

        Returns:
            Об'єкт Member або None
        """
        result = await db.execute(
            select(self.model).where(
                and_(
                    self.model.userbot_id == userbot_id,
                    self.model.group_id == group_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_members_by_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Member]:
        """
        Отримати всіх учасників конкретної групи

        Args:
            db: Async database session
            group_id: UUID групи
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список об'єктів Member
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.group_id == group_id)
            .options(selectinload(self.model.userbot))
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at)
        )
        return list(result.scalars().all())

    async def get_groups_by_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Member]:
        """
        Отримати всі групи в яких є конкретний юзербот

        Args:
            db: Async database session
            userbot_id: UUID юзербота
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список об'єктів Member з завантаженими group
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.userbot_id == userbot_id)
            .options(selectinload(self.model.group))
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_member_to_group(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        group_id: UUID
    ) -> Member:
        """
        Додати учасника до групи

        Args:
            db: Async database session
            userbot_id: UUID юзербота
            group_id: UUID групи

        Returns:
            Створений об'єкт Member
        """
        # Перевірити чи не існує вже
        existing = await self.get_by_userbot_and_group(db, userbot_id, group_id)
        if existing:
            return existing

        return await self.create(
            db,
            userbot_id=userbot_id,
            group_id=group_id
        )

    async def remove_member_from_group(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        group_id: UUID
    ) -> bool:
        """
        Видалити учасника з групи

        Args:
            db: Async database session
            userbot_id: UUID юзербота
            group_id: UUID групи

        Returns:
            True якщо видалено, False якщо не знайдено
        """
        member = await self.get_by_userbot_and_group(db, userbot_id, group_id)
        if not member:
            return False

        return await self.delete(db, member.id)

    async def bulk_add_members(
        self,
        db: AsyncSession,
        group_id: UUID,
        userbot_ids: List[UUID]
    ) -> List[Member]:
        """
        Масово додати учасників до групи

        Args:
            db: Async database session
            group_id: UUID групи
            userbot_ids: Список UUID юзерботів

        Returns:
            Список створених об'єктів Member
        """
        members = []
        for userbot_id in userbot_ids:
            # Перевірити чи не існує
            existing = await self.get_by_userbot_and_group(db, userbot_id, group_id)
            if not existing:
                member = self.model(
                    userbot_id=userbot_id,
                    group_id=group_id
                )
                db.add(member)
                members.append(member)
            else:
                members.append(existing)

        await db.flush()
        for member in members:
            if member not in db:
                await db.refresh(member)

        return members

    async def count_members_in_group(
        self,
        db: AsyncSession,
        group_id: UUID
    ) -> int:
        """
        Підрахувати кількість учасників в групі

        Args:
            db: Async database session
            group_id: UUID групи

        Returns:
            Кількість учасників
        """
        result = await db.execute(
            select(func.count(self.model.id))
            .where(self.model.group_id == group_id)
        )
        return result.scalar() or 0

    async def count_groups_for_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID
    ) -> int:
        """
        Підрахувати кількість груп в яких є юзербот

        Args:
            db: Async database session
            userbot_id: UUID юзербота

        Returns:
            Кількість груп
        """
        result = await db.execute(
            select(func.count(self.model.id))
            .where(self.model.userbot_id == userbot_id)
        )
        return result.scalar() or 0

    async def is_member_of_group(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        group_id: UUID
    ) -> bool:
        """
        Перевірити чи є юзербот учасником групи

        Args:
            db: Async database session
            userbot_id: UUID юзербота
            group_id: UUID групи

        Returns:
            True якщо є учасником, False якщо ні
        """
        member = await self.get_by_userbot_and_group(db, userbot_id, group_id)
        return member is not None

    async def get_userbots_by_group(
        self,
        db: AsyncSession,
        group_id: UUID
    ) -> List[Userbot]:
        """
        Отримати список юзерботів в групі

        Args:
            db: Async database session
            group_id: UUID групи

        Returns:
            Список об'єктів Userbot
        """
        result = await db.execute(
            select(Userbot)
            .join(Member, Member.userbot_id == Userbot.id)
            .where(Member.group_id == group_id)
            .order_by(Member.created_at)
        )
        return list(result.scalars().all())
