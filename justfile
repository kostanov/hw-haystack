default:
    @just --list

run:
    uv run python main.py

ddgs *args:
    uv run duckduckgo.py {{args}}

hs-with-ddgs:
    uv run hs_with_ddgs.py

lint:
    uv run ruff check

fix:
    uv run ruff check --fix

format:
    uv run ruff format
