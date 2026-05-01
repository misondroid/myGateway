build:
	docker compose build
.PHONY: build

up:
	docker compose up -d
.PHONY: up

down:
	docker compose down
.PHONY: down
restart:
	docker compose down && docker compose up -d
.PHONY: restart
logs:
	docker compose logs -f
.PHONY: logs