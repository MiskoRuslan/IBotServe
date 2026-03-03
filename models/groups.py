from sqlalchemy import String, BigInteger, ForeignKey, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.base import BaseModel


class Group(BaseModel):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="SET NULL"),
        nullable=True
    )
    global_prompt: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    group_settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    context_messages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    min_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    max_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=40, server_default="40")

    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="group",
        cascade="all, delete-orphan"
    )
