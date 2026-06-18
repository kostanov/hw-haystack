"""Краткое резюме содержимого документа в одно предложение."""

from __future__ import annotations

from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack import Pipeline
from haystack.dataclasses import Document
from haystack.utils import Secret

from bot_v2.bot.config import Settings

SUMMARY_PROMPT = """По фрагментам документа составь ровно одно предложение на русском языке,
которое кратко описывает, о чём этот файл. Без вводных слов и без списков.

Фрагменты:
{% for doc in documents %}
---
{{ doc.content }}
{% endfor %}

Одно предложение:"""


class DocumentSummarizer:
    """Генерация однострочного резюме через LLM."""

    def __init__(self, settings: Settings) -> None:
        self._pipeline = Pipeline()
        self._pipeline.add_component(
            "prompt",
            PromptBuilder(
                template=SUMMARY_PROMPT,
                required_variables=["documents"],
            ),
        )
        self._pipeline.add_component(
            "llm",
            OpenAIGenerator(
                api_key=Secret.from_token(settings.openai_api_key),
                model=settings.openai_chat_model,
                api_base_url=settings.openai_base_url,
                generation_kwargs={"max_tokens": 120, "temperature": 0.3},
            ),
        )
        self._pipeline.connect("prompt", "llm")

    def summarize(self, documents: list[Document], *, max_chunks: int = 8) -> str:
        if not documents:
            return "Документ не содержит распознаваемого текста."

        sample = documents[:max_chunks]
        result = self._pipeline.run({"prompt": {"documents": sample}})
        replies = result["llm"]["replies"]
        if not replies:
            return "Не удалось составить краткое резюме файла."

        text = replies[0].strip().split("\n")[0].strip()
        if text.endswith("."):
            return text
        return f"{text}."
