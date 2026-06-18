default:
    @just --list

bot:
    uv run python -m bot

bot-v2:
    uv run python -m bot_v2

lint:
    uv run ruff check

fix:
    uv run ruff check --fix

format:
    uv run ruff format
