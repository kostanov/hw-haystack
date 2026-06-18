"""Инструменты агента bot_v2."""

from bot_v2.components.tools.agent_tools import (
    CatPhoto,
    begin_agent_request,
    configure_tools,
    consume_pending_cat_photo,
    end_agent_request,
    get_agent_tools,
)

__all__ = [
    "CatPhoto",
    "begin_agent_request",
    "configure_tools",
    "consume_pending_cat_photo",
    "end_agent_request",
    "get_agent_tools",
]
