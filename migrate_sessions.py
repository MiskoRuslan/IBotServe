"""
Скрипт для міграції існуючих .session файлів в базу даних
Використовуйте якщо у вас вже є сесії в папці sessions/
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

from database import Database


async def migrate_sessions():
    """Міграція всіх сесій з папки sessions/ в базу даних"""

    print("=" * 60)
    print("Міграція існуючих Telegram сесій в базу даних")
    print("=" * 60)
    print()

    # Завантажуємо env
    load_dotenv()

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')

    if not api_id or not api_hash:
        print("❌ Помилка: API_ID або API_HASH не знайдені в .env")
        sys.exit(1)

    api_id = int(api_id)

    # Ініціалізуємо БД
    db = Database()

    # Папка з сесіями
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        print("❌ Папка sessions/ не знайдена")
        sys.exit(1)

    # Знаходимо всі .session файли
    session_files = list(sessions_dir.glob("*.session"))

    if not session_files:
        print("❌ Не знайдено .session файлів в папці sessions/")
        sys.exit(1)

    print(f"Знайдено {len(session_files)} файл(ів) сесій\n")

    migrated = 0
    skipped = 0
    errors = 0

    for session_file in session_files:
        session_name = session_file.stem
        session_path = str(sessions_dir / session_name)

        print(f"Обробка: {session_name}...", end=" ")

        # Перевірка чи вже існує в БД
        existing = db.get_session(session_name)
        if existing:
            print("⏭️  Вже в БД, пропускаємо")
            skipped += 1
            continue

        try:
            # Підключаємось до сесії
            client = TelegramClient(
                session_path,
                api_id,
                api_hash
            )

            await client.connect()

            if not await client.is_user_authorized():
                print("⚠️  Не авторизована, пропускаємо")
                await client.disconnect()
                skipped += 1
                continue

            # Отримуємо інформацію
            me = await client.get_me()

            # Додаємо в БД
            db.add_session(
                session_name=session_name,
                user_id=me.id,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name,
                phone=me.phone,
                is_admin=False
            )

            await client.disconnect()

            print(f"✅ Додано ({me.first_name})")
            migrated += 1

        except Exception as e:
            print(f"❌ Помилка: {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"Міграція завершена!")
    print(f"✅ Додано: {migrated}")
    print(f"⏭️  Пропущено: {skipped}")
    print(f"❌ Помилок: {errors}")
    print("=" * 60)
    print()

    if migrated > 0:
        print("Тепер потрібно встановити одну сесію як адмін:")
        print("1. Запустіть Control Bot: python main.py --control")
        print("2. Використайте команду: /set_admin <session_name>")
        print()

    db.close()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_sessions())
    except KeyboardInterrupt:
        print("\n\n⚠️  Операцію скасовано")
    except Exception as e:
        print(f"\n❌ Критична помилка: {e}")
        sys.exit(1)
