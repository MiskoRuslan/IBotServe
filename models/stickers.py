from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class Sticker(BaseModel):
    """Sticker model for storing userbot stickers with emotions"""
    __tablename__ = "stickers"

    userbot_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )

    file_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Telegram file_id of the sticker"
    )

    emotion: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Emotion tag: laughter, sad, angry, love, surprised, etc."
    )

    userbot: Mapped["Userbot"] = relationship(
        "Userbot",
        backref="stickers"
    )
