"""
Менеджери для роботи з базою даних

Використання:
    from database.managers import UserBotsManager, GroupsManager, MembersManager

    # Створення екземплярів
    userbots_manager = UserBotsManager()
    groups_manager = GroupsManager()
    members_manager = MembersManager()

    # Використання з async session
    async with get_db() as db:
        userbot = await userbots_manager.get_by_phone(db, "+380123456789")
        groups = await groups_manager.get_by_admin(db, admin_id)
        members = await members_manager.get_members_by_group(db, group_id)
"""

from database.managers.base_manager import BaseManager
from database.managers.userbots_manager import UserBotsManager
from database.managers.groups_manager import GroupsManager
from database.managers.members_manager import MembersManager
from database.managers.contacts_manager import ContactsManager

__all__ = [
    "BaseManager",
    "UserBotsManager",
    "GroupsManager",
    "MembersManager",
    "ContactsManager",
    "StickersManager",
]
