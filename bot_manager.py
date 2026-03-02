import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.sessions import Session

from database import Database

logger = logging.getLogger(__name__)


class BotManager:
    """Manages multiple Telegram userbot clients"""

    def __init__(self, api_id: int, api_hash: str, db: Database, sessions_dir: str = "sessions"):
        """
        Initialize BotManager

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            db: Database instance
            sessions_dir: Directory containing session files
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.db = db
        self.sessions_dir = Path(sessions_dir)

        self.clients: List[TelegramClient] = []
        self.client_info: List[Dict] = []  # Stores metadata about each client
        self.admin_client: Optional[TelegramClient] = None

    async def load_sessions(self):
        """
        Load all session files from the sessions directory and initialize clients
        Uses database to determine roles and active status
        """
        # Create sessions directory if it doesn't exist
        self.sessions_dir.mkdir(exist_ok=True)

        # Get active sessions from database
        db_sessions = self.db.get_all_sessions(active_only=True)

        if not db_sessions:
            logger.warning("No active sessions found in database")

            # Check if there are session files without DB records
            session_files = list(self.sessions_dir.glob("*.session"))
            if session_files:
                logger.info(f"Found {len(session_files)} session files without DB records")
                logger.info("Run migration or add sessions through control bot")
            return

        logger.info(f"Loading {len(db_sessions)} session(s) from database")

        for db_session in db_sessions:
            session_name = db_session['session_name']
            session_path = str(self.sessions_dir / session_name)
            session_file = Path(f"{session_path}.session")

            # Check if session file exists
            if not session_file.exists():
                logger.warning(f"Session file not found for {session_name}, skipping")
                continue

            try:
                # Create client with file-based session
                client = TelegramClient(
                    session_path,
                    self.api_id,
                    self.api_hash,
                    device_model="IBotServe",
                    system_version="1.0"
                )

                # Connect and get user info
                await client.connect()

                if not await client.is_user_authorized():
                    logger.warning(f"Session {session_name} is not authorized, skipping")
                    await client.disconnect()
                    continue

                # Get user information
                me = await client.get_me()
                user_id = me.id
                username = me.username or "No username"
                first_name = me.first_name or "Unknown"
                last_name = me.last_name or ""
                phone = me.phone or ""

                # Update database with fresh info
                self.db.update_session(
                    session_name=session_name,
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone
                )

                # Store client
                self.clients.append(client)
                is_admin = bool(db_session['is_admin'])

                client_data = {
                    "client": client,
                    "session_name": session_name,
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "is_admin": is_admin
                }

                self.client_info.append(client_data)

                # Set admin client
                if is_admin:
                    self.admin_client = client
                    logger.info(f"Admin client set: {first_name} (@{username})")

                logger.info(
                    f"Loaded client: {first_name} (@{username}) - "
                    f"{'ADMIN' if is_admin else 'USER'}"
                )

            except Exception as e:
                logger.error(f"Failed to load session {session_name}: {e}")

        if not self.clients:
            raise RuntimeError("No valid client sessions loaded")

        if not self.admin_client:
            logger.warning("No admin session found. Using first client as admin.")
            self.admin_client = self.clients[0]
            self.client_info[0]["is_admin"] = True
            # Update in database
            self.db.set_admin(self.client_info[0]["session_name"], True)

        logger.info(f"Successfully loaded {len(self.clients)} client(s)")

    def get_non_admin_clients(self) -> List[TelegramClient]:
        """
        Get all non-admin clients

        Returns:
            List of non-admin TelegramClient instances
        """
        return [
            info["client"]
            for info in self.client_info
            if not info["is_admin"]
        ]

    def get_all_clients(self) -> List[TelegramClient]:
        """
        Get all clients including admin

        Returns:
            List of all TelegramClient instances
        """
        return self.clients

    def get_client_by_id(self, user_id: int) -> Optional[TelegramClient]:
        """
        Get client by user ID

        Args:
            user_id: Telegram user ID

        Returns:
            TelegramClient or None if not found
        """
        for info in self.client_info:
            if info["user_id"] == user_id:
                return info["client"]
        return None

    async def disconnect_all(self):
        """Disconnect all clients"""
        for client in self.clients:
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")

        logger.info("All clients disconnected")
