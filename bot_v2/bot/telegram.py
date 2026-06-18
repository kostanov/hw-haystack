"""Создание aiogram Bot и вспомогательные функции."""

from __future__ import annotations

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import Message

from bot_v2.bot.config import Settings


def create_bot(settings: Settings) -> Bot:
    base_url = settings.bot_base_url
    if base_url:
        api = TelegramAPIServer.from_base(
            base_url.rstrip("/"),
            is_local=True,
        )
        if settings.bot_base_file_url:
            file_base = settings.bot_base_file_url.rstrip("/")
            api = TelegramAPIServer(
                base=api.base,
                file=f"{file_base}/file/bot{{token}}/{{path}}",
                is_local=True,
            )
        session = AiohttpSession(api=api)
        return Bot(token=settings.bot_token, session=session)

    return Bot(token=settings.bot_token)


def user_id(message: Message) -> str:
    if message.from_user is None:
        return "unknown"
    return str(message.from_user.id)
