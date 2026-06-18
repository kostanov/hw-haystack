"""Поиск загруженных документов пользователя в Chroma."""

from __future__ import annotations

from haystack.dataclasses import Document
from haystack_integrations.components.retrievers.chroma import ChromaQueryTextRetriever
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

SOURCE_TYPE_DOCUMENT = "document"


class DocumentRetriever:
    """Извлечение релевантных чанков из загруженных файлов."""

    def __init__(self, document_store: ChromaDocumentStore, *, top_k: int = 5) -> None:
        self.retriever = ChromaQueryTextRetriever(document_store, top_k=top_k)

    def _document_filters(self, user_id: str) -> dict:
        return {
            "operator": "AND",
            "conditions": [
                {"field": "user_id", "operator": "==", "value": user_id},
                {
                    "field": "source_type",
                    "operator": "==",
                    "value": SOURCE_TYPE_DOCUMENT,
                },
            ],
        }

    def get_context(self, user_id: str, query: str, *, top_k: int = 5) -> str:
        result = self.retriever.run(
            query=query,
            filters=self._document_filters(user_id),
            top_k=top_k,
        )
        documents: list[Document] = result["documents"]
        if not documents:
            return "Нет загруженных документов по этому запросу."

        lines = []
        for document in documents:
            filename = document.meta.get("filename", "файл")
            chunk_index = document.meta.get("chunk_index")
            page = document.meta.get("page")
            location = []
            if page is not None:
                location.append(f"стр. {page}")
            if chunk_index is not None:
                location.append(f"чанк {chunk_index}")
            suffix = f" ({', '.join(location)})" if location else ""
            lines.append(f"- [{filename}{suffix}] {document.content}")
        return "\n".join(lines)

    def get_documents_text(self, documents: list[Document]) -> str:
        return "\n\n".join(doc.content for doc in documents if doc.content)
