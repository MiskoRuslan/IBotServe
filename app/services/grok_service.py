import os
import aiohttp
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class GrokService:

    def __init__(self):
        self.api_key = os.getenv('GROK_API_KEY')
        self.api_url = os.getenv('GROK_API_URL')

        if not self.api_key or not self.api_url:
            raise ValueError("GROK_API_KEY and GROK_API_URL must be set in .env file")

        self.model = "grok-4-1-fast-non-reasoning"

    async def generate_conversation_starter(
        self,
        trigger_message: str,
        global_prompt: Optional[str] = None,
        member_prompt: Optional[str] = None,
        custom_system_prompt: Optional[str] = None
    ) -> str:
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            # Build system prompt
            system_parts = [
                "You are a helpful assistant that generates natural, human-like conversation starters.",
                "Your task is to create a casual question or statement that a real person would write.",
                "The message should be simple, conversational, and look completely natural.",
                "DO NOT use formal language, overly complex sentences, or AI-like patterns.",
                "Examples of good messages:",
                "- 'Як зараз справи з транзитом нафти в Америці?'",
                "- 'Порадьте хороший корм для мого спаніеля'",
                "- 'Хто знає де купити якісні шини для джипа?'",
                "- 'Цікаво, чи варто зараз інвестувати в біткоїн?'",
            ]

            if global_prompt:
                system_parts.append(f"\nGroup context: {global_prompt}")

            if member_prompt:
                system_parts.append(f"\nYour personality/style: {member_prompt}")

            system_prompt = "\n".join(system_parts)

        user_prompt = f"""Based on this topic/instruction: "{trigger_message}"

Generate ONE simple, natural question or statement that a real person would write in a chat.
Keep it casual and conversational. Write in the same language as the topic.
DO NOT add explanations, just return the message itself."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Grok API error: {response.status} - {error_text}")

                    data = await response.json()

            generated_text = data['choices'][0]['message']['content'].strip()

            if generated_text.startswith('"') and generated_text.endswith('"'):
                generated_text = generated_text[1:-1]
            if generated_text.startswith("'") and generated_text.endswith("'"):
                generated_text = generated_text[1:-1]

            return generated_text

        except Exception as e:
            print(f"[GrokService] Error generating message: {e}")
            raise

grok_service = GrokService()
