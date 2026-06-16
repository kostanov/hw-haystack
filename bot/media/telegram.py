"""Отправка изображений в Telegram (эмулятор и production)."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)


class TelegramMediaDelivery:
    """Доставка изображений: для эмулятора — multipart sendPhoto, как в telegram-emulator."""

    def __init__(self, bot_token: str, bot_base_url: str | None) -> None:
        self._bot_token = bot_token
        self._bot_base_url = bot_base_url.rstrip("/") if bot_base_url else None

    async def send_image(
        self,
        bot: Bot,
        chat_id: int,
        file_path: Path,
        caption: str = "",
    ) -> None:
        if self._bot_base_url:
            await self._send_via_emulator(chat_id, file_path, caption)
            return

        photo = FSInputFile(file_path)
        try:
            await bot.send_photo(chat_id, photo, caption=caption or None)
        except TelegramAPIError:
            logger.debug("send_photo не удался, пробуем send_document", exc_info=True)
            await bot.send_document(
                chat_id,
                FSInputFile(file_path),
                caption=caption or None,
            )

    async def _send_via_emulator(
        self,
        chat_id: int,
        file_path: Path,
        caption: str,
    ) -> None:
        async with aiohttp.ClientSession() as session:
            if await self._post_multipart(
                session,
                "sendPhoto",
                chat_id,
                file_path,
                caption,
                field_name="photo",
            ):
                return
            if await self._post_multipart(
                session,
                "sendDocument",
                chat_id,
                file_path,
                caption,
                field_name="document",
            ):
                return
        raise RuntimeError("Эмулятор не принял фото")

    async def _post_multipart(
        self,
        session: aiohttp.ClientSession,
        method: str,
        chat_id: int,
        file_path: Path,
        caption: str,
        *,
        field_name: str,
    ) -> bool:
        url = f"{self._bot_base_url}/bot{self._bot_token}/{method}?chat_id={chat_id}"
        content_type = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
        form = aiohttp.FormData()
        form.add_field("chat_id", str(chat_id))
        if caption:
            form.add_field("caption", caption[:1024])
        form.add_field(
            field_name,
            file_path.read_bytes(),
            filename=file_path.name,
            content_type=content_type,
        )

        try:
            async with session.post(
                url,
                data=form,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                body = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as exc:
            logger.warning("%s: ошибка запроса: %s", method, exc)
            return False

        if isinstance(body, dict) and body.get("ok"):
            logger.info("%s: файл %s отправлен в чат", method, file_path)
            return True

        description = body.get("description", body) if isinstance(body, dict) else body
        logger.warning("%s: отклонено эмулятором: %s", method, description)
        return False
