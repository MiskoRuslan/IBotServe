import os
import asyncio
from pathlib import Path
from typing import Dict, Optional
from telethon import TelegramClient, events
from telethon.tl.types import User
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.config import async_session_maker
from models import Userbot, Member, MessageHistory
from uuid import UUID

load_dotenv()


class MessageListenerService:
    """Service for listening to messages from trusted users"""

    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.active_listeners: Dict[str, TelegramClient] = {}
        self.listener_tasks: Dict[str, asyncio.Task] = {}

        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH must be set in .env file")

    def _find_session_by_phone(self, phone: str) -> Optional[Path]:
        """Find session file by phone number"""
        phone_clean = phone.lstrip('+')
        for variant in [f'+{phone_clean}', phone_clean]:
            p = self.sessions_dir / f"{variant}.session"
            if p.exists():
                return p
        return None

    async def _save_message(
        self,
        message_text: str,
        userbot_id: UUID,
        group_id: Optional[UUID] = None,
        additional_info: Optional[dict] = None
    ):
        """Save message to database"""
        try:
            async with async_session_maker() as db:
                message = MessageHistory(
                    message=message_text,
                    userbot_id=userbot_id,
                    group_id=group_id,
                    additional_info=additional_info or {}
                )
                db.add(message)
                await db.commit()
                print(f"[MessageListener] Message saved for userbot {userbot_id}")
        except Exception as e:
            print(f"[MessageListener] Error saving message: {e}")

    async def start_listener_for_userbot(self, userbot_id: str, phone: str, trusted_id: int):
        """Start message listener for a specific userbot"""
        try:
            session_path = self._find_session_by_phone(phone)
            if not session_path:
                print(f"[MessageListener] Session not found for {phone}")
                return

            client = TelegramClient(
                str(session_path.with_suffix('')),
                self.api_id,
                self.api_hash
            )

            await client.connect()

            if not client.is_user_authorized():
                print(f"[MessageListener] Session not authorized for {phone}")
                await client.disconnect()
                return

            # Store active client
            self.active_listeners[userbot_id] = client

            print(f"[MessageListener] Started listening for userbot {phone} (trusted_id: {trusted_id})")

            # Handler for new messages
            @client.on(events.NewMessage(from_users=trusted_id))
            async def message_handler(event):
                try:
                    message_text = event.message.message
                    sender = await event.get_sender()

                    additional_info = {
                        "sender_id": sender.id if sender else None,
                        "sender_username": sender.username if sender and hasattr(sender, 'username') else None,
                        "message_id": event.message.id,
                        "date": event.message.date.isoformat() if event.message.date else None
                    }

                    print(f"[MessageListener] Received message from {trusted_id} to {phone}: {message_text[:50]}...")

                    await self._save_message(
                        message_text=message_text,
                        userbot_id=UUID(userbot_id),
                        additional_info=additional_info
                    )

                except Exception as e:
                    print(f"[MessageListener] Error handling message: {e}")

            # Keep client running
            await client.run_until_disconnected()

        except Exception as e:
            print(f"[MessageListener] Error in listener for {phone}: {e}")
        finally:
            if userbot_id in self.active_listeners:
                del self.active_listeners[userbot_id]

    async def start_all_listeners(self):
        """Start listeners for all admin userbots with trusted_id"""
        try:
            async with async_session_maker() as db:
                # Get all members who are admins
                result = await db.execute(
                    select(Member).where(Member.is_admin == True)
                )
                admin_members = result.scalars().all()

                # Get userbots for these admins with trusted_id set
                for member in admin_members:
                    userbot_result = await db.execute(
                        select(Userbot).where(
                            Userbot.id == member.userbot_id,
                            Userbot.trusted_id.isnot(None),
                            Userbot.phone_number.isnot(None)
                        )
                    )
                    userbot = userbot_result.scalar_one_or_none()

                    if userbot:
                        userbot_id_str = str(userbot.id)

                        # Skip if already listening
                        if userbot_id_str in self.listener_tasks:
                            continue

                        # Start listener in background
                        task = asyncio.create_task(
                            self.start_listener_for_userbot(
                                userbot_id_str,
                                userbot.phone_number,
                                userbot.trusted_id
                            )
                        )
                        self.listener_tasks[userbot_id_str] = task

                        print(f"[MessageListener] Started listener for admin {userbot.phone_number}")

                print(f"[MessageListener] Total active listeners: {len(self.listener_tasks)}")

        except Exception as e:
            print(f"[MessageListener] Error starting listeners: {e}")

    async def stop_listener_for_userbot(self, userbot_id: str):
        """Stop listener for a specific userbot"""
        if userbot_id in self.active_listeners:
            client = self.active_listeners[userbot_id]
            await client.disconnect()
            del self.active_listeners[userbot_id]

        if userbot_id in self.listener_tasks:
            task = self.listener_tasks[userbot_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.listener_tasks[userbot_id]

        print(f"[MessageListener] Stopped listener for userbot {userbot_id}")

    async def stop_all_listeners(self):
        """Stop all active listeners"""
        for userbot_id in list(self.listener_tasks.keys()):
            await self.stop_listener_for_userbot(userbot_id)

        print("[MessageListener] All listeners stopped")

    def get_active_listeners_count(self) -> int:
        """Get number of active listeners"""
        return len(self.active_listeners)


# Global instance
message_listener = MessageListenerService()
