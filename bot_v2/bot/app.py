"""Telegram-бот bot_v2: текстовые сообщения и загрузка документов."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from bot_v2.bot.config import SUPPORTED_DOCUMENT_EXTENSIONS, Settings
from bot_v2.bot.downloads import download_document
from bot_v2.bot.telegram import create_bot, user_id
from bot_v2.components.chroma import create_document_store
from bot_v2.components.media.telegram import TelegramMediaDelivery
from bot_v2.pipelines.generation import GenerationPipeline
from bot_v2.pipelines.ingestion import IngestionPipeline

logger = logging.getLogger(__name__)

FILE_RECEIVED_MSG = (
    "Файл получен. Запускаю анализ и сохранение. Это может занять немного времени…"
)
FILE_READY_MSG = "Готово. Я изучил этот файл, теперь можем его обсудить."


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def handle_text(
    message: Message,
    generation: GenerationPipeline,
    media_delivery: TelegramMediaDelivery,
) -> None:
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    text = message.text.strip()
    if not text:
        return

    uid = user_id(message)
    reply = await asyncio.to_thread(generation.run, uid, text)
    generation.remember_exchange(uid, text, reply.text)

    if reply.cat_photo is not None:
        try:
            await media_delivery.send_image(
                message.bot,
                message.chat.id,
                reply.cat_photo.path,
            )
        except Exception:
            logger.exception("Не удалось отправить фото кошки")
            await message.answer("Фото найдено, но отправить в чат не удалось.")

    await message.answer(reply.text)


async def handle_document(
    message: Message,
    settings: Settings,
    ingestion: IngestionPipeline,
) -> None:
    if message.document is None or message.bot is None:
        return

    filename = message.document.file_name or f"document_{message.document.file_id}"
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        await message.answer(
            f"Формат «{extension or 'без расширения'}» не поддерживается. "
            f"Допустимые форматы: {supported}."
        )
        return

    await message.answer(FILE_RECEIVED_MSG)

    local_name = f"{uuid4().hex}{extension}"
    local_path = settings.uploads_dir / local_name

    try:
        await download_document(message.bot, settings, message.document, local_path)
        uid = user_id(message)
        result = await asyncio.to_thread(
            ingestion.run,
            uid,
            local_path,
            filename,
        )
        await message.answer(FILE_READY_MSG)
        await message.answer(result.summary)
    except Exception:
        logger.exception("Ошибка обработки документа %s", filename)
        await message.answer(
            "Не удалось обработать файл. Проверьте формат и попробуйте снова."
        )
    finally:
        local_path.unlink(missing_ok=True)


async def main() -> None:
    load_dotenv()
    setup_logging()

    settings = Settings.from_env()
    settings.ensure_dirs()

    document_store = create_document_store(settings)
    generation = GenerationPipeline(document_store, settings)
    ingestion = IngestionPipeline(document_store, settings)
    bot = create_bot(settings)
    media_delivery = TelegramMediaDelivery(
        bot_token=settings.bot_token,
        bot_base_url=settings.bot_base_url,
    )
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Привет! Я персональный помощник v2. "
            "Помню контекст диалога, анализирую загруженные документы (PDF, DOCX и др.), "
            "рассказываю факты о кошках, определяю породу по фото и сообщаю погоду."
        )

    @dispatcher.message(F.document)
    async def on_document(message: Message) -> None:
        try:
            await handle_document(message, settings, ingestion)
        except Exception:
            logger.exception("Ошибка обработки документа")
            await message.answer("Произошла ошибка при загрузке файла.")

    @dispatcher.message(F.text)
    async def on_text(message: Message) -> None:
        try:
            await handle_text(message, generation, media_delivery)
        except Exception:
            logger.exception("Ошибка обработки сообщения")
            await message.answer("Произошла ошибка. Попробуйте позже.")

    logger.info("Бот v2 запущен")
    await dispatcher.start_polling(bot)


def cli() -> None:
    asyncio.run(main())
