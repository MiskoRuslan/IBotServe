import os
import logging
from typing import List, Dict
import aiohttp

logger = logging.getLogger(__name__)


class GrokClient:
    """Async client for Grok AI API"""

    def __init__(self, api_key: str, api_url: str):
        """
        Initialize Grok AI client

        Args:
            api_key: Grok API key
            api_url: Grok API endpoint URL
        """
        self.api_key = api_key
        self.api_url = api_url
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def generate_message(self, context: List[Dict[str, str]], prompt: str) -> str:
        """
        Generate a message based on conversation context and system prompt

        Args:
            context: List of message dicts with 'role' and 'content' keys
                     Example: [{"role": "user", "content": "Hello"}, ...]
            prompt: System prompt defining the AI behavior

        Returns:
            Generated message string
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Build messages array with system prompt
        messages = [{"role": "system", "content": prompt}]
        messages.extend(context)

        payload = {
            "messages": messages,
            "model": "grok-beta",
            "temperature": 0.8,
            "max_tokens": 200
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Extract message from response
                message = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not message:
                    logger.warning("Empty response from Grok API, using fallback")
                    return self._fallback_message(context)

                return message.strip()

        except aiohttp.ClientError as e:
            logger.error(f"Grok API request failed: {e}")
            return self._fallback_message(context)
        except Exception as e:
            logger.error(f"Unexpected error in Grok client: {e}")
            return self._fallback_message(context)

    def _fallback_message(self, context: List[Dict[str, str]]) -> str:
        """
        Generate a simple fallback message when API is unavailable

        Args:
            context: Conversation context

        Returns:
            Fallback message string
        """
        fallback_messages = [
            "Interesting point!",
            "I agree with that.",
            "That makes sense.",
            "Good observation.",
            "What do you think about this?",
            "Let me think about that...",
            "That's a valid perspective."
        ]

        # Simple hash-based selection for consistency
        if context:
            last_msg = context[-1].get("content", "")
            index = hash(last_msg) % len(fallback_messages)
            return fallback_messages[index]

        return fallback_messages[0]
