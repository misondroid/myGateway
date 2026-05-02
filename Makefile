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

# NAT 断片を生成（サーバで compose 起動後、ネットワーク名が一致すること）
rules:
	@$(MAKE) -s rules-check-venv
	.venv/bin/python scripts/create_rules.py -o services/host/nat.generated.rules
.PHONY: rules

restore-rules:
	@test -f services/host/nat.generated.rules && cp services/host/nat.generated.rules /tmp/nat.rules && sudo iptables-restore /tmp/nat.rules && sudo ufw reload
.PHONY: restore-rules

rules-check-venv:
	@test -x .venv/bin/python || (echo "run: python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt" >&2; exit 1)
.PHONY: rules-check-venv