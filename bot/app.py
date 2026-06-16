"""Telegram-бот персонального помощника на Haystack."""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from bot.agent import build_agent, run_agent
from bot.memory import ConversationMemory
from bot.media.telegram import TelegramMediaDelivery

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_bot() -> Bot:
    token = os.environ["BOT_TOKEN"]
    base_url = os.getenv("BOT_BASE_URL")

    if base_url:
        api = TelegramAPIServer.from_base(
            base_url.rstrip("/"),
            is_local=True,
        )
        file_url = os.getenv("BOT_BASE_FILE_URL")
        if file_url:
            file_base = file_url.rstrip("/")
            api = TelegramAPIServer(
                base=api.base,
                file=f"{file_base}/file/bot{{token}}/{{path}}",
                is_local=True,
            )
        session = AiohttpSession(api=api)
        return Bot(token=token, session=session)

    return Bot(token=token)


def user_id(message: Message) -> str:
    if message.from_user is None:
        return "unknown"
    return str(message.from_user.id)


async def handle_text(
    message: Message,
    memory: ConversationMemory,
    agent,
    media_delivery: TelegramMediaDelivery,
) -> None:
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    text = message.text.strip()
    if not text:
        return

    uid = user_id(message)
    memory_context = memory.get_context(uid, text)
    reply = await asyncio.to_thread(run_agent, agent, text, memory_context)

    memory.remember(uid, "user", text)
    memory.remember(uid, "assistant", reply.text)

    if reply.cat_photo is not None:
        try:
            logger.info("Отправка фото кошки: %s", reply.cat_photo.path)
            await media_delivery.send_image(
                message.bot,
                message.chat.id,
                reply.cat_photo.path,
            )
        except Exception:
            logger.exception("Не удалось отправить фото кошки")
            await message.answer("Фото найдено, но отправить в чат не удалось.")

    await message.answer(reply.text)


async def main() -> None:
    load_dotenv()
    setup_logging()

    memory = ConversationMemory()
    agent = build_agent()
    bot = create_bot()
    media_delivery = TelegramMediaDelivery(
        bot_token=os.environ["BOT_TOKEN"],
        bot_base_url=os.getenv("BOT_BASE_URL"),
    )
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Привет! Я твой персональный помощник. "
            "Могу запоминать контекст, рассказывать факты о кошках, "
            "определять породу по фото и сообщать погоду."
        )

    @dispatcher.message(F.text)
    async def on_text(message: Message) -> None:
        try:
            await handle_text(message, memory, agent, media_delivery)
        except Exception:
            logger.exception("Ошибка обработки сообщения")
            await message.answer("Произошла ошибка. Попробуйте позже.")

    logger.info("Бот запущен")
    await dispatcher.start_polling(bot)


def cli() -> None:
    asyncio.run(main())
