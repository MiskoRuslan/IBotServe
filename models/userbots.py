from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from models.base import BaseModel


class Userbot(BaseModel):
    __tablename__ = "userbots"

    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    trusted_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Style settings for message generation
    style_settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default='{"allow_profanity": false, "use_punctuation": true, "use_uppercase": true, "send_photos": false, "gender": "male", "send_stickers": false, "use_ascii_emoticons": false, "emoji_probability": 0, "message_length": "medium", "use_youth_slang": false, "use_illiterate_slang": false, "use_typos": false, "language": "ukrainian"}'
    )

    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="userbot",
        cascade="all, delete-orphan"
    )
