import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import (
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthKeyUnregisteredError,
    SessionPasswordNeededError
)
from dotenv import load_dotenv

load_dotenv()


class ContactService:
    """Service for managing Telegram contacts"""

    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')

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

    async def add_contacts_for_userbot(
        self,
        phone: str,
        contacts_info: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Add contacts for a single userbot

        Args:
            phone: Userbot phone number
            contacts_info: List of dicts with 'phone' and 'name'

        Returns:
            Dict with 'success', 'added', 'failed', 'error'
        """
        session_path = self._find_session_by_phone(phone)

        if not session_path:
            return {
                'success': False,
                'added': 0,
                'failed': len(contacts_info),
                'error': 'Session file not found'
            }

        client = TelegramClient(
            str(session_path.with_suffix('')),
            self.api_id,
            self.api_hash
        )

        try:
            await client.connect()

            if not client.is_user_authorized():
                return {
                    'success': False,
                    'added': 0,
                    'failed': len(contacts_info),
                    'error': 'Session not authorized'
                }

            telegram_contacts = []
            for i, info in enumerate(contacts_info):
                contact_phone = info.get('phone', '').lstrip('+')
                name = info.get('name', 'User').strip()
                parts = name.split(' ', 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ''

                telegram_contacts.append(InputPhoneContact(
                    client_id=i,
                    phone=contact_phone,
                    first_name=first,
                    last_name=last
                ))

            if telegram_contacts:
                result = await client(ImportContactsRequest(telegram_contacts))
                await asyncio.sleep(1.2)

                added = len(result.users) if result else 0
                failed = len(contacts_info) - added

                return {
                    'success': True,
                    'added': added,
                    'failed': failed,
                    'error': None
                }

            return {
                'success': True,
                'added': 0,
                'failed': 0,
                'error': None
            }

        except FloodWaitError as e:
            return {
                'success': False,
                'added': 0,
                'failed': len(contacts_info),
                'error': f'Flood wait: must wait {e.seconds} seconds'
            }
        except AuthKeyUnregisteredError:
            return {
                'success': False,
                'added': 0,
                'failed': len(contacts_info),
                'error': 'Session is invalid or expired'
            }
        except Exception as e:
            return {
                'success': False,
                'added': 0,
                'failed': len(contacts_info),
                'error': f'{type(e).__name__}: {str(e)}'
            }
        finally:
            if client.is_connected():
                await client.disconnect()

    async def contact_all_userbots(
        self,
        userbots_data: List[Dict[str, any]]
    ) -> AsyncGenerator[Dict[str, any], None]:
        """
        Add all userbots to each other's contacts with progress updates

        Args:
            userbots_data: List of dicts with 'id', 'phone_number', 'name'

        Yields:
            Progress updates as dicts
        """
        total_userbots = len(userbots_data)
        total_success = 0
        total_skipped = 0
        total_errors = 0

        yield {
            'type': 'started',
            'total_userbots': total_userbots,
            'message': f'Starting to process {total_userbots} userbots...'
        }

        for idx, userbot in enumerate(userbots_data, 1):
            userbot_id = userbot['id']
            phone = userbot.get('phone_number')
            name = userbot.get('name', phone)

            yield {
                'type': 'processing_userbot',
                'current': idx,
                'total': total_userbots,
                'userbot_name': name,
                'userbot_phone': phone
            }

            if not phone:
                total_skipped += 1
                yield {
                    'type': 'userbot_skipped',
                    'current': idx,
                    'total': total_userbots,
                    'userbot_name': name,
                    'reason': 'No phone number'
                }
                continue

            session_path = self._find_session_by_phone(phone)
            if not session_path:
                total_skipped += 1
                yield {
                    'type': 'userbot_skipped',
                    'current': idx,
                    'total': total_userbots,
                    'userbot_name': name,
                    'reason': 'Session file not found'
                }
                continue

            contacts_to_add = []
            for other_bot in userbots_data:
                if other_bot['id'] != userbot_id and other_bot.get('phone_number'):
                    contacts_to_add.append({
                        'phone': other_bot['phone_number'],
                        'name': other_bot.get('name', other_bot['phone_number'])
                    })

            if not contacts_to_add:
                total_skipped += 1
                yield {
                    'type': 'userbot_skipped',
                    'current': idx,
                    'total': total_userbots,
                    'userbot_name': name,
                    'reason': 'No valid contacts to add'
                }
                continue

            result = await self.add_contacts_for_userbot(phone, contacts_to_add)

            if result['success']:
                total_success += 1
                yield {
                    'type': 'userbot_completed',
                    'current': idx,
                    'total': total_userbots,
                    'userbot_name': name,
                    'added': result['added'],
                    'failed': result['failed']
                }
            else:
                total_errors += 1
                yield {
                    'type': 'userbot_error',
                    'current': idx,
                    'total': total_userbots,
                    'userbot_name': name,
                    'error': result['error']
                }

        yield {
            'type': 'completed',
            'total_userbots': total_userbots,
            'success': total_success,
            'skipped': total_skipped,
            'errors': total_errors,
            'message': f'Completed! Success: {total_success}, Skipped: {total_skipped}, Errors: {total_errors}'
        }
