"""Медиа: сохранение файлов и отправка в Telegram."""

from bot.media.storage import save_media_file
from bot.media.telegram import TelegramMediaDelivery

__all__ = ["TelegramMediaDelivery", "save_media_file"]
