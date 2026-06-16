"""Память диалога на Haystack + Chroma с косинусным поиском."""

from __future__ import annotations

import uuid

from haystack.dataclasses import Document
from haystack_integrations.components.retrievers.chroma import ChromaQueryTextRetriever
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

from bot.chroma import create_document_store


class ConversationMemory:
    """Хранение и извлечение контекста диалога пользователя."""

    def __init__(self, document_store: ChromaDocumentStore | None = None) -> None:
        self.document_store = document_store or create_document_store()
        self.retriever = ChromaQueryTextRetriever(self.document_store, top_k=5)

    def get_context(self, user_id: str, query: str, *, top_k: int = 5) -> str:
        """Найти релевантный контекст по косинусному сходству."""
        filters = {"field": "user_id", "operator": "==", "value": user_id}
        result = self.retriever.run(query=query, filters=filters, top_k=top_k)
        documents: list[Document] = result["documents"]
        if not documents:
            return "Нет сохранённого контекста."

        lines = []
        for document in documents:
            role = document.meta.get("role", "message")
            lines.append(f"- [{role}] {document.content}")
        return "\n".join(lines)

    def remember(self, user_id: str, role: str, text: str) -> None:
        """Сохранить сообщение в Chroma."""
        document = Document(
            id=str(uuid.uuid4()),
            content=text,
            meta={"user_id": user_id, "role": role},
        )
        self.document_store.write_documents([document])
