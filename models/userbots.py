from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Userbot(BaseModel):
    __tablename__ = "userbots"

    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)

    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="userbot",
        cascade="all, delete-orphan"
    )
