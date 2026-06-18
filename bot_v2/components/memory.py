"""Память диалога на Chroma с косинусным поиском."""

from __future__ import annotations

import uuid

from haystack.dataclasses import Document
from haystack_integrations.components.retrievers.chroma import ChromaQueryTextRetriever
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

SOURCE_TYPE_CONVERSATION = "conversation"


class ConversationMemory:
    """Хранение и извлечение контекста диалога пользователя."""

    def __init__(self, document_store: ChromaDocumentStore) -> None:
        self.document_store = document_store
        self.retriever = ChromaQueryTextRetriever(document_store, top_k=5)

    def _conversation_filters(self, user_id: str) -> dict:
        return {
            "operator": "AND",
            "conditions": [
                {"field": "user_id", "operator": "==", "value": user_id},
                {
                    "field": "source_type",
                    "operator": "==",
                    "value": SOURCE_TYPE_CONVERSATION,
                },
            ],
        }

    def get_context(self, user_id: str, query: str, *, top_k: int = 5) -> str:
        result = self.retriever.run(
            query=query,
            filters=self._conversation_filters(user_id),
            top_k=top_k,
        )
        documents: list[Document] = result["documents"]
        if not documents:
            return "Нет сохранённого контекста диалога."

        lines = []
        for document in documents:
            role = document.meta.get("role", "message")
            lines.append(f"- [{role}] {document.content}")
        return "\n".join(lines)

    def remember(self, user_id: str, role: str, text: str) -> None:
        document = Document(
            id=str(uuid.uuid4()),
            content=text,
            meta={
                "user_id": user_id,
                "role": role,
                "source_type": SOURCE_TYPE_CONVERSATION,
            },
        )
        self.document_store.write_documents([document])
