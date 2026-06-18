"""Медиа-компоненты bot_v2."""

from bot_v2.components.media.storage import save_media_file
from bot_v2.components.media.telegram import TelegramMediaDelivery

__all__ = ["TelegramMediaDelivery", "save_media_file"]
