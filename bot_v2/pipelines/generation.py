"""Пайплайн генерации ответа: retriever + Haystack Agent."""

from __future__ import annotations

from dataclasses import dataclass

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

from bot_v2.bot.config import Settings
from bot_v2.components.document_retriever import DocumentRetriever
from bot_v2.components.memory import ConversationMemory
from bot_v2.components.tools import (
    CatPhoto,
    begin_agent_request,
    configure_tools,
    consume_pending_cat_photo,
    end_agent_request,
    get_agent_tools,
)

SYSTEM_PROMPT = """Ты умный персональный помощник в Telegram.
Отвечай на русском языке, дружелюбно и по делу.
Учитывай контекст предыдущих сообщений пользователя и загруженные документы.
Если нужны актуальные данные — используй доступные инструменты:
- get_random_cat_fact — случайный факт о кошках;
- describe_random_cat_breed — фото кошки и описание породы (фото бот отправит сам, не вставляй ссылки и markdown);
- get_weather — погода в городе.
Не выдумывай факты, которых нет в контексте, документах или инструментах."""


@dataclass(frozen=True)
class GenerationResult:
    text: str
    cat_photo: CatPhoto | None = None


class GenerationPipeline:
    """Retriever по документам и памяти + агент с инструментами v1."""

    def __init__(self, document_store: ChromaDocumentStore, settings: Settings) -> None:
        configure_tools(settings)
        self.memory = ConversationMemory(document_store)
        self.documents = DocumentRetriever(document_store)
        chat_generator = OpenAIChatGenerator(
            api_key=Secret.from_token(settings.openai_api_key),
            model=settings.openai_chat_model,
            api_base_url=settings.openai_base_url,
        )
        self.agent = Agent(
            chat_generator=chat_generator,
            tools=get_agent_tools(),
            system_prompt=SYSTEM_PROMPT,
            max_agent_steps=8,
        )

    def run(self, user_id: str, user_text: str) -> GenerationResult:
        memory_context = self.memory.get_context(user_id, user_text)
        document_context = self.documents.get_context(user_id, user_text)

        request_id = begin_agent_request()
        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Релевантный контекст диалога:\n{memory_context}\n\n"
            f"Релевантные фрагменты загруженных документов:\n{document_context}"
        )
        try:
            result = self.agent.run(
                messages=[ChatMessage.from_user(user_text)],
                system_prompt=system_prompt,
            )
            last_message = result.get("last_message")
            if last_message is None:
                return GenerationResult(text="Не удалось сформировать ответ.")
            text = last_message.text or "Не удалось сформировать ответ."
            return GenerationResult(
                text=text,
                cat_photo=consume_pending_cat_photo(),
            )
        finally:
            end_agent_request(request_id)

    def remember_exchange(
        self, user_id: str, user_text: str, assistant_text: str
    ) -> None:
        self.memory.remember(user_id, "user", user_text)
        self.memory.remember(user_id, "assistant", assistant_text)
