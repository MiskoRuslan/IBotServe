from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.base import BaseModel
from uuid import UUID as UUID_TYPE


class ChatHistory(BaseModel):
    """История сообщений в группах"""
    __tablename__ = "chat_history"

    group_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False
    )

    userbot_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )

    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ID сообщения от trusted user, которое послужило триггером (если применимо)
    trigger_message_id: Mapped[UUID_TYPE | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_history.id", ondelete="SET NULL"),
        nullable=True
    )

    # Telegram message ID для возможности отслеживания
    telegram_message_id: Mapped[int | None] = mapped_column(nullable=True)

    # Дополнительная информация (промпты, использованные при генерации, и т.д.)
    additional_info: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}"
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", backref="chat_messages")
    userbot: Mapped["Userbot"] = relationship("Userbot", backref="sent_messages")
    trigger_message: Mapped["MessageHistory"] = relationship(
        "MessageHistory",
        backref="generated_messages",
        foreign_keys=[trigger_message_id]
    )
