from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class Member(BaseModel):
    __tablename__ = "members"

    userbot_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )
    group_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False
    )

    userbot: Mapped["Userbot"] = relationship("Userbot", back_populates="members")
    group: Mapped["Group"] = relationship("Group", back_populates="members")
