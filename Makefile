.PHONY: install test lint format run compose-up compose-down

install:
	asdf install
	uv sync --python "$$(asdf which python)" --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

run:
	uv run retail-mcp --transport http

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
