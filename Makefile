.PHONY: up down api-test api-lint web-test web-lint check

up:
	docker compose up -d db

down:
	docker compose down

api-test:
	cd apps/api && pytest

api-lint:
	cd apps/api && ruff check .

web-test:
	cd apps/web && npm test -- --run

web-lint:
	cd apps/web && npm run lint

check: api-lint api-test web-lint web-test
