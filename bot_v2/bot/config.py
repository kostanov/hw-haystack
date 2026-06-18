"""Настройки bot_v2 из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    chroma_persist_directory: Path
    chroma_collection: str
    cat_photos_dir: Path
    uploads_dir: Path
    bot_token: str
    bot_base_url: str | None
    bot_base_file_url: str | None
    openai_api_key: str
    openai_base_url: str | None
    openai_chat_model: str
    openai_embedding_model: str

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.getenv("BOT_V2_DATA_DIR", "./data_v2"))
        return cls(
            data_dir=data_dir,
            chroma_persist_directory=Path(
                os.getenv("CHROMA_V2_PERSIST_DIRECTORY", str(data_dir / "chroma"))
            ),
            chroma_collection=os.getenv("CHROMA_V2_COLLECTION", "bot_v2_collection"),
            cat_photos_dir=Path(
                os.getenv("BOT_V2_CAT_PHOTOS_DIR", str(data_dir / "cat_photos"))
            ),
            uploads_dir=Path(
                os.getenv("BOT_V2_UPLOADS_DIR", str(data_dir / "uploads"))
            ),
            bot_token=os.environ["BOT_TOKEN"],
            bot_base_url=os.getenv("BOT_BASE_URL"),
            bot_base_file_url=os.getenv("BOT_BASE_FILE_URL"),
            openai_api_key=os.environ["OPENAI_API_KEY"],
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            openai_embedding_model=os.getenv(
                "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
            ),
        )

    def ensure_dirs(self) -> None:
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.cat_photos_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".csv",
}
