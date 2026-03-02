"""
Control Bot - звичайний Telegram бот для керування юзерботами
Дозволяє додавати нові сесії, управляти ролями та переглядати статус
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError

from database import Database

logger = logging.getLogger(__name__)


# FSM States для додавання сесії
class AddSessionStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()
    waiting_for_session_name = State()


class ControlBot:
    """Control Bot для керування юзерботами"""

    def __init__(
        self,
        bot_token: str,
        api_id: int,
        api_hash: str,
        db: Database,
        admin_user_ids: list,
        sessions_dir: str = "sessions"
    ):
        """
        Ініціалізація Control Bot

        Args:
            bot_token: Токен звичайного бота
            api_id: Telegram API ID для userbot-ів
            api_hash: Telegram API hash для userbot-ів
            db: Database instance
            admin_user_ids: Список ID адміністраторів бота
            sessions_dir: Папка для зберігання сесій
        """
        self.bot_token = bot_token
        self.api_id = api_id
        self.api_hash = api_hash
        self.db = db
        self.admin_user_ids = admin_user_ids
        self.sessions_dir = Path(sessions_dir)

        # Створюємо папку для сесій
        self.sessions_dir.mkdir(exist_ok=True)

        # Aiogram bot
        self.bot = Bot(token=bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        # Тимчасове сховище для Telethon клієнтів під час авторизації
        self.temp_clients: Dict[int, TelegramClient] = {}

        # Реєструємо хендлери
        self._register_handlers()

    def _register_handlers(self):
        """Реєструє всі хендлери бота"""
        # Команди
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.cmd_list_sessions, Command("list"))
        self.dp.message.register(self.cmd_add_session, Command("add"))
        self.dp.message.register(self.cmd_delete_session, Command("delete"))
        self.dp.message.register(self.cmd_set_admin, Command("set_admin"))
        self.dp.message.register(self.cmd_cancel, Command("cancel"))

        # FSM handlers (мають бути перед текстовими кнопками)
        self.dp.message.register(self.process_phone, AddSessionStates.waiting_for_phone)
        self.dp.message.register(self.process_code, AddSessionStates.waiting_for_code)
        self.dp.message.register(self.process_password, AddSessionStates.waiting_for_password)
        self.dp.message.register(self.process_session_name, AddSessionStates.waiting_for_session_name)

        # Текстові кнопки
        self.dp.message.register(self.cmd_add_session, F.text == "➕ Додати сесію")
        self.dp.message.register(self.cmd_list_sessions, F.text == "📋 Список сесій")
        self.dp.message.register(self.cmd_help, F.text == "ℹ️ Допомога")

    def _is_admin(self, user_id: int) -> bool:
        """Перевірка чи користувач є адміном"""
        return user_id in self.admin_user_ids

    async def cmd_start(self, message: Message):
        """Команда /start"""
        if not self._is_admin(message.from_user.id):
            await message.answer("❌ У вас немає доступу до цього бота")
            return

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Додати сесію")],
                [KeyboardButton(text="📋 Список сесій")],
                [KeyboardButton(text="ℹ️ Допомога")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "👋 Вітаю у Control Bot!\n\n"
            "Я допоможу керувати юзерботами.\n"
            "Використовуйте /help для списку команд.",
            reply_markup=keyboard
        )

    async def cmd_help(self, message: Message):
        """Команда /help"""
        if not self._is_admin(message.from_user.id):
            return

        help_text = """
📚 Доступні команди:

/add - Додати нову юзербот сесію
/list - Список всіх сесій
/delete <session_name> - Видалити сесію
/set_admin <session_name> - Встановити адмін-роль
/cancel - Скасувати поточну операцію

Або використовуйте кнопки в меню! 👇
        """

        await message.answer(help_text)

    async def cmd_list_sessions(self, message: Message):
        """Команда /list - список всіх сесій"""
        if not self._is_admin(message.from_user.id):
            return

        sessions = self.db.get_all_sessions(active_only=False)

        if not sessions:
            await message.answer("📭 Немає збережених сесій")
            return

        text = "📋 Список сесій:\n\n"

        for session in sessions:
            status = "✅" if session['is_active'] else "❌"
            admin = "👑" if session['is_admin'] else ""
            name = session['first_name'] or "Unknown"
            username = f"@{session['username']}" if session['username'] else ""

            text += (
                f"{status} {admin} {name} {username}\n"
                f"   Session: {session['session_name']}\n"
                f"   ID: {session['user_id'] or 'N/A'}\n\n"
            )

        await message.answer(text)

    async def cmd_add_session(self, message: Message, state: FSMContext):
        """Команда /add - почати процес додавання сесії"""
        if not self._is_admin(message.from_user.id):
            return

        await message.answer(
            "📱 Додавання нової юзербот сесії\n\n"
            "Введіть номер телефону у міжнародному форматі:\n"
            "Приклад: +380123456789\n\n"
            "Використовуйте /cancel щоб скасувати",
            reply_markup=ReplyKeyboardRemove()
        )

        await state.set_state(AddSessionStates.waiting_for_phone)

    async def process_phone(self, message: Message, state: FSMContext):
        """Обробка введеного номера телефону"""
        phone = message.text.strip()

        await message.answer("⏳ Відправляю код на ваш телефон...")

        try:
            # Генеруємо унікальне ім'я сесії
            import time
            session_name = f"userbot_{int(time.time())}"
            session_path = str(self.sessions_dir / session_name)

            # Створюємо Telethon клієнт
            client = TelegramClient(
                session_path,
                self.api_id,
                self.api_hash,
                device_model="IBotServe",
                system_version="1.0"
            )

            await client.connect()

            # Відправляємо код
            result = await client.send_code_request(phone)

            # Зберігаємо клієнт і дані
            self.temp_clients[message.from_user.id] = client
            await state.update_data(
                phone=phone,
                phone_code_hash=result.phone_code_hash,
                session_name=session_name
            )

            await message.answer(
                "✅ Код відправлено на ваш телефон!\n\n"
                "Введіть код підтвердження (без дефісів):"
            )

            await state.set_state(AddSessionStates.waiting_for_code)

        except PhoneNumberInvalidError:
            await message.answer("❌ Невірний формат номера телефону. Спробуйте ще раз:")
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            await message.answer(
                f"❌ Помилка: {str(e)}\n\n"
                "Спробуйте ще раз або використовуйте /cancel"
            )

    async def process_code(self, message: Message, state: FSMContext):
        """Обробка коду підтвердження"""
        code = message.text.strip()
        user_id = message.from_user.id
        data = await state.get_data()

        phone = data['phone']
        client = self.temp_clients.get(user_id)

        if not client:
            await message.answer("❌ Сесія закінчилась. Почніть спочатку: /add")
            await state.clear()
            return

        try:
            # Авторизація з кодом
            await client.sign_in(phone, code)

            # Успішна авторизація
            me = await client.get_me()

            await message.answer(
                f"✅ Успішна авторизація!\n\n"
                f"👤 {me.first_name} {me.last_name or ''}\n"
                f"🆔 ID: {me.id}\n"
                f"📱 @{me.username or 'немає username'}\n\n"
                f"Введіть зручне ім'я для сесії (англійські літери, без пробілів):"
            )

            # Зберігаємо дані користувача
            await state.update_data(
                user_id=me.id,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name
            )

            await state.set_state(AddSessionStates.waiting_for_session_name)

        except SessionPasswordNeededError:
            await message.answer(
                "🔐 Цей акаунт захищений двофакторною автентифікацією.\n\n"
                "Введіть пароль (2FA):"
            )
            await state.set_state(AddSessionStates.waiting_for_password)

        except PhoneCodeInvalidError:
            await message.answer("❌ Невірний код. Спробуйте ще раз:")

        except Exception as e:
            logger.error(f"Error during sign in: {e}")
            await message.answer(f"❌ Помилка: {str(e)}\n\nСпробуйте ще раз:")

    async def process_password(self, message: Message, state: FSMContext):
        """Обробка 2FA пароля"""
        password = message.text.strip()
        user_id = message.from_user.id
        client = self.temp_clients.get(user_id)

        # Видаляємо повідомлення з паролем
        try:
            await message.delete()
        except:
            pass

        if not client:
            await message.answer("❌ Сесія закінчилась. Почніть спочатку: /add")
            await state.clear()
            return

        try:
            # Авторизація з паролем
            await client.sign_in(password=password)

            # Успішна авторизація
            me = await client.get_me()

            await message.answer(
                f"✅ Успішна авторизація!\n\n"
                f"👤 {me.first_name} {me.last_name or ''}\n"
                f"🆔 ID: {me.id}\n"
                f"📱 @{me.username or 'немає username'}\n\n"
                f"Введіть зручне ім'я для сесії (англійські літери, без пробілів):"
            )

            # Зберігаємо дані користувача
            await state.update_data(
                user_id=me.id,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name
            )

            await state.set_state(AddSessionStates.waiting_for_session_name)

        except Exception as e:
            logger.error(f"Error with password: {e}")
            await message.answer(f"❌ Невірний пароль або помилка: {str(e)}\n\nСпробуйте ще раз:")

    async def process_session_name(self, message: Message, state: FSMContext):
        """Обробка імені для сесії"""
        custom_name = message.text.strip().replace(" ", "_")
        user_id = message.from_user.id
        data = await state.get_data()

        client = self.temp_clients.get(user_id)
        temp_session_name = data['session_name']

        if not client:
            await message.answer("❌ Сесія закінчилась. Почніть спочатку: /add")
            await state.clear()
            return

        # Перевірка чи не існує вже така назва
        existing = self.db.get_session(custom_name)
        if existing:
            await message.answer("❌ Сесія з такою назвою вже існує. Введіть інше ім'я:")
            return

        try:
            # Перейменовуємо файл сесії
            old_path = self.sessions_dir / f"{temp_session_name}.session"
            new_path = self.sessions_dir / f"{custom_name}.session"

            if old_path.exists():
                old_path.rename(new_path)

            # Відключаємо клієнт
            await client.disconnect()
            del self.temp_clients[user_id]

            # Додаємо в базу даних
            self.db.add_session(
                session_name=custom_name,
                user_id=data.get('user_id'),
                username=data.get('username'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                phone=data.get('phone'),
                is_admin=False
            )

            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="➕ Додати сесію")],
                    [KeyboardButton(text="📋 Список сесій")],
                ],
                resize_keyboard=True
            )

            await message.answer(
                f"✅ Сесію успішно додано!\n\n"
                f"📝 Назва: {custom_name}\n"
                f"👤 {data.get('first_name')}\n"
                f"🆔 ID: {data.get('user_id')}\n\n"
                f"Тепер потрібно перезапустити основний бот (main.py) щоб сесія активувалась.",
                reply_markup=keyboard
            )

            await state.clear()

        except Exception as e:
            logger.error(f"Error saving session: {e}")
            await message.answer(f"❌ Помилка при збереженні: {str(e)}")

    async def cmd_delete_session(self, message: Message):
        """Команда /delete - видалити сесію"""
        if not self._is_admin(message.from_user.id):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Використання: /delete <session_name>")
            return

        session_name = args[1].strip()

        # Перевірка чи існує
        session = self.db.get_session(session_name)
        if not session:
            await message.answer(f"❌ Сесію '{session_name}' не знайдено")
            return

        try:
            # Видаляємо файл
            session_file = self.sessions_dir / f"{session_name}.session"
            if session_file.exists():
                session_file.unlink()

            # Видаляємо з БД
            self.db.delete_session(session_name)

            await message.answer(f"✅ Сесію '{session_name}' видалено")

        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            await message.answer(f"❌ Помилка: {str(e)}")

    async def cmd_set_admin(self, message: Message):
        """Команда /set_admin - встановити адмін-роль"""
        if not self._is_admin(message.from_user.id):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Використання: /set_admin <session_name>")
            return

        session_name = args[1].strip()

        # Перевірка чи існує
        session = self.db.get_session(session_name)
        if not session:
            await message.answer(f"❌ Сесію '{session_name}' не знайдено")
            return

        try:
            self.db.set_admin(session_name, True)
            await message.answer(f"✅ Сесію '{session_name}' встановлено як адмін")

        except Exception as e:
            logger.error(f"Error setting admin: {e}")
            await message.answer(f"❌ Помилка: {str(e)}")

    async def cmd_cancel(self, message: Message, state: FSMContext):
        """Команда /cancel - скасувати поточну операцію"""
        if not self._is_admin(message.from_user.id):
            return

        user_id = message.from_user.id

        # Закриваємо тимчасовий клієнт якщо є
        if user_id in self.temp_clients:
            try:
                await self.temp_clients[user_id].disconnect()
                del self.temp_clients[user_id]
            except:
                pass

        await state.clear()

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Додати сесію")],
                [KeyboardButton(text="📋 Список сесій")],
            ],
            resize_keyboard=True
        )

        await message.answer("✅ Операцію скасовано", reply_markup=keyboard)

    async def start(self):
        """Запуск бота"""
        logger.info("Control Bot starting...")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        """Зупинка бота"""
        logger.info("Control Bot stopping...")
        await self.bot.session.close()
