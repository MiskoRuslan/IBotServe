import asyncio
import random
from pathlib import Path
from typing import Dict, Optional, List
from uuid import UUID
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from sqlalchemy import select, desc
from database.config import async_session_maker
from models import Group, Member, ChatHistory, Userbot, MessageHistory
from app.services.grok_service import grok_service
import os
from dotenv import load_dotenv

load_dotenv()


class ConversationService:
    """Service for managing automatic conversations in groups"""

    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')

        # Track active conversations: group_id -> asyncio.Task
        self.active_conversations: Dict[str, asyncio.Task] = {}

        # Track clients for each group: group_id -> list of TelegramClient
        self.group_clients: Dict[str, List[TelegramClient]] = {}

        # Track last message sender per group: group_id -> userbot_id
        self.last_sender: Dict[str, UUID] = {}

        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH must be set in .env file")

    def _find_session_by_phone(self, phone: str) -> Optional[Path]:
        """Find session file by phone number"""
        phone_clean = phone.lstrip('+')
        for variant in [f'+{phone_clean}', phone_clean]:
            p = self.sessions_dir / f"{variant}.session"
            if p.exists():
                return p
        return None

    async def _get_recent_messages(
        self,
        group_id: UUID,
        limit: int
    ) -> List[ChatHistory]:
        """Get recent messages from chat history for context with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with async_session_maker() as db:
                    result = await db.execute(
                        select(ChatHistory)
                        .where(ChatHistory.group_id == group_id)
                        .order_by(desc(ChatHistory.created_at))
                        .limit(limit)
                    )
                    messages = result.scalars().all()
                    return list(reversed(messages))  # Return in chronological order

            except Exception as db_error:
                error_msg = str(db_error)
                if "database is locked" in error_msg.lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.3
                    print(f"[ConversationService] DB locked reading messages, retry {attempt + 1}/{max_retries} in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[ConversationService] Failed to read messages: {db_error}")
                    if attempt == max_retries - 1:
                        return []  # Return empty list on final failure instead of crashing

    def _find_unanswered_question(self, recent_messages: List[ChatHistory]) -> Optional[ChatHistory]:
        """
        Find a question from admin that needs an answer.
        Each question randomly needs 1-3 answers before being considered "answered".
        """
        if len(recent_messages) < 1:
            return None

        # Look at last 8 messages maximum
        messages_to_check = recent_messages[-8:] if len(recent_messages) > 8 else recent_messages

        # Find ALL questions (messages with "?")
        questions = [msg for msg in messages_to_check if '?' in msg.message]

        if not questions:
            return None

        # Prioritize the FIRST (oldest) unanswered question to keep conversation on topic
        # Each question needs a RANDOM number of answers (1-3) to feel more natural
        for question in questions:  # Check from oldest to newest
            question_index = recent_messages.index(question)
            messages_after_count = len(recent_messages) - question_index - 1

            # Use question ID as seed for consistent random number per question
            # This ensures the same question always needs the same number of answers
            random.seed(str(question.id))
            target_answers = random.randint(1, 3)
            random.seed()  # Reset seed to default

            print(f"[ConversationService] Question '{question.message[:50]}...' needs {target_answers} answers, has {messages_after_count}")

            # If question has fewer answers than target, it still needs attention
            if messages_after_count < target_answers:
                return question

        return None

    async def _generate_reply(
        self,
        userbot_id: UUID,
        group_id: UUID,
        global_prompt: str,
        member_prompt: str,
        recent_messages: List[ChatHistory],
        style_settings: dict = None,
        unanswered_question: Optional[ChatHistory] = None
    ) -> dict:
        """
        Generate a contextual reply for a member

        Returns:
            dict with 'message' (str) and 'reply_to' (telegram_message_id or None)
        """

        # Count messages in conversation
        message_count = len(recent_messages)

        # Build conversation context
        context_parts = [
            "You are participating in a group conversation.",
            "Your PRIMARY GOAL: Keep conversation DIVERSE and INTERESTING.",
            "Write in the same language as the conversation.",
        ]

        # PRIORITY: Answer unanswered questions first
        if unanswered_question:
            context_parts.append("\n" + "="*60)
            context_parts.append("⭐⭐⭐ HIGHEST PRIORITY TASK ⭐⭐⭐")
            context_parts.append("YOU MUST ANSWER THIS SPECIFIC QUESTION:")
            context_parts.append(f'❓ QUESTION: "{unanswered_question.message}"')
            context_parts.append("="*60)
            context_parts.append("\n🎯 YOUR ONLY TASK:")
            context_parts.append("Answer the EXACT TOPIC of the question above.")
            context_parts.append("If the question is about ENGINE (двигун), answer about ENGINE.")
            context_parts.append("If the question is about BRAKES (гальма), answer about BRAKES.")
            context_parts.append("If the question is about GAS (газ), answer about GAS.")
            context_parts.append("DO NOT talk about different topic!")
            context_parts.append("\n✅ HOW TO ANSWER:")
            context_parts.append("1. Read the question carefully - what is it asking about?")
            context_parts.append("2. Share YOUR experience with that EXACT topic")
            context_parts.append("3. Give specific advice, prices, contacts, or solutions")
            context_parts.append("4. Be helpful and conversational")
            context_parts.append("5. NO '?' symbols - you are ANSWERING, not asking!")
            context_parts.append("\n⛔ ABSOLUTELY FORBIDDEN:")
            context_parts.append("- Answering about DIFFERENT topic than asked")
            context_parts.append("- Asking a new question instead of answering")
            context_parts.append("- Changing the subject")
            context_parts.append("- Generic responses like 'good question' without actual answer")
            context_parts.append("\n📝 EXAMPLES:")
            context_parts.append("Question: 'У кого стукає двигун?' → GOOD: 'В мене стукав на W204, виявилось розтяг ланцюга, міняв за 8000 грн'")
            context_parts.append("Question: 'Де дешевше газ?' → GOOD: 'Я заправляюсь на окружній біля Києва, там 28 грн за літр'")
            context_parts.append("Question: 'Хто міняв гальма?' → GOOD: 'Я ставив Brembo минулого місяця, тепер гальмує м'якше'")
            context_parts.append("\nRemember: Answer THE QUESTION, not random topic!")
        else:
            # No unanswered questions - normal conversation flow
            context_parts.append("\n⛔ ABSOLUTE RULES:")
            context_parts.append("1. NEVER repeat questions/topics from previous messages")
            context_parts.append("2. NEVER ask variations of the same question (like 'а в Києві?', 'а в Харкові?' after someone asked about city)")
            context_parts.append("3. If topic becomes repetitive (same pattern 2+ times) - you MUST change topic immediately")
            context_parts.append("4. Each response must bring NEW value, not echo what was said")
            context_parts.append("5. Be human-like: creative, unpredictable, naturally changing subjects")

        # Add topic shift logic - only if no unanswered questions
        # EVERY 4 messages to allow conversation to develop
        should_shift_topic = (not unanswered_question and message_count > 0 and message_count % 4 == 0)

        if should_shift_topic:
            context_parts.append("\n🔄 MANDATORY TOPIC CHANGE - STOP CURRENT TOPIC NOW!")
            context_parts.append("\n⛔ FORBIDDEN:")
            context_parts.append("- Continuing discussion about what was just mentioned")
            context_parts.append("- Asking variations of previous questions (like 'а в [іншому місці]?')")
            context_parts.append("- Repeating patterns from recent messages")
            context_parts.append("\n✅ REQUIRED: Start COMPLETELY DIFFERENT topic:")
            context_parts.append("Option A: Ask NEW question about DIFFERENT subject (tech, news, experience, advice, etc.)")
            context_parts.append("Option B: Share personal story/opinion on UNRELATED topic")
            context_parts.append("Option C: Make observation/comment about something NEW")
            context_parts.append("\nTransitions: 'Ех, а...', 'Кстаті...', 'До речі...', 'Хлопці, а...'")
            if global_prompt:
                context_parts.append(f"Stay relevant to group theme: {global_prompt}")
            context_parts.append("\n⚠️ THIS IS NOT NEGOTIABLE - change topic NOW or conversation looks stupid!")
        else:
            # First message in cycle - respond naturally but prepare for topic change
            context_parts.append("\n💬 Respond naturally to current discussion. DON'T ask follow-up if someone already did.")

        if global_prompt:
            context_parts.append(f"\nGroup context: {global_prompt}")

        if member_prompt:
            context_parts.append(f"\nYour personality/style: {member_prompt}")

        # Add style settings to context
        # BUT if answering a question, style is SECONDARY to answering correctly
        if style_settings:
            if unanswered_question:
                context_parts.append("\n=== Style Requirements (secondary to answering the question) ===")
            else:
                context_parts.append("\n=== CRITICAL STYLE REQUIREMENTS (MUST FOLLOW EXACTLY) ===")

            # Punctuation - STRICT
            if not style_settings.get("use_punctuation", True):
                context_parts.append("⚠️ MANDATORY: Write WITHOUT any punctuation marks at all - no periods, commas, question marks, exclamation marks, nothing")
                context_parts.append("Example: 'так нормально все добре' instead of 'Так, нормально. Все добре!'")

            # Uppercase - STRICT
            if not style_settings.get("use_uppercase", True):
                context_parts.append("⚠️ MANDATORY: Write ONLY in lowercase letters - absolutely NO capital letters anywhere")
                context_parts.append("Example: 'привіт як справи' instead of 'Привіт, як справи?'")

            # Message length - STRICT
            length = style_settings.get("message_length", "medium")
            if length == "short":
                context_parts.append("⚠️ MANDATORY: Response must be VERY SHORT - maximum 5-15 words, one phrase only")
                context_parts.append("Example: 'та нормально все' or 'не знаю честно'")
            elif length == "long":
                context_parts.append("⚠️ MANDATORY: Response must be LONG - 3-5 sentences minimum, elaborate and detailed")
                context_parts.append("Example: Full paragraph with multiple thoughts and explanations")
            elif length == "medium":
                context_parts.append("Response should be MEDIUM length - 1-3 sentences")

            # Gender - VERY IMPORTANT
            gender = style_settings.get("gender", "male")
            if gender == "female":
                context_parts.append("\n⚠️ CRITICAL: You are a FEMALE person. Use feminine speech patterns:")
                context_parts.append("- Use feminine endings: 'я була', 'я зробила', 'я думала' (NOT 'я був', 'я зробив', 'я думав')")
                context_parts.append("- Use feminine adjectives: 'я рада', 'я здивована', 'я втомлена' (NOT 'радий', 'здивований', 'втомлений')")
                context_parts.append("- Write naturally as a woman would speak in casual conversation")
                context_parts.append("Examples: 'Дівчата, я вчора була в магазині...', 'Я так втомилася сьогодні', 'Подруга мені казала...'")
            else:
                context_parts.append("\n⚠️ CRITICAL: You are a MALE person. Use masculine speech patterns:")
                context_parts.append("- Use masculine endings: 'я був', 'я зробив', 'я думав'")
                context_parts.append("- Use masculine adjectives: 'я радий', 'я здивований', 'я втомлений'")
                context_parts.append("- Write naturally as a man would speak in casual conversation")

            # Profanity
            if style_settings.get("allow_profanity"):
                context_parts.append("You MAY use profanity when contextually appropriate (don't force it, but it's allowed)")
            else:
                context_parts.append("NEVER use profanity or curse words under any circumstances")

            # Photo/Image restrictions - CRITICAL
            context_parts.append("\n🚫 CRITICAL RESTRICTION: NEVER request photos or images!")
            context_parts.append("- FORBIDDEN phrases: 'скиньте фото', 'надішліть фотку', 'send photo', 'покажіть картинку', etc.")
            context_parts.append("- Do NOT ask to see pictures, images, screenshots, or any visual content")
            context_parts.append("- If someone mentions photos/images, respond with text only - DO NOT ask them to share it")
            context_parts.append("- You can TALK ABOUT photos if someone already sent them, but NEVER ask for them yourself")

            # Emoji probability
            emoji_prob = style_settings.get("emoji_probability", 0)
            if emoji_prob > 0:
                if emoji_prob >= 80:
                    context_parts.append(f"Use emojis VERY OFTEN (probability: {emoji_prob}%) - add them frequently to messages 😊👍🔥")
                elif emoji_prob >= 50:
                    context_parts.append(f"Use emojis REGULARLY (probability: {emoji_prob}%) - add them to about half of messages 😊")
                elif emoji_prob >= 20:
                    context_parts.append(f"Use emojis OCCASIONALLY (probability: {emoji_prob}%) - add them sometimes when natural")
                else:
                    context_parts.append(f"Use emojis RARELY (probability: {emoji_prob}%) - only occasionally")
                context_parts.append("Examples: 😊 😂 👍 🔥 💪 😅 🤔 ❤️ 😢 😡 (use contextually appropriate emojis)")

            # Keep ASCII emoticons as backup
            if style_settings.get("use_ascii_emoticons"):
                context_parts.append("You may also use ASCII emoticons like :) :D :( occasionally")

            context_parts.append("=== END CRITICAL REQUIREMENTS ===\n")

        system_prompt = "\n".join(context_parts)

        # Build conversation history - EMPHASIZE not to repeat
        conversation_history = []
        for idx, msg in enumerate(recent_messages, 1):
            # Highlight the unanswered question if it exists
            if unanswered_question and msg.id == unanswered_question.id:
                conversation_history.append(f"Message {idx}: ❓❓❓ {msg.message} ❓❓❓ ← YOU MUST ANSWER THIS!")
            else:
                conversation_history.append(f"Message {idx}: {msg.message}")

        if conversation_history:
            history_text = "\n".join(conversation_history)
            if unanswered_question:
                history_header = f"📝 Recent conversation:\n\n{history_text}\n\n⚠️ LOOK FOR ❓❓❓ - that's the question you MUST answer!"
            else:
                history_header = f"📝 Recent conversation ({len(recent_messages)} messages):\n⚠️ DO NOT repeat any of these phrases, sentiments, or ideas!\n\n{history_text}"
        else:
            history_header = "No previous messages - start fresh!"

        # Build user prompt with style reminders
        user_prompt_parts = [history_header, ""]

        # Add critical reminders based on settings
        if style_settings:
            # Gender reminder - CRITICAL
            gender = style_settings.get("gender", "male")
            if gender == "female":
                user_prompt_parts.append("⚠️ CRITICAL REMINDER: You are FEMALE! Use feminine grammar: 'я була', 'я думала', 'я втомилася' (NOT masculine forms!)")
            else:
                user_prompt_parts.append("REMINDER: You are MALE - use masculine grammar.")

            if not style_settings.get("use_punctuation", True):
                user_prompt_parts.append("REMEMBER: NO punctuation marks at all!")
            if not style_settings.get("use_uppercase", True):
                user_prompt_parts.append("REMEMBER: Only lowercase letters!")

            length = style_settings.get("message_length", "medium")
            if length == "short":
                user_prompt_parts.append("REMEMBER: Very short response (5-15 words max)!")
            elif length == "long":
                user_prompt_parts.append("REMEMBER: Long detailed response (3-5 sentences)!")

        # Special instructions if answering a question
        if unanswered_question:
            user_prompt_parts.append("\n" + "🔴"*30)
            user_prompt_parts.append("⭐ CRITICAL: YOU MUST ANSWER THIS EXACT QUESTION:")
            user_prompt_parts.append(f"❓ '{unanswered_question.message}'")
            user_prompt_parts.append("🔴"*30)
            user_prompt_parts.append("\n⚠️ REQUIREMENTS:")
            user_prompt_parts.append("1. Your answer must be about the SAME TOPIC as the question")
            user_prompt_parts.append("2. If question about ENGINE (двигун) - answer about ENGINE, not brakes/battery/etc")
            user_prompt_parts.append("3. If question about GAS (газ) - answer about GAS prices/stations")
            user_prompt_parts.append("4. Share YOUR specific experience with that topic")
            user_prompt_parts.append("5. NO '?' symbols - this is an ANSWER, not a question")
            user_prompt_parts.append("\n⛔ FORBIDDEN:")
            user_prompt_parts.append("- Talking about DIFFERENT topic than asked")
            user_prompt_parts.append("- Asking new question")
            user_prompt_parts.append("- Using '?' symbol")
            user_prompt_parts.append("\n✅ Format: 'В мене [опис проблеми], [що робив], [результат]'")

        # Topic shift reminder based on message count (only if not answering question)
        if not unanswered_question and message_count > 0 and message_count % 4 == 0:
            user_prompt_parts.append(f"\n🔄 TOPIC CHANGE REQUIRED (message #{message_count + 1}):")
            user_prompt_parts.append("⛔ STOP current topic immediately!")
            user_prompt_parts.append("⛔ FORBIDDEN: Asking 'а в [місто/місце]?' or similar variations")
            user_prompt_parts.append("⛔ FORBIDDEN: Continuing what was just discussed")
            user_prompt_parts.append("\n✅ You MUST introduce NEW topic:")
            user_prompt_parts.append("- NEW question about DIFFERENT subject")
            user_prompt_parts.append("- Personal story/opinion on UNRELATED topic")
            if global_prompt:
                user_prompt_parts.append(f"- Relevant to: {global_prompt}")
            user_prompt_parts.append("\nExample: If discussion was about gas prices, switch to car repairs, traffic, weather, work, etc.")
        elif not unanswered_question:
            user_prompt_parts.append(f"\n💬 Message #{message_count + 1}: Respond naturally, don't repeat patterns.")

        # Critical reminders (skip if answering a question)
        if not unanswered_question:
            user_prompt_parts.append("\n⛔ ABSOLUTELY FORBIDDEN:")
            user_prompt_parts.append("- Repeating question patterns ('а в Києві?', 'а в Харкові?' after someone asked)")
            user_prompt_parts.append("- Echoing sentiments already expressed")
            user_prompt_parts.append("- Asking for photos ('скиньте фото', 'send photo')")

        # Final instructions
        if unanswered_question:
            user_prompt_parts.append("\nGenerate ONE direct answer to the question (NO new questions!).")
        else:
            user_prompt_parts.append("\nGenerate ONE unique, creative response.")

        user_prompt_parts.append("Follow ALL requirements above EXACTLY.")
        user_prompt_parts.append("Return ONLY the message text, no explanations.")

        user_prompt = "\n".join(user_prompt_parts)

        try:
            # Debug: log style settings and message count
            print(f"[ConversationService] Message count: {message_count}, Style settings: {style_settings}")

            # Pass the complete system_prompt we built with all style settings
            generated_message = await grok_service.generate_conversation_starter(
                trigger_message=user_prompt,
                custom_system_prompt=system_prompt
            )

            # Return dict with message and reply_to info
            reply_to_msg_id = unanswered_question.telegram_message_id if unanswered_question else None
            return {
                'message': generated_message,
                'reply_to': reply_to_msg_id
            }

        except Exception as e:
            print(f"[ConversationService] Error generating reply: {e}")
            raise

    async def _send_member_message(
        self,
        client: TelegramClient,
        group: Group,
        member: Member,
        message_text: str,
        reply_to: Optional[int] = None
    ):
        """
        Send a message from a member and save to chat history

        Args:
            reply_to: Telegram message ID to reply to (optional)
        """
        try:
            # Get entity first
            entity = await client.get_entity(group.telegram_id)

            # Calculate typing duration: 1 second per word
            word_count = len(message_text.split())
            typing_duration = word_count  # seconds

            print(f"[ConversationService] Simulating typing for {typing_duration}s ({word_count} words)...")

            # Simulate typing action
            # Telethon typing action lasts ~5 seconds, so we need to repeat if duration is longer
            elapsed = 0
            while elapsed < typing_duration:
                await client(SetTypingRequest(
                    peer=entity,
                    action=SendMessageTypingAction()
                ))

                # Wait for the shorter of: remaining time or 4 seconds
                wait_time = min(4, typing_duration - elapsed)
                await asyncio.sleep(wait_time)
                elapsed += wait_time

            # Send to Telegram (with reply if specified)
            sent_message = await client.send_message(
                entity=entity,
                message=message_text,
                reply_to=reply_to
            )

            reply_info = f" (replying to message {reply_to})" if reply_to else ""
            print(f"[ConversationService] Member message sent to '{group.name}'{reply_info}")

            # Save to both chat_history and message_history with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with async_session_maker() as db:
                        # Save to chat_history (for conversation tracking)
                        chat_entry = ChatHistory(
                            group_id=group.id,
                            userbot_id=member.userbot_id,
                            message=message_text,
                            telegram_message_id=sent_message.id,
                            additional_info={
                                "global_prompt": group.global_prompt or "",
                                "member_prompt": member.additional_prompt or "",
                                "auto_generated": True
                            }
                        )
                        db.add(chat_entry)

                        # Save to message_history (for general message tracking)
                        message_entry = MessageHistory(
                            message=message_text,
                            group_id=group.id,
                            userbot_id=member.userbot_id,
                            additional_info={
                                "telegram_message_id": sent_message.id,
                                "auto_generated": True,
                                "message_type": "conversation_reply"
                            }
                        )
                        db.add(message_entry)

                        await db.commit()
                        print(f"[ConversationService] Message saved to chat_history and message_history")
                        break  # Success, exit retry loop

                except Exception as db_error:
                    error_msg = str(db_error)
                    if "database is locked" in error_msg.lower() and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 0.5  # 0.5s, 1s, 1.5s
                        print(f"[ConversationService] Database locked on attempt {attempt + 1}/{max_retries}, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Last attempt or different error - log and raise
                        print(f"[ConversationService] Failed to save message after {attempt + 1} attempts: {db_error}")
                        if attempt == max_retries - 1:
                            raise

            # Update last sender
            self.last_sender[str(group.id)] = member.userbot_id

        except Exception as e:
            print(f"[ConversationService] Error sending member message: {e}")
            raise

    async def _conversation_loop(self, group_id: str):
        """Main conversation loop for a group"""
        print(f"[ConversationService] Starting conversation loop for group {group_id}")

        try:
            while True:
                try:
                    async with async_session_maker() as db:
                        # Get group details
                        result = await db.execute(
                            select(Group).where(Group.id == UUID(group_id))
                        )
                        group = result.scalar_one_or_none()

                        if not group or not group.is_active:
                            print(f"[ConversationService] Group {group_id} is no longer active, stopping loop")
                            break

                        # Get non-admin members
                        members_result = await db.execute(
                            select(Member, Userbot)
                            .join(Userbot, Member.userbot_id == Userbot.id)
                            .where(
                                Member.group_id == UUID(group_id),
                                Member.is_admin == False,
                                Userbot.phone_number.isnot(None)
                            )
                        )
                        members_data = members_result.all()

                        if not members_data:
                            print(f"[ConversationService] No members in group {group_id}")
                            break

                        # Filter out last sender
                        last_sender_id = self.last_sender.get(group_id)
                        available_members = [
                            (member, userbot) for member, userbot in members_data
                            if member.userbot_id != last_sender_id
                        ]

                        if not available_members:
                            # Everyone has spoken, reset
                            available_members = members_data

                        # Random selection
                        selected_member, selected_userbot = random.choice(available_members)

                        print(f"[ConversationService] Selected member: {selected_userbot.name or selected_userbot.phone_number}")

                        # Get recent messages for context
                        recent_messages = await self._get_recent_messages(
                            group_id=UUID(group_id),
                            limit=group.context_messages_count
                        )

                        # Check for unanswered questions - PRIORITY
                        unanswered_question = self._find_unanswered_question(recent_messages)
                        if unanswered_question:
                            print(f"[ConversationService] Found unanswered question: '{unanswered_question.message}'")

                        # Generate reply with style settings
                        reply_data = await self._generate_reply(
                            userbot_id=selected_member.userbot_id,
                            group_id=UUID(group_id),
                            global_prompt=group.global_prompt or "",
                            member_prompt=selected_member.additional_prompt or "",
                            recent_messages=recent_messages,
                            style_settings=selected_userbot.style_settings,
                            unanswered_question=unanswered_question
                        )

                        message_text = reply_data['message']
                        reply_to = reply_data['reply_to']

                        print(f"[ConversationService] Generated: {message_text}")
                        if reply_to:
                            print(f"[ConversationService] Will reply to message ID: {reply_to}")

                        # Get client for this member
                        session_path = self._find_session_by_phone(selected_userbot.phone_number)
                        if not session_path:
                            print(f"[ConversationService] Session not found for {selected_userbot.phone_number}")
                            continue

                        client = TelegramClient(
                            str(session_path.with_suffix('')),
                            self.api_id,
                            self.api_hash
                        )

                        try:
                            await client.connect()

                            if not await client.is_user_authorized():
                                print(f"[ConversationService] Session not authorized for {selected_userbot.phone_number}")
                                continue

                            # Send message (with reply if answering a question)
                            await self._send_member_message(
                                client=client,
                                group=group,
                                member=selected_member,
                                message_text=message_text,
                                reply_to=reply_to
                            )

                        finally:
                            # Always disconnect client, even if error occurs
                            if client.is_connected():
                                await client.disconnect()

                        # Random delay
                        delay = random.randint(group.min_delay_seconds, group.max_delay_seconds)
                        print(f"[ConversationService] Waiting {delay} seconds before next message...")
                        await asyncio.sleep(delay)

                except Exception as iteration_error:
                    # Handle errors within a single iteration without stopping the loop
                    error_msg = str(iteration_error)
                    print(f"[ConversationService] Error in iteration for {group_id}: {error_msg}")

                    # Check if it's a database lock error
                    if "database is locked" in error_msg.lower():
                        print(f"[ConversationService] Database locked, waiting 5 seconds before retry...")
                        await asyncio.sleep(5)
                    elif "operational error" in error_msg.lower():
                        print(f"[ConversationService] Database operational error, waiting 3 seconds...")
                        await asyncio.sleep(3)
                    else:
                        # For other errors, wait shorter time
                        print(f"[ConversationService] Unexpected error, waiting 2 seconds...")
                        await asyncio.sleep(2)

                    # Continue to next iteration instead of breaking
                    continue

        except asyncio.CancelledError:
            print(f"[ConversationService] Conversation loop cancelled for group {group_id}")
        except Exception as e:
            print(f"[ConversationService] Error in conversation loop for {group_id}: {e}")
        finally:
            if group_id in self.active_conversations:
                del self.active_conversations[group_id]
            print(f"[ConversationService] Conversation loop ended for group {group_id}")

    async def start_conversation(self, group_id: str):
        """Start conversation for a specific group"""
        if group_id in self.active_conversations:
            print(f"[ConversationService] Conversation already active for group {group_id}")
            return

        # Reset last sender
        self.last_sender[group_id] = None

        # Start loop
        task = asyncio.create_task(self._conversation_loop(group_id))
        self.active_conversations[group_id] = task
        print(f"[ConversationService] Conversation started for group {group_id}")

    async def stop_conversation(self, group_id: str):
        """Stop conversation for a specific group"""
        if group_id not in self.active_conversations:
            print(f"[ConversationService] No active conversation for group {group_id}")
            return

        task = self.active_conversations[group_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        if group_id in self.active_conversations:
            del self.active_conversations[group_id]

        print(f"[ConversationService] Conversation stopped for group {group_id}")

    async def restart_conversation(self, group_id: str):
        """Restart conversation (new topic from admin)"""
        print(f"[ConversationService] Restarting conversation for group {group_id} (new topic)")
        await self.stop_conversation(group_id)
        await self.start_conversation(group_id)

    def get_active_conversations_count(self) -> int:
        """Get number of active conversations"""
        return len(self.active_conversations)


# Global instance
conversation_service = ConversationService()
