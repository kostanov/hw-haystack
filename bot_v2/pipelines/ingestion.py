"""Пайплайн загрузки документов: DocLing → Chroma → резюме."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack_integrations.components.converters.docling import DoclingConverter
from haystack_integrations.components.converters.docling.converter import ExportType
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

from bot_v2.bot.config import Settings
from bot_v2.components.enricher import DocumentIngestEnricher
from bot_v2.components.summarizer import DocumentSummarizer


@dataclass(frozen=True)
class IngestionResult:
    documents: list[Document]
    summary: str


class IngestionPipeline:
    """DocLing-анализ файла, сохранение чанков в Chroma и краткое резюме."""

    def __init__(self, document_store: ChromaDocumentStore, settings: Settings) -> None:
        self._summarizer = DocumentSummarizer(settings)
        self._pipeline = Pipeline()
        self._pipeline.add_component(
            "converter",
            DoclingConverter(export_type=ExportType.DOC_CHUNKS),
        )
        self._pipeline.add_component("enricher", DocumentIngestEnricher())
        self._pipeline.add_component(
            "writer",
            DocumentWriter(document_store=document_store),
        )
        self._pipeline.connect("converter.documents", "enricher.documents")
        self._pipeline.connect("enricher.documents", "writer.documents")

    def run(self, user_id: str, file_path: Path, filename: str) -> IngestionResult:
        result = self._pipeline.run(
            {
                "converter": {"sources": [str(file_path)]},
                "enricher": {"user_id": user_id, "filename": filename},
            },
            include_outputs_from={"enricher"},
        )
        documents: list[Document] = result["enricher"]["documents"]
        summary = self._summarizer.summarize(documents)
        return IngestionResult(documents=documents, summary=summary)
