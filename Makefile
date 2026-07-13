.PHONY: install dev test lint format serve clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src/
	mypy src/

format:
	ruff format src/

serve:
	uvicorn src.api.main:app --reload --port 8000

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
