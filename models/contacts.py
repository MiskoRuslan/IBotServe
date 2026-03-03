from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class Contact(BaseModel):
    __tablename__ = "contacts"

    userbot_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )

    contact_userbot_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("userbots.id", ondelete="CASCADE"),
        nullable=False
    )

    userbot: Mapped["Userbot"] = relationship(
        "Userbot",
        foreign_keys=[userbot_id],
        backref="contacts_owned"
    )

    contact: Mapped["Userbot"] = relationship(
        "Userbot",
        foreign_keys=[contact_userbot_id],
        backref="contacted_by"
    )

    __table_args__ = (
        UniqueConstraint('userbot_id', 'contact_userbot_id', name='uq_userbot_contact'),
    )
