# IBotServe

Modern Telegram userbot management platform with AI-powered conversations.

## Features

- **Userbot Management** - Manage multiple Telegram userbots from a single dashboard
- **AI Conversations** - Generate natural conversations using Grok AI
- **Group Management** - Create and manage Telegram groups with automated interactions
- **Style Customization** - Configure message styles, language, emojis, and slang for each bot
- **Message Listening** - Listen to trusted users and trigger automated responses
- **Sticker Support** - Upload and manage global stickers with emotion-based selection
- **Photo Sharing** - Automatic photo integration via Unsplash
- **Real-time Responses** - Bots reply to user messages and continue conversations naturally

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI - Modern async web framework
- Telethon - Telegram MTProto API library
- SQLAlchemy - Async ORM
- PostgreSQL - Database
- Alembic - Database migrations
- Grok AI - Natural language generation

**Frontend:**
- Vanilla JavaScript (ES6+)
- Modern CSS with dark theme
- Responsive design

**Infrastructure:**
- Docker & Docker Compose
- Uvicorn ASGI server

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Telegram API credentials (API_ID, API_HASH)
- Grok API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IBotServe
```

2. Create `.env` file:
```env
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash

# Grok AI
GROK_API_KEY=your_grok_api_key

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/ibotserve
```

3. Start the application:
```bash
docker-compose up -d
```

4. Access the admin panel:
```
http://localhost:8000
```

### Initial Setup

1. **Add Session Files** - Place your Telegram session files (`.session`) in the `sessions/` folder
2. **Update Data** - Click "Update Data" to import userbots from session files
3. **Create Groups** - Use "Create Group" to set up Telegram groups
4. **Configure Bots** - Click on userbots to customize their style settings
5. **Upload Stickers** - Use "Upload Stickers" to add TGS stickers (optional)
6. **Start Listeners** - Click "Start Listeners" to activate message monitoring

## Project Structure

```
IBotServe/
├── app/
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   │   ├── conversation_service.py
│   │   ├── message_listener.py
│   │   ├── grok_service.py
│   │   └── sticker_service.py
│   └── main.py
├── database/
│   ├── config.py         # Database configuration
│   └── managers/         # Database managers
├── models/               # SQLAlchemy models
├── alembic/             # Database migrations
├── static/              # CSS, JS, stickers
├── templates/           # HTML templates
├── sessions/            # Telegram session files
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Configuration

### Bot Style Settings

Each userbot can be customized with:
- **Gender** - Male/Female
- **Language** - Ukrainian/Russian
- **Message Length** - Short/Medium/Long/Any
- **Emoji Probability** - 0-100%
- **Slang Options** - Youth slang, illiterate slang
- **Special Features** - Typos, ASCII emoticons, profanity
- **Media** - Photos (10%), Stickers (15%)

### Group Settings

- **Global Prompt** - Instructions for all bots in the group
- **Member Prompts** - Individual instructions per bot
- **Context Messages** - Number of recent messages for AI context (default: 10)
- **Delay Range** - Min/Max delay between messages (default: 10-40s)

## API Documentation

Once running, visit:
- **API Docs** - http://localhost:8000/docs
- **Admin Panel** - http://localhost:8000
