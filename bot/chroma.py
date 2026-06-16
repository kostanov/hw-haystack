"""Фабрика ChromaDocumentStore для локального, удалённого и облачного Chroma."""

from __future__ import annotations

import os
from typing import Any

import chromadb
from haystack_integrations.document_stores.chroma import ChromaDocumentStore


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


def create_document_store() -> ChromaDocumentStore:
    """Создать ChromaDocumentStore по настройкам из окружения."""
    embedding_params: dict[str, Any] = {
        "api_key": os.environ["OPENAI_API_KEY"],
        "model_name": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    }
    api_base = os.getenv("OPENAI_BASE_URL")
    if api_base:
        embedding_params["api_base"] = api_base

    common: dict[str, Any] = {
        "collection_name": os.getenv("CHROMA_COLLECTION", "my_collection"),
        "embedding_function": "OpenAIEmbeddingFunction",
        "distance_function": "cosine",
        **embedding_params,
    }

    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    if api_key and tenant:
        return CloudChromaDocumentStore(**common)

    persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY")
    if persist_directory:
        os.makedirs(persist_directory, exist_ok=True)
        return ChromaDocumentStore(persist_path=persist_directory, **common)

    host = os.getenv("CHROMA_HOST")
    port = os.getenv("CHROMA_PORT")
    if host and port:
        return ChromaDocumentStore(host=host, port=int(port), **common)

    return ChromaDocumentStore(**common)
