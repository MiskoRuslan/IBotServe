"""
Скрипт для створення нових Telegram сесій для userbot-ів
"""
import os
import sys
from pathlib import Path
from telethon.sync import TelegramClient
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

def create_session():
    """Створює нову Telegram сесію"""

    # Перевіряємо наявність API credentials
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')

    if not api_id or not api_hash:
        print("❌ Помилка: API_ID або API_HASH не знайдені в .env файлі")
        print("   Створіть .env файл на основі .env.example і заповніть його")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ Помилка: API_ID має бути числом")
        sys.exit(1)

    # Запитуємо ім'я сесії
    print("\n" + "="*60)
    print("Створення нової Telegram сесії")
    print("="*60)
    print()

    session_name = input("Введіть ім'я сесії (без .session): ").strip()

    if not session_name:
        print("❌ Ім'я сесії не може бути порожнім")
        sys.exit(1)

    # Створюємо папку sessions якщо не існує
    sessions_dir = Path('sessions')
    sessions_dir.mkdir(exist_ok=True)

    session_path = sessions_dir / session_name

    # Перевіряємо чи існує вже така сесія
    if (sessions_dir / f"{session_name}.session").exists():
        overwrite = input(f"⚠️  Сесія '{session_name}' вже існує. Перезаписати? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Операція скасована")
            sys.exit(0)

    print(f"\n📱 Створюємо сесію '{session_name}'...")
    print("   Вам буде запропоновано ввести номер телефону та код підтвердження")
    print()

    try:
        # Створюємо клієнт
        client = TelegramClient(
            str(session_path),
            api_id,
            api_hash,
            device_model="IBotServe",
            system_version="1.0"
        )

        # Запускаємо авторизацію
        client.start()

        # Отримуємо інформацію про користувача
        me = client.get_me()

        print()
        print("="*60)
        print("✅ Сесія успішно створена!")
        print("="*60)
        print(f"   Ім'я: {me.first_name or 'N/A'} {me.last_name or ''}")
        print(f"   Username: @{me.username or 'немає'}")
        print(f"   ID: {me.id}")
        print(f"   Телефон: {me.phone or 'N/A'}")
        print(f"   Файл: sessions/{session_name}.session")
        print("="*60)
        print()

        # Відключаємось
        client.disconnect()

        # Питаємо чи потрібно створити ще одну сесію
        another = input("Створити ще одну сесію? (y/n): ").strip().lower()
        if another == 'y':
            print()
            create_session()

    except KeyboardInterrupt:
        print("\n\n⚠️  Операція скасована користувачем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Помилка при створенні сесії: {e}")
        sys.exit(1)


def main():
    """Головна функція"""
    try:
        create_session()
    except KeyboardInterrupt:
        print("\n\n👋 До побачення!")
    except Exception as e:
        print(f"\n❌ Критична помилка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
