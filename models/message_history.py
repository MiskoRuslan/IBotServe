from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.base import BaseModel


class MessageHistory(BaseModel):
    __tablename__ = "message_history"

    message: Mapped[str] = mapped_column(Text, nullable=False)

    group_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True
    )

    userbot_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )

    additional_info: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}"
    )

    userbot: Mapped["Userbot"] = relationship("Userbot", backref="message_history")
    group: Mapped["Group"] = relationship("Group", backref="message_history")
