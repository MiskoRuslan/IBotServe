"""
Модуль для роботи з базою даних SQLite
Зберігає інформацію про сесії, ролі та налаштування
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class Database:
    """Клас для роботи з базою даних"""

    def __init__(self, db_path: str = "ibotserve.db"):
        """
        Ініціалізація бази даних

        Args:
            db_path: Шлях до файлу бази даних
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Створює таблиці якщо їх не існує"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Таблиця сесій
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT UNIQUE NOT NULL,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Таблиця для тимчасових даних авторизації
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                session_name TEXT NOT NULL,
                phone_code_hash TEXT,
                phone TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # Таблиця налаштувань
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def add_session(
        self,
        session_name: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        is_admin: bool = False,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Додає нову сесію в БД

        Args:
            session_name: Ім'я файлу сесії
            user_id: Telegram user ID
            username: Username
            first_name: Ім'я
            last_name: Прізвище
            phone: Номер телефону
            is_admin: Чи є адміністратором
            metadata: Додаткові метадані (JSON)

        Returns:
            ID доданої сесії
        """
        cursor = self.conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        try:
            cursor.execute("""
                INSERT INTO sessions (
                    session_name, user_id, username, first_name, last_name,
                    phone, is_admin, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_name, user_id, username, first_name, last_name,
                phone, is_admin, metadata_json
            ))

            self.conn.commit()
            logger.info(f"Session added to database: {session_name}")
            return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            logger.error(f"Session already exists: {session_name}")
            raise ValueError(f"Session {session_name} already exists") from e

    def update_session(
        self,
        session_name: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[Dict] = None
    ):
        """Оновлює інформацію про сесію"""
        cursor = self.conn.cursor()

        updates = []
        params = []

        if user_id is not None:
            updates.append("user_id = ?")
            params.append(user_id)

        if username is not None:
            updates.append("username = ?")
            params.append(username)

        if first_name is not None:
            updates.append("first_name = ?")
            params.append(first_name)

        if last_name is not None:
            updates.append("last_name = ?")
            params.append(last_name)

        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)

        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(is_admin)

        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(session_name)

        query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_name = ?"
        cursor.execute(query, params)
        self.conn.commit()

        logger.info(f"Session updated: {session_name}")

    def get_session(self, session_name: str) -> Optional[Dict]:
        """Отримує дані про сесію по імені"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_name = ?", (session_name,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all_sessions(self, active_only: bool = True) -> List[Dict]:
        """
        Отримує всі сесії

        Args:
            active_only: Тільки активні сесії

        Returns:
            Список сесій
        """
        cursor = self.conn.cursor()

        if active_only:
            cursor.execute("SELECT * FROM sessions WHERE is_active = 1")
        else:
            cursor.execute("SELECT * FROM sessions")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_admin_session(self) -> Optional[Dict]:
        """Отримує адмін-сесію"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE is_admin = 1 AND is_active = 1 LIMIT 1")
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def delete_session(self, session_name: str):
        """Видаляє сесію з БД"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_name = ?", (session_name,))
        self.conn.commit()
        logger.info(f"Session deleted from database: {session_name}")

    def set_admin(self, session_name: str, is_admin: bool = True):
        """Встановлює/знімає адмін-роль для сесії"""
        # Якщо встановлюємо нового адміна, спочатку знімаємо зі всіх інших
        if is_admin:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE sessions SET is_admin = 0")

        self.update_session(session_name, is_admin=is_admin)
        logger.info(f"Admin status updated for {session_name}: {is_admin}")

    # Методи для роботи з тимчасовими даними авторизації

    def create_auth_session(
        self,
        telegram_user_id: int,
        session_name: str,
        phone: str,
        phone_code_hash: Optional[str] = None
    ) -> int:
        """Створює запис для процесу авторизації"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO auth_sessions (
                telegram_user_id, session_name, phone, phone_code_hash, status
            ) VALUES (?, ?, ?, ?, 'pending')
        """, (telegram_user_id, session_name, phone, phone_code_hash))

        self.conn.commit()
        return cursor.lastrowid

    def get_auth_session(self, telegram_user_id: int) -> Optional[Dict]:
        """Отримує активну авторизаційну сесію користувача"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM auth_sessions
            WHERE telegram_user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (telegram_user_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def update_auth_session(
        self,
        auth_session_id: int,
        phone_code_hash: Optional[str] = None,
        status: Optional[str] = None
    ):
        """Оновлює дані авторизаційної сесії"""
        cursor = self.conn.cursor()

        updates = []
        params = []

        if phone_code_hash is not None:
            updates.append("phone_code_hash = ?")
            params.append(phone_code_hash)

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return

        params.append(auth_session_id)
        query = f"UPDATE auth_sessions SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, params)
        self.conn.commit()

    def delete_auth_session(self, telegram_user_id: int):
        """Видаляє авторизаційну сесію"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM auth_sessions WHERE telegram_user_id = ?", (telegram_user_id,))
        self.conn.commit()

    # Методи для роботи з налаштуваннями

    def set_setting(self, key: str, value: str):
        """Зберігає налаштування"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        self.conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        """Отримує налаштування"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return None

    def close(self):
        """Закриває з'єднання з БД"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
