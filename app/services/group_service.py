import os
import asyncio
import random
from pathlib import Path
from typing import List, Dict
from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest, AddChatUserRequest
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import UserAlreadyParticipantError, UserPrivacyRestrictedError
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
        Створити групу в Telegram та додати учасників

        Args:
            admin_phone: Номер телефону адміна (який створює групу)
            group_name: Назва групи
            members_info: Список словників з інформацією про учасників
                         [{"phone": "+123456", "name": "John Doe"}, ...]

        Returns:
            int: Telegram chat_id створеної групи
        """
        # Знайти сесію адміна
        admin_session_path = self._find_session_by_phone(admin_phone)
        if not admin_session_path:
            raise ValueError(f"Сесію для адміна {admin_phone} не знайдено")

        # Створити клієнт для адміна
        admin_client = TelegramClient(
            str(admin_session_path.with_suffix('')),
            self.api_id,
            self.api_hash
        )

        chat_id = None

        try:
            await admin_client.connect()

            if not await admin_client.is_user_authorized():
                raise ValueError(f"Сесія адміна {admin_phone} не авторизована")

            # Крок 1: Додати всіх учасників у контакти
            print("Додавання учасників у контакти адміна...")
            contacts_to_import = []

            for i, member_info in enumerate(members_info):
                member_phone = member_info.get('phone', '').lstrip('+')
                member_name = member_info.get('name', 'User')

                # Розділити ім'я на first та last
                name_parts = member_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                contact = InputPhoneContact(
                    client_id=i,
                    phone=member_phone,
                    first_name=first_name,
                    last_name=last_name
                )
                contacts_to_import.append(contact)

            # Імпортувати всі контакти одразу
            if contacts_to_import:
                result = await admin_client(ImportContactsRequest(contacts_to_import))
                print(f"Додано {len(result.users)} контактів")

            # Крок 2: Отримати об'єкти користувачів
            users_to_add = []
            for member_info in members_info:
                try:
                    member_phone = member_info.get('phone', '').lstrip('+')
                    # Тепер користувач є в контактах, можемо його знайти
                    user = await admin_client.get_entity(f'+{member_phone}')
                    users_to_add.append(user)
                    print(f"Знайдено користувача: {user.first_name or member_phone}")
                except Exception as e:
                    print(f"Не вдалося знайти користувача {member_phone}: {e}")
                    continue

            if not users_to_add:
                raise ValueError("Жоден з учасників не знайдено")

            # Створити групу з першим учасником
            print(f"Створення групи '{group_name}' з першим учасником...")
            result = await admin_client(CreateChatRequest(
                users=[users_to_add[0]],
                title=group_name
            ))

            # Почекати трохи, щоб група створилась
            await asyncio.sleep(1)

            # Знайти створену групу через діалоги
            print("Пошук створеної групи...")
            chat_entity = None
            chat_id = None
            async for dialog in admin_client.iter_dialogs(limit=50):
                if dialog.name == group_name and dialog.is_group:
                    chat_entity = dialog.entity
                    chat_id = dialog.id
                    print(f"Знайдено групу '{group_name}' з ID: {chat_id}")
                    print(f"Тип entity: {type(chat_entity)}")
                    break

            if not chat_entity or not chat_id:
                raise ValueError(f"Не вдалося знайти створену групу '{group_name}'")

            # Додати інших учасників з рандомною затримкою
            added_count = 0
            failed_count = 0

            for i, user in enumerate(users_to_add[1:], start=1):
                try:
                    # Рандомна затримка від 2 до 7 секунд
                    delay = random.uniform(2, 7)
                    print(f"[{i}/{len(users_to_add)-1}] Очікування {delay:.2f} секунд перед додаванням наступного учасника...")
                    await asyncio.sleep(delay)

                    # Додати учасника використовуючи entity групи
                    print(f"Додавання користувача: {user.first_name or user.phone} (ID: {user.id})")

                    # Спробувати різні методи додавання
                    try:
                        # Метод 1: Використати AddChatUserRequest
                        await admin_client(AddChatUserRequest(
                            chat_id=chat_id,
                            user_id=user,
                            fwd_limit=0
                        ))
                    except Exception as e1:
                        print(f"  Метод 1 (AddChatUserRequest) не спрацював: {e1}")
                        # Метод 2: Спробувати через високорівневий API
                        try:
                            await admin_client.edit_permissions(
                                chat_entity,
                                user,
                                view_messages=True
                            )
                        except Exception as e2:
                            print(f"  Метод 2 (edit_permissions) не спрацював: {e2}")
                            raise e1  # Підняти оригінальну помилку

                    added_count += 1
                    print(f"✓ Успішно додано учасника: {user.first_name or user.phone}")

                except UserAlreadyParticipantError:
                    print(f"ℹ Користувач {user.first_name or user.phone} вже є учасником")
                    added_count += 1
                except UserPrivacyRestrictedError:
                    failed_count += 1
                    print(f"✗ Користувач {user.first_name or user.phone} має обмеження приватності")
                    continue
                except Exception as e:
                    failed_count += 1
                    print(f"✗ ПОМИЛКА при додаванні учасника {user.first_name or user.phone}: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"\n=== Підсумок ===")
            print(f"Всього учасників для додавання: {len(users_to_add)-1}")
            print(f"Успішно додано: {added_count}")
            print(f"Помилок: {failed_count}")

            return chat_id

        except Exception as e:
            raise e
        finally:
            if admin_client.is_connected():
                await admin_client.disconnect()

    def _find_session_by_phone(self, phone: str) -> Path | None:
        """Знайти session файл за номером телефону"""
        # Видалити + якщо є
        phone_clean = phone.lstrip('+')

        # Спробувати знайти файл з + та без
        for phone_variant in [f'+{phone_clean}', phone_clean]:
            session_path = self.sessions_dir / f"{phone_variant}.session"
            if session_path.exists():
                return session_path

        return None
