from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models.contacts import Contact
from database.managers.base_manager import BaseManager


class ContactsManager(BaseManager[Contact]):

    def __init__(self):
        super().__init__(Contact)

    async def contact_exists(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        contact_userbot_id: UUID
    ) -> bool:

        result = await db.execute(
            select(Contact).where(
                and_(
                    Contact.userbot_id == userbot_id,
                    Contact.contact_userbot_id == contact_userbot_id
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_contacts_for_userbot(
        self,
        db: AsyncSession,
        userbot_id: UUID
    ) -> List[Contact]:

        result = await db.execute(
            select(Contact)
            .where(Contact.userbot_id == userbot_id)
            .order_by(Contact.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_missing_contacts(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        potential_contact_ids: List[UUID]
    ) -> List[UUID]:

        result = await db.execute(
            select(Contact.contact_userbot_id)
            .where(
                and_(
                    Contact.userbot_id == userbot_id,
                    Contact.contact_userbot_id.in_(potential_contact_ids)
                )
            )
        )
        existing_contact_ids = set(result.scalars().all())

        return [uid for uid in potential_contact_ids if uid not in existing_contact_ids]

    async def bulk_create_contacts(
        self,
        db: AsyncSession,
        userbot_id: UUID,
        contact_ids: List[UUID]
    ) -> List[Contact]:

        contacts = []
        for contact_id in contact_ids:
            if contact_id == userbot_id:
                continue

            if not await self.contact_exists(db, userbot_id, contact_id):
                contact = Contact(
                    userbot_id=userbot_id,
                    contact_userbot_id=contact_id
                )
                db.add(contact)
                contacts.append(contact)

        await db.flush()
        for contact in contacts:
            await db.refresh(contact)

        return contacts
