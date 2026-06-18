"""Обогащение метаданных чанков после DocLing."""

from __future__ import annotations

import uuid

from haystack import component
from haystack.dataclasses import Document

from bot_v2.components.document_retriever import SOURCE_TYPE_DOCUMENT


@component
class DocumentIngestEnricher:
    """Добавить user_id, имя файла и номер чанка/страницы к документам."""

    @component.output_types(documents=list[Document])
    def run(
        self,
        documents: list[Document],
        user_id: str,
        filename: str,
    ) -> dict[str, list[Document]]:
        enriched: list[Document] = []
        for index, document in enumerate(documents):
            meta = dict(document.meta)
            meta.update(
                {
                    "user_id": user_id,
                    "filename": filename,
                    "chunk_index": index,
                    "source_type": SOURCE_TYPE_DOCUMENT,
                }
            )
            page = meta.get("page_number") or meta.get("page")
            if page is not None:
                meta["page"] = page
            enriched.append(
                Document(
                    id=str(uuid.uuid4()),
                    content=document.content,
                    meta=meta,
                )
            )
        return {"documents": enriched}
