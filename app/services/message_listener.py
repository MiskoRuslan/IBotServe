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
from models import Userbot, Member, MessageHistory, Group, ChatHistory
from uuid import UUID
from app.services.grok_service import grok_service

load_dotenv()

conversation_service = None


def get_conversation_service():
    global conversation_service
    if conversation_service is None:
        from app.services.conversation_service import conversation_service as cs
        conversation_service = cs
    return conversation_service


class MessageListenerService:

    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.active_listeners: Dict[str, TelegramClient] = {}
        self.listener_tasks: Dict[str, asyncio.Task] = {}

        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH must be set in .env file")

    def _find_session_by_phone(self, phone: str) -> Optional[Path]:
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
    ) -> Optional[UUID]:
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
                await db.refresh(message)
                print(f"[MessageListener] Message saved for userbot {userbot_id}")
                return message.id
        except Exception as e:
            print(f"[MessageListener] Error saving message: {e}")
            return None

    async def _process_trigger_message(
        self,
        client: TelegramClient,
        trigger_message_text: str,
        trigger_message_id: UUID,
        userbot_id: UUID
    ):
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Member, Group)
                    .join(Group, Member.group_id == Group.id)
                    .where(
                        Member.userbot_id == userbot_id,
                        Member.is_admin == True
                    )
                )
                admin_memberships = result.all()

                if not admin_memberships:
                    print(f"[MessageListener] No admin groups found for userbot {userbot_id}")
                    return

                print(f"[MessageListener] Processing {len(admin_memberships)} groups for userbot {userbot_id}")

                for member, group in admin_memberships:
                    try:
                        global_prompt = group.global_prompt or ""
                        member_prompt = member.additional_prompt or ""

                        print(f"[MessageListener] Generating message for group '{group.name}'...")

                        generated_message = await grok_service.generate_conversation_starter(
                            trigger_message=trigger_message_text,
                            global_prompt=global_prompt,
                            member_prompt=member_prompt
                        )

                        print(f"[MessageListener] Generated: {generated_message}")

                        print(f"[MessageListener] Attempting to send to Telegram group ID: {group.telegram_id}")

                        try:
                            entity = await client.get_entity(group.telegram_id)
                            print(f"[MessageListener] Entity found: {entity.title} (ID: {entity.id})")

                            try:
                                participants = await client.get_participants(entity, limit=1)
                                print(f"[MessageListener] We have access to group participants")
                            except Exception as e:
                                print(f"[MessageListener] Warning: Cannot access participants: {e}")

                            sent_message = await client.send_message(
                                entity=entity,
                                message=generated_message
                            )

                            print(f"[MessageListener] ✓ Message sent successfully!")
                            print(f"[MessageListener]   - Message ID: {sent_message.id}")
                            print(f"[MessageListener]   - Chat ID: {sent_message.chat_id}")
                            print(f"[MessageListener]   - Date: {sent_message.date}")
                            print(f"[MessageListener]   - To: {entity.title}")

                        except Exception as send_error:
                            print(f"[MessageListener] ✗ Failed to send message to Telegram:")
                            print(f"[MessageListener]   - Error: {send_error}")
                            print(f"[MessageListener]   - Error type: {type(send_error).__name__}")
                            print(f"[MessageListener]   - Group: '{group.name}' (ID: {group.telegram_id})")
                            raise

                        chat_history_entry = ChatHistory(
                            group_id=group.id,
                            userbot_id=userbot_id,
                            message=generated_message,
                            trigger_message_id=trigger_message_id,
                            telegram_message_id=sent_message.id,
                            additional_info={
                                "global_prompt": global_prompt,
                                "member_prompt": member_prompt,
                                "trigger_message": trigger_message_text
                            }
                        )
                        db.add(chat_history_entry)

                        group_id_str = str(group.id)
                        group_name = group.name
                        is_active = group.is_active

                        await db.commit()

                        print(f"[MessageListener] Saved to chat_history for group '{group_name}'")
                        print(f"[MessageListener] Group active status: {is_active}")

                        if is_active:
                            print(f"[MessageListener] Starting conversation for group '{group_name}'...")
                            conv_service = get_conversation_service()
                            await conv_service.restart_conversation(group_id_str)
                            print(f"[MessageListener] ✓ Conversation started for group '{group_name}'")
                        else:
                            print(f"[MessageListener] ✗ Group '{group_name}' is not active (is_active={is_active}), conversation not started")

                    except Exception as e:
                        print(f"[MessageListener] Error processing group '{group.name}': {e}")
                        await db.rollback()
                        continue

        except Exception as e:
            print(f"[MessageListener] Error in _process_trigger_message: {e}")

    async def start_listener_for_userbot(self, userbot_id: str, phone: str, trusted_id: int):
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

            if not await client.is_user_authorized():
                print(f"[MessageListener] Session not authorized for {phone}")
                await client.disconnect()
                return

            self.active_listeners[userbot_id] = client

            print(f"[MessageListener] Started listening for userbot {phone} (trusted_id: {trusted_id})")

            async with async_session_maker() as db:
                result = await db.execute(
                    select(Member, Group)
                    .join(Group, Member.group_id == Group.id)
                    .where(
                        Member.userbot_id == UUID(userbot_id),
                        Member.is_admin == True,
                        Group.is_active == True
                    )
                )
                admin_groups = result.all()
                group_chat_ids = [group.telegram_id for _, group in admin_groups]

            print(f"[MessageListener] Listening to {len(group_chat_ids)} groups: {group_chat_ids}")

            @client.on(events.NewMessage(from_users=trusted_id))
            async def trusted_message_handler(event):
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

                    trigger_msg_id = await self._save_message(
                        message_text=message_text,
                        userbot_id=UUID(userbot_id),
                        additional_info=additional_info
                    )

                    if trigger_msg_id:
                        print(f"[MessageListener] Processing trigger message for groups...")
                        await self._process_trigger_message(
                            client=client,
                            trigger_message_text=message_text,
                            trigger_message_id=trigger_msg_id,
                            userbot_id=UUID(userbot_id)
                        )

                except Exception as e:
                    print(f"[MessageListener] Error handling trusted message: {e}")

            if group_chat_ids:
                print(f"[MessageListener] Registering group handler for chats: {group_chat_ids}")

                @client.on(events.NewMessage(chats=group_chat_ids))
                async def group_message_handler(event):
                    try:
                        print(f"[MessageListener] Group message event triggered in chat {event.chat_id}")

                        sender = await event.get_sender()
                        if not sender or not hasattr(sender, 'id'):
                            print(f"[MessageListener] Skipping message - no sender info")
                            return

                        message_text = event.message.message
                        if not message_text:
                            print(f"[MessageListener] Skipping message - no text content")
                            return

                        chat_id = event.chat_id
                        async with async_session_maker() as db:
                            result = await db.execute(
                                select(Group).where(
                                    Group.telegram_id == chat_id,
                                    Group.is_active == True
                                )
                            )
                            group = result.scalar_one_or_none()

                            if not group:
                                print(f"[MessageListener] Group not found or not active for chat_id {chat_id}")
                                return

                            existing_result = await db.execute(
                                select(ChatHistory).where(
                                    ChatHistory.telegram_message_id == event.message.id,
                                    ChatHistory.group_id == group.id
                                )
                            )
                            existing_message = existing_result.scalar_one_or_none()

                            if existing_message:
                                is_auto_generated = existing_message.additional_info.get("auto_generated", False)
                                if is_auto_generated:
                                    print(f"[MessageListener] Skipping message from userbot (already in chat_history)")
                                    return

                            chat_entry = ChatHistory(
                                group_id=group.id,
                                userbot_id=UUID(userbot_id),
                                message=message_text,
                                telegram_message_id=event.message.id,
                                additional_info={
                                    "sender_id": sender.id,
                                    "sender_name": getattr(sender, 'first_name', 'Unknown'),
                                    "sender_username": getattr(sender, 'username', None),
                                    "from_real_user": True,
                                    "date": event.message.date.isoformat() if event.message.date else None
                                }
                            )
                            db.add(chat_entry)
                            await db.commit()

                            print(f"[MessageListener] ✓ Saved user message from {getattr(sender, 'first_name', 'Unknown')} in group '{group.name}': {message_text[:50]}...")

                    except Exception as e:
                        print(f"[MessageListener] Error handling group message: {e}")
                        import traceback
                        traceback.print_exc()

                print(f"[MessageListener] ✓ Group message handler registered for {len(group_chat_ids)} groups")
            else:
                print(f"[MessageListener] No groups to listen to for userbot {phone}")

            await client.run_until_disconnected()

        except Exception as e:
            print(f"[MessageListener] Error in listener for {phone}: {e}")
        finally:
            if userbot_id in self.active_listeners:
                del self.active_listeners[userbot_id]

    async def start_all_listeners(self):
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Member).where(Member.is_admin == True)
                )
                admin_members = result.scalars().all()

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

                        if userbot_id_str in self.listener_tasks:
                            continue

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
        for userbot_id in list(self.listener_tasks.keys()):
            await self.stop_listener_for_userbot(userbot_id)

        print("[MessageListener] All listeners stopped")

    def get_active_listeners_count(self) -> int:
        return len(self.active_listeners)


# Global instance
message_listener = MessageListenerService()
