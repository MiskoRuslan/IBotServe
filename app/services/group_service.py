import os
import asyncio
import random
from pathlib import Path
from typing import List, Dict
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact, ChannelParticipantsAdmins
from telethon.errors import (
    UserAlreadyParticipantError,
    UserPrivacyRestrictedError,
    PeerFloodError,
    ChatAdminRequiredError,
    UserIdInvalidError
)
from dotenv import load_dotenv

load_dotenv()


class GroupService:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')

        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID та API_HASH мають бути встановлені в .env файлі")

    async def create_group_with_members(
        self,
        admin_phone: str,
        group_name: str,
        members_info: List[Dict[str, str]]
    ) -> int:
        """
        Створити супергрупу в Telegram та додати учасників

        Args:
            admin_phone: Номер телефону адміна (який створює групу)
            group_name: Назва групи
            members_info: Список словників [{"phone": "+380...", "name": "John Doe"}, ...]

        Returns:
            int: Telegram chat_id створеної супергрупи (негативне число, наприклад -1001234567890)
        """
        admin_session_path = self._find_session_by_phone(admin_phone)

        client = TelegramClient(
            str(admin_session_path.with_suffix('')),
            self.api_id,
            self.api_hash
        )

        try:
            await client.connect()

            # ─── 1. Додати номери в контакти (полегшує подальший пошук) ───
            print("Імпорт контактів...")
            contacts = []
            for i, info in enumerate(members_info):
                phone = info.get('phone', '').lstrip('+')
                name = info.get('name', 'User').strip()
                parts = name.split(' ', 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ''

                contacts.append(InputPhoneContact(
                    client_id=i,
                    phone=phone,
                    first_name=first,
                    last_name=last
                ))

            if contacts:
                await client(ImportContactsRequest(contacts))
                await asyncio.sleep(1.2)  # невелика пауза після імпорту

            # ─── 2. Отримати InputUser для всіх учасників ───
            users_input = []
            for info in members_info:
                phone = info.get('phone', '').strip()
                if not phone.startswith('+'):
                    phone = '+' + phone
                try:
                    entity = await client.get_entity(phone)
                    users_input.append(await client.get_input_entity(entity))
                    print(f"OK → {entity.first_name or phone}")
                except Exception as e:
                    print(f"Не вдалося отримати {phone}: {type(e).__name__} {e}")
                    continue

            if not users_input:
                raise ValueError("Не вдалося отримати жодного дійсного користувача")

            # ─── 3. Створити супергрупу (megagroup=True) ───
            print(f"Створюємо супергрупу '{group_name}'...")
            created = await client(CreateChannelRequest(
                title=group_name,
                about="",
                megagroup=True  # ← це ключовий момент!
            ))

            # Отримуємо entity щойно створеної групи
            group = created.chats[0]
            group_input = await client.get_input_entity(group)

            print(f"Створено супергрупу: {group.title} | ID: {group.id} | chat_id: {-1000000000000 - group.id}")

            # ─── 4. Додавання учасників (крім себе, якщо ти вже там) ───
            added = 0
            failed = 0

            for idx, user_input in enumerate(users_input, 1):
                try:
                    delay = random.uniform(0.5, 1.5)
                    print(f"[{idx}/{len(users_input)}] Очікування {delay:.1f}с...")
                    await asyncio.sleep(delay)

                    await client(InviteToChannelRequest(
                        channel=group_input,
                        users=[user_input]
                    ))

                    added += 1
                    print(f"✓ Додано")

                except UserAlreadyParticipantError:
                    added += 1
                    print(" вже в групі")
                except UserPrivacyRestrictedError:
                    failed += 1
                    print(" приватність забороняє додавання")
                except PeerFloodError:
                    print("!!! FLOOD WAIT — треба чекати кілька хвилин/годин !!!")
                    failed += 1
                    await asyncio.sleep(180)  # хоча б 2 хв
                except ChatAdminRequiredError:
                    print("!!! Потрібні права адміністратора (додавання учасників) !!!")
                    raise
                except UserIdInvalidError:
                    print(" невалідний користувач")
                    failed += 1
                except Exception as e:
                    failed += 1
                    print(f"ПОМИЛКА: {type(e).__name__}: {e}")

            print("\n" + "═" * 50)
            print(f"Усього цільових учасників: {len(users_input)}")
            print(f"Успішно / вже були:     {added}")
            print(f"Не вдалося:              {failed}")
            print("═" * 50)

            return -1000000000000 - group.id   # стандартний формат chat_id для супергруп

        finally:
            if client.is_connected():
                await client.disconnect()

    def _find_session_by_phone(self, phone: str) -> Path | None:
        phone_clean = phone.lstrip('+')
        for variant in [f'+{phone_clean}', phone_clean]:
            p = self.sessions_dir / f"{variant}.session"
            if p.exists():
                return p
        return None
