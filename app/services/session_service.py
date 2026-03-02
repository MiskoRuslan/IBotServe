import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()


class SessionService:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)

    def get_session_files(self) -> List[Path]:
        """Отримати всі .session файли з папки sessions"""
        if not self.sessions_dir.exists():
            return []

        return list(self.sessions_dir.glob("*.session"))

    def read_session_info(self, session_path: Path) -> Optional[Dict[str, str]]:
        """
        Прочитати інформацію з Telethon session файлу (SQLite)

        Returns:
            Dict з phone та/або username, або None якщо не вдалось прочитати
        """
        try:
            conn = sqlite3.connect(str(session_path))
            cursor = conn.cursor()

            # Спробувати отримати дані з таблиці sessions
            cursor.execute("SELECT * FROM sessions LIMIT 1")
            row = cursor.fetchone()

            info = {}

            if row:
                # Telethon зберігає dc_id, server_address, port, auth_key
                # Нам потрібен номер телефону - він зазвичай в назві файлу
                session_name = session_path.stem

                # Якщо в назві файлу є номер (починається з +)
                if session_name.startswith('+') or session_name[0].isdigit():
                    # Завжди зберігаємо як строку, додаємо + якщо немає
                    phone = session_name if session_name.startswith('+') else f'+{session_name}'
                    info['phone_number'] = phone
                else:
                    info['username'] = session_name

            # Спробувати знайти entity (користувача)
            try:
                cursor.execute("SELECT id, hash, username, phone FROM entities WHERE id > 0 LIMIT 1")
                entity_row = cursor.fetchone()

                if entity_row and len(entity_row) >= 4:
                    if entity_row[3]:  # phone - конвертуємо в строку
                        phone = str(entity_row[3])
                        # Додаємо + якщо немає
                        if not phone.startswith('+'):
                            phone = f'+{phone}'
                        info['phone_number'] = phone
                    if entity_row[2]:  # username
                        info['username'] = str(entity_row[2])
            except sqlite3.OperationalError:
                # Таблиця entities може не існувати або мати іншу структуру
                pass

            conn.close()

            # Якщо не знайшли інформацію, використовуємо назву файлу
            if not info:
                session_name = session_path.stem
                # Перевіряємо чи це номер телефону
                if session_name.startswith('+') or session_name[0].isdigit():
                    phone = session_name if session_name.startswith('+') else f'+{session_name}'
                    info['phone_number'] = phone
                else:
                    info['username'] = session_name

            return info

        except Exception as e:
            print(f"Error reading session {session_path}: {e}")
            # Повертаємо базову інформацію з назви файлу
            session_name = session_path.stem
            if session_name.startswith('+') or (session_name and session_name[0].isdigit()):
                phone = session_name if session_name.startswith('+') else f'+{session_name}'
                return {'phone_number': phone}
            else:
                return {'username': session_name}

    def get_all_sessions_info(self) -> List[Dict[str, Optional[str]]]:
        """
        Отримати інформацію про всі session файли

        Returns:
            List[Dict] з phone_number та/або username для кожної сесії
        """
        session_files = self.get_session_files()
        sessions_info = []

        for session_file in session_files:
            info = self.read_session_info(session_file)
            if info:
                sessions_info.append(info)

        return sessions_info

    async def get_all_sessions_info_via_telethon(self) -> List[Dict[str, Optional[str]]]:
        """
        Отримати інформацію про всі session файли через Telethon API
        Підключається до кожної сесії та отримує реальні дані від Telegram

        Returns:
            List[Dict] з name, phone_number та username для кожної сесії
        """
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')

        if not api_id or not api_hash:
            raise ValueError("API_ID та API_HASH мають бути встановлені в .env файлі")

        session_files = self.get_session_files()
        sessions_info = []

        for session_file in session_files:
            try:
                # Створити клієнт для цієї сесії
                # session_file.stem - це ім'я файлу без розширення
                session_path = str(session_file.with_suffix(''))

                client = TelegramClient(session_path, api_id, api_hash)

                await client.connect()

                # Перевірити чи авторизований
                if not await client.is_user_authorized():
                    print(f"Сесія {session_file.name} не авторизована, пропускаємо")
                    await client.disconnect()
                    continue

                # Отримати інформацію про користувача
                me = await client.get_me()

                info = {}

                # Ім'я (first_name + last_name)
                name_parts = []
                if me.first_name:
                    name_parts.append(me.first_name)
                if me.last_name:
                    name_parts.append(me.last_name)

                if name_parts:
                    info['name'] = ' '.join(name_parts)

                # Username (без @)
                if me.username:
                    info['username'] = me.username

                # Номер телефону (з +)
                if me.phone:
                    phone = me.phone if me.phone.startswith('+') else f'+{me.phone}'
                    info['phone_number'] = phone

                sessions_info.append(info)

                await client.disconnect()

            except Exception as e:
                print(f"Помилка при отриманні інформації з сесії {session_file.name}: {e}")
                # Якщо виникла помилка, спробувати отримати базову інформацію з SQLite
                fallback_info = self.read_session_info(session_file)
                if fallback_info:
                    sessions_info.append(fallback_info)
                continue

        return sessions_info
