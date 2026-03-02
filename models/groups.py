from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Group(BaseModel):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String, nullable=False)

    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="group",
        cascade="all, delete-orphan"
    )
