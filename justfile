default:
    @just --list

bot:
    uv run python -m bot

lint:
    uv run ruff check

fix:
    uv run ruff check --fix

format:
    uv run ruff format
