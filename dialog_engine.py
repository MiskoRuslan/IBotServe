import asyncio
import random
import logging
from typing import List, Dict, Optional
from collections import deque
from telethon import TelegramClient, events
from telethon.tl.types import Message

from ai_client import GrokClient
from bot_manager import BotManager
from media_handler import MediaHandler

logger = logging.getLogger(__name__)


class DialogEngine:
    """Manages conversation flow and message generation"""

    def __init__(
        self,
        bot_manager: BotManager,
        ai_client: GrokClient,
        group_id: int,
        prompt: str,
        min_delay: int,
        max_delay: int,
        max_context: int
    ):
        """
        Initialize DialogEngine

        Args:
            bot_manager: BotManager instance with loaded clients
            ai_client: GrokClient instance for message generation
            group_id: Target Telegram group ID
            prompt: System prompt for AI behavior
            min_delay: Minimum seconds between messages
            max_delay: Maximum seconds between messages
            max_context: Maximum number of messages to keep in context
        """
        self.bot_manager = bot_manager
        self.ai_client = ai_client
        self.group_id = group_id
        self.prompt = prompt
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_context = max_context

        # Context buffer - stores recent messages
        self.context_buffer: deque = deque(maxlen=max_context)

        # Track last sender to avoid consecutive messages from same bot
        self.last_sender_id: Optional[int] = None

        # Media handler
        self.media_handler = MediaHandler()

        # Flag to control the run loop
        self.running = False

    async def start_listening(self):
        """Start listening to group messages to populate context"""
        admin_client = self.bot_manager.admin_client

        @admin_client.on(events.NewMessage(chats=self.group_id))
        async def message_handler(event: events.NewMessage.Event):
            """Handle incoming messages and add to context"""
            message: Message = event.message

            # Skip service messages
            if not message.text:
                return

            sender = await message.get_sender()
            sender_name = getattr(sender, 'first_name', 'Unknown')

            # Add to context buffer
            self.context_buffer.append({
                "role": "user",
                "content": f"{sender_name}: {message.text}"
            })

            logger.info(f"Added to context: {sender_name}: {message.text[:50]}...")

        logger.info(f"Started listening to group {self.group_id}")

    def _pick_next_client(self) -> Optional[TelegramClient]:
        """
        Pick next random bot client, excluding the last sender

        Returns:
            TelegramClient or None if no suitable client found
        """
        available_clients = [
            info["client"]
            for info in self.bot_manager.client_info
            if info["user_id"] != self.last_sender_id
        ]

        if not available_clients:
            # Fallback: use any client if all were last sender (shouldn't happen normally)
            available_clients = self.bot_manager.get_all_clients()

        if not available_clients:
            return None

        return random.choice(available_clients)

    async def _simulate_typing(self, client: TelegramClient, duration: int = 3):
        """
        Simulate typing action in the chat

        Args:
            client: TelegramClient to use for typing
            duration: Typing duration in seconds
        """
        try:
            async with client.action(self.group_id, 'typing'):
                await asyncio.sleep(duration)
        except Exception as e:
            logger.error(f"Error simulating typing: {e}")

    async def _send_message(self, client: TelegramClient, text: str):
        """
        Send a message using the specified client

        Args:
            client: TelegramClient to send message from
            text: Message text to send
        """
        try:
            # Simulate typing before sending
            typing_duration = min(len(text) // 20, 5)  # Max 5 seconds
            await self._simulate_typing(client, typing_duration)

            # Send message
            await client.send_message(self.group_id, text)

            # Get sender info
            me = await client.get_me()
            sender_name = me.first_name
            self.last_sender_id = me.id

            logger.info(f"Sent message as {sender_name}: {text[:50]}...")

            # Add own message to context
            self.context_buffer.append({
                "role": "assistant",
                "content": text
            })

        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def _generate_and_send(self):
        """Generate a message using AI and send it"""
        # Pick next client
        client = self._pick_next_client()
        if not client:
            logger.error("No available clients to send message")
            return

        # Convert context buffer to list for AI
        context = list(self.context_buffer)

        if not context:
            logger.warning("Context is empty, skipping message generation")
            return

        try:
            # Generate message
            logger.info("Generating message from AI...")
            message = await self.ai_client.generate_message(context, self.prompt)

            if message:
                # Send the message
                await self._send_message(client, message)
            else:
                logger.warning("AI returned empty message")

        except Exception as e:
            logger.error(f"Error generating/sending message: {e}")

    async def run(self):
        """
        Main loop - continuously generate and send messages with random delays
        """
        self.running = True
        logger.info("Dialog engine started")

        # Start listening to messages
        await self.start_listening()

        # Wait a bit to collect initial context
        logger.info("Collecting initial context...")
        await asyncio.sleep(10)

        while self.running:
            try:
                # Random delay between messages
                delay = random.randint(self.min_delay, self.max_delay)
                logger.info(f"Waiting {delay} seconds before next message...")
                await asyncio.sleep(delay)

                # Generate and send message
                await self._generate_and_send()

            except asyncio.CancelledError:
                logger.info("Dialog engine cancelled")
                break
            except Exception as e:
                logger.error(f"Error in dialog engine loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

        logger.info("Dialog engine stopped")

    def stop(self):
        """Stop the dialog engine"""
        self.running = False
        logger.info("Stopping dialog engine...")
