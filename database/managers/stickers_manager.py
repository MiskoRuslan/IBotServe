from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.stickers import Sticker
from database.managers.base_manager import BaseManager


class StickersManager(BaseManager[Sticker]):
    """Manager for stickers operations"""

    def __init__(self):
        super().__init__(Sticker)

    async def get_stickers_for_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID
    ) -> List[Sticker]:
        """
        Get all stickers for a specific userbot

        Args:
            db: Async database session
            userbot_id: Userbot ID

        Returns:
            List of stickers
        """
        result = await db.execute(
            select(Sticker)
            .where(Sticker.userbot_id == userbot_id)
            .order_by(Sticker.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_stickers_by_emotion(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        emotion: str
    ) -> List[Sticker]:
        """
        Get stickers for a specific userbot filtered by emotion

        Args:
            db: Async database session
            userbot_id: Userbot ID
            emotion: Emotion tag

        Returns:
            List of stickers with matching emotion
        """
        result = await db.execute(
            select(Sticker)
            .where(
                and_(
                    Sticker.userbot_id == userbot_id,
                    Sticker.emotion == emotion
                )
            )
            .order_by(Sticker.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_sticker(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        file_id: str,
        emotion: str
    ) -> Sticker:
        """
        Create a new sticker

        Args:
            db: Async database session
            userbot_id: Userbot ID
            file_id: Telegram file_id
            emotion: Emotion tag

        Returns:
            Created sticker
        """
        sticker = Sticker(
            userbot_id=userbot_id,
            file_id=file_id,
            emotion=emotion
        )
        db.add(sticker)
        await db.flush()
        await db.refresh(sticker)
        return sticker

    async def delete_sticker(
        self,
        db: AsyncSession,
        sticker_id: UUID
    ) -> bool:
        """
        Delete a sticker

        Args:
            db: Async database session
            sticker_id: Sticker ID

        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            delete(Sticker).where(Sticker.id == sticker_id)
        )
        await db.flush()
        return result.rowcount > 0

    async def delete_all_stickers_for_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID
    ) -> int:
        """
        Delete all stickers for a userbot

        Args:
            db: Async database session
            userbot_id: Userbot ID

        Returns:
            Number of deleted stickers
        """
        result = await db.execute(
            delete(Sticker).where(Sticker.userbot_id == userbot_id)
        )
        await db.flush()
        return result.rowcount

    async def get_random_sticker_by_emotion(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        emotion: str
    ) -> Optional[Sticker]:
        """
        Get a random sticker for a specific emotion

        Args:
            db: Async database session
            userbot_id: Userbot ID
            emotion: Emotion tag

        Returns:
            Random sticker or None if not found
        """
        from sqlalchemy import func

        result = await db.execute(
            select(Sticker)
            .where(
                and_(
                    Sticker.userbot_id == userbot_id,
                    Sticker.emotion == emotion
                )
            )
            .order_by(func.random())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_emotions_for_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID
    ) -> List[str]:
        """
        Get list of all unique emotions for a userbot

        Args:
            db: Async database session
            userbot_id: Userbot ID

        Returns:
            List of unique emotion tags
        """
        from sqlalchemy import distinct

        result = await db.execute(
            select(distinct(Sticker.emotion))
            .where(Sticker.userbot_id == userbot_id)
            .order_by(Sticker.emotion)
        )
        return list(result.scalars().all())
