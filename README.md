# IBotServe

Telegram Userbot Management Service

## Структура проекту

```
IBotServe/
├── app/                    # FastAPI додаток
│   ├── __init__.py
│   └── main.py            # Головний файл з роутами
├── database/              # Конфігурація бази даних
│   ├── __init__.py
│   └── config.py          # SQLAlchemy engine та сесії
├── models/                # Моделі бази даних
│   ├── __init__.py
│   ├── base.py           # Базова модель
│   ├── groups.py         # Модель груп
│   ├── userbots.py       # Модель юзерботів
│   └── members.py        # Зв'язна таблиця
├── sessions/             # Сесії Telegram (автоматично створюються)
├── venv/                 # Віртуальне оточення Python
├── .env                  # Змінні оточення (не в git)
├── .env.example          # Приклад змінних оточення
├── .gitignore
├── requirements.txt      # Python залежності
├── run.py               # Файл запуску сервера
├── Dockerfile           # Docker образ для додатку
└── docker-compose.yml   # Оркестрація контейнерів
```

## База даних

### Таблиці:

**groups**
- `id` (UUID) - первинний ключ
- `name` (String) - назва групи
- `created_at` (DateTime) - дата створення

**userbots**
- `id` (UUID) - первинний ключ
- `phone_number` (String, optional) - номер телефону
- `username` (String, optional) - username
- `created_at` (DateTime) - дата створення

**members** (зв'язна таблиця)
- `id` (UUID) - первинний ключ
- `userbot_id` (UUID) - зовнішній ключ до userbots
- `group_id` (UUID) - зовнішній ключ до groups
- `created_at` (DateTime) - дата створення

### Підключення до бази даних

#### Через командний рядок (psql)

Після запуску Docker контейнерів, підключіться до БД:

```bash
docker-compose exec db psql -U postgres -d ibotserve
```

Корисні SQL команди:
```sql
-- Переглянути всі таблиці
\dt

-- Описати структуру таблиці
\d groups
\d userbots
\d members

-- Вибірка даних
SELECT * FROM groups;
SELECT * FROM userbots;
SELECT * FROM members;

-- Вийти з psql
\q
```

#### Через GUI клієнти (DBeaver, pgAdmin, DataGrip)

**Параметри підключення:**
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `ibotserve`
- **Username:** `postgres`
- **Password:** `postgres`

**Приклад для DBeaver:**
1. Створіть нове підключення PostgreSQL
2. Вкажіть параметри вище
3. Тестуйте підключення
4. Збережіть і підключайтеся

**Приклад для pgAdmin:**
1. Add New Server
2. General → Name: `IBotServe`
3. Connection:
   - Host: `localhost`
   - Port: `5432`
   - Database: `ibotserve`
   - Username: `postgres`
   - Password: `postgres`
4. Save і підключайтеся

**Connection String:**
```
postgresql://postgres:postgres@localhost:5432/ibotserve
```

## Docker

Проект використовує Docker для розгортання. Складається з двох контейнерів:
- **db** - PostgreSQL 16 база даних
- **app** - FastAPI додаток

### Запуск через Docker

1. Створіть файл `.env` на основі `.env.example`:
```bash
cp .env.example .env
```

2. Відредагуйте `.env` та заповніть необхідні дані:
```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
CONTROL_BOT_TOKEN=your_bot_token_here
GROK_API_KEY=your_grok_api_key_here
GROK_API_URL=https://api.x.ai/v1/chat/completions
```

3. Запустіть контейнери:
```bash
docker-compose up -d
```

4. Перевірте статус:
```bash
docker-compose ps
```

5. Переглянути логи:
```bash
docker-compose logs -f app
```

6. Зупинити контейнери:
```bash
docker-compose down
```

7. Зупинити та видалити дані (включно з БД):
```bash
docker-compose down -v
```

### Корисні команди

**Перезапуск тільки app контейнера:**
```bash
docker-compose restart app
```

**Перебудувати образ після змін коду:**
```bash
docker-compose up -d --build
```

**Підключитись до БД:**
```bash
docker-compose exec db psql -U postgres -d ibotserve
```

**Виконати команду в app контейнері:**
```bash
docker-compose exec app bash
```

## Веб інтерфейс (Admin Panel)

Після запуску проекту, адмін панель доступна за адресою: `http://localhost:8000`

### Функціонал:

**1. Головна сторінка** - дашборд з темним дизайном
   - Статистика: кількість UserBots, Session файлів, Груп
   - Кнопка "Update Data" для синхронізації sessions з БД

**2. Лівий Sidebar**
   - Список всіх UserBots з бази даних
   - Відображає username або номер телефону
   - Автоматично оновлюється після Update Data

**3. Update Data**
   - Сканує папку `sessions/` на наявність `.session` файлів
   - Читає інформацію з Telethon session файлів (SQLite)
   - Додає нові UserBots в таблицю `userbots`
   - Пропускає вже існуючі записи
   - Показує результат: скільки додано, скільки пропущено

### Як використовувати:

1. Розмістіть ваші Telethon `.session` файли в папку `sessions/`
2. Відкрийте `http://localhost:8000` в браузері
3. Натисніть кнопку "Update Data"
4. Перегляньте результат та оновлений список UserBots в sidebar

## API Endpoints

### Web Routes

**GET /**
Головна сторінка адмін панелі (HTML)

### API Routes

**GET /api/userbots**
Отримати список всіх UserBots з БД

**Відповідь:**
```json
{
  "userbots": [
    {
      "id": "uuid",
      "phone_number": "+380123456789",
      "username": "username",
      "created_at": "2026-03-02T12:00:00"
    }
  ]
}
```

**GET /api/stats**
Отримати статистику

**Відповідь:**
```json
{
  "total_userbots": 5,
  "total_sessions": 10,
  "total_groups": 3
}
```

**POST /api/update-data**
Синхронізувати session файли з БД

**Відповідь:**
```json
{
  "added": 5,
  "skipped": 2,
  "total_sessions": 7
}
```

## Локальна розробка (без Docker)

1. Створіть віртуальне оточення:
```bash
python -m venv venv
```

2. Активуйте:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Запустіть PostgreSQL локально та створіть базу даних `ibotserve`

5. Налаштуйте `.env` з DATABASE_URL для локальної БД:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ibotserve
```

6. Запустіть сервер:
```bash
python run.py
```

Сервер буде доступний на `http://localhost:8000`

## Технології

- **FastAPI** - веб фреймворк
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL** - база даних
- **asyncpg** - асинхронний драйвер PostgreSQL
- **Uvicorn** - ASGI сервер
- **Docker & Docker Compose** - контейнеризація
- **Telethon** - Telegram userbot бібліотека
- **Aiogram** - Telegram bot бібліотека
