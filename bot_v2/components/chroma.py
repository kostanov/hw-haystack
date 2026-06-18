"""Фабрика ChromaDocumentStore для bot_v2 (отдельные данные и коллекция)."""

from __future__ import annotations

import os
from typing import Any

import chromadb
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

from bot_v2.bot.config import Settings


class CloudChromaDocumentStore(ChromaDocumentStore):
    """ChromaDocumentStore с поддержкой Chroma Cloud."""

    def _ensure_initialized(self) -> None:
        if self._collection:
            return

        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        if not api_key or not tenant:
            super()._ensure_initialized()
            return

        client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=os.getenv("CHROMA_DATABASE", "default_database"),
        )
        self._client = client

        self._metadata = self._metadata or {}
        if "hnsw:space" not in self._metadata:
            self._metadata["hnsw:space"] = self._distance_function

        existing = [collection.name for collection in client.list_collections()]
        if self._collection_name in existing:
            self._collection = client.get_collection(
                self._collection_name,
                embedding_function=self._embedding_func,
            )
        else:
            self._collection = client.create_collection(
                name=self._collection_name,
                metadata=self._metadata,
                embedding_function=self._embedding_func,
            )


def create_document_store(settings: Settings) -> ChromaDocumentStore:
    """Создать ChromaDocumentStore по настройкам bot_v2."""
    settings.ensure_dirs()

    embedding_params: dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "model_name": settings.openai_embedding_model,
    }
    if settings.openai_base_url:
        embedding_params["api_base"] = settings.openai_base_url

    common: dict[str, Any] = {
        "collection_name": settings.chroma_collection,
        "embedding_function": "OpenAIEmbeddingFunction",
        "distance_function": "cosine",
        **embedding_params,
    }

    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    if api_key and tenant:
        return CloudChromaDocumentStore(**common)

    return ChromaDocumentStore(
        persist_path=str(settings.chroma_persist_directory),
        **common,
    )
