from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseManager(Generic[ModelType]):
    """
    Базовий менеджер для роботи з БД
    Надає стандартні CRUD операції для всіх моделей
    """

    def __init__(self, model: Type[ModelType]):
        """
        Args:
            model: SQLAlchemy модель для якої створюється менеджер
        """
        self.model = model

    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        """
        Створити новий запис в БД

        Args:
            db: Async database session
            **kwargs: Поля моделі

        Returns:
            Створений об'єкт моделі
        """
        instance = self.model(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        """
        Отримати запис за ID

        Args:
            db: Async database session
            id: UUID запису

        Returns:
            Об'єкт моделі або None
        """
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
        """
        Отримати всі записи з пагінацією

        Args:
            db: Async database session
            skip: Скільки записів пропустити
            limit: Максимальна кількість записів

        Returns:
            Список об'єктів моделі
        """
        result = await db.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        """
        Підрахувати загальну кількість записів

        Args:
            db: Async database session

        Returns:
            Кількість записів
        """
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
        """
        Оновити запис за ID

        Args:
            db: Async database session
            id: UUID запису
            **kwargs: Поля для оновлення

        Returns:
            Оновлений об'єкт або None
        """
        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
        )
        await db.flush()
        return await self.get_by_id(db, id)

    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """
        Видалити запис за ID

        Args:
            db: Async database session
            id: UUID запису

        Returns:
            True якщо видалено, False якщо не знайдено
        """
        result = await db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await db.flush()
        return result.rowcount > 0

    async def exists(self, db: AsyncSession, id: UUID) -> bool:
        """
        Перевірити чи існує запис з таким ID

        Args:
            db: Async database session
            id: UUID запису

        Returns:
            True якщо існує, False якщо ні
        """
        result = await db.execute(
            select(func.count(self.model.id))
            .where(self.model.id == id)
        )
        count = result.scalar()
        return count > 0
