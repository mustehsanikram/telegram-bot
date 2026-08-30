from aiogram.filters import BaseFilter
from aiogram.types import Message

from stylebot.config import Settings
from stylebot.services.clients import is_admin


class IsAdmin(BaseFilter):
    """Passes only for a sender listed in ADMIN_USER_IDS."""

    async def __call__(self, message: Message, settings: Settings) -> bool:
        user = message.from_user
        return user is not None and is_admin(user.id, settings.admin_user_ids)
