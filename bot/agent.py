"""Haystack-агент персонального помощника."""

from __future__ import annotations

import os
from dataclasses import dataclass

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from bot.tools import (
    CatPhoto,
    begin_agent_request,
    consume_pending_cat_photo,
    end_agent_request,
    get_agent_tools,
)

SYSTEM_PROMPT = """Ты умный персональный помощник в Telegram.
Отвечай на русском языке, дружелюбно и по делу.
Учитывай контекст предыдущих сообщений пользователя и веди диалог как настоящий помощник.
Если нужны актуальные данные — используй доступные инструменты:
- get_random_cat_fact — случайный факт о кошках;
- describe_random_cat_breed — фото кошки и описание породы (фото бот отправит сам, не вставляй ссылки и markdown);
- get_weather — погода в городе.
Не выдумывай факты, которых нет в контексте или инструментах."""


@dataclass(frozen=True)
class AgentReply:
    text: str
    cat_photo: CatPhoto | None = None


def build_agent() -> Agent:
    chat_generator = OpenAIChatGenerator(
        api_key=Secret.from_env_var("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        api_base_url=os.getenv("OPENAI_BASE_URL"),
    )
    return Agent(
        chat_generator=chat_generator,
        tools=get_agent_tools(),
        system_prompt=SYSTEM_PROMPT,
        max_agent_steps=8,
    )


def run_agent(agent: Agent, user_text: str, memory_context: str) -> AgentReply:
    """Запустить агента с учётом контекста из Chroma."""
    request_id = begin_agent_request()
    system_prompt = (
        f"{SYSTEM_PROMPT}\n\nРелевантный контекст из памяти:\n{memory_context}"
    )
    try:
        result = agent.run(
            messages=[ChatMessage.from_user(user_text)],
            system_prompt=system_prompt,
        )
        last_message = result.get("last_message")
        if last_message is None:
            return AgentReply(text="Не удалось сформировать ответ.")
        text = last_message.text or "Не удалось сформировать ответ."
        return AgentReply(text=text, cat_photo=consume_pending_cat_photo())
    finally:
        end_agent_request(request_id)
