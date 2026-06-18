"""Скачивание файлов из Telegram (эмулятор не отдаёт file_unique_id в getFile)."""

from __future__ import annotations

from pathlib import Path

import aiohttp
from aiogram import Bot
from aiogram.types import Document

from bot_v2.bot.config import Settings


async def download_document(
    bot: Bot,
    settings: Settings,
    document: Document,
    destination: Path,
) -> None:
    if settings.bot_base_url:
        await _download_via_emulator(settings, document.file_id, destination)
        return
    await bot.download(document, destination=destination)


async def _download_via_emulator(
    settings: Settings,
    file_id: str,
    destination: Path,
) -> None:
    file_base = (settings.bot_base_file_url or settings.bot_base_url or "").rstrip("/")
    url = f"{file_base}/file/bot{settings.bot_token}/{file_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            resp.raise_for_status()
            destination.write_bytes(await resp.read())
