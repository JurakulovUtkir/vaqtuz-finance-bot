.PHONY: help build up down restart logs ps shell test backup restore

BACKUP_DIR ?= backups
STAMP := $(shell date +%Y%m%d-%H%M%S)

help:
	@echo "make build    - Docker image'ni yig'ish"
	@echo "make up       - botni fonda ishga tushirish"
	@echo "make down     - to'xtatish"
	@echo "make restart  - qayta ishga tushirish"
	@echo "make logs     - jonli log'lar"
	@echo "make ps       - holat"
	@echo "make shell    - konteyner ichiga kirish"
	@echo "make test     - testlarni ishga tushirish"
	@echo "make backup   - bazani $(BACKUP_DIR)/ ga nusxalash"
	@echo "make restore FILE=... - bazani zaxiradan tiklash"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

shell:
	docker compose exec bot sh

test:
	python3 -m pytest -q

backup:
	@mkdir -p $(BACKUP_DIR)
	docker compose cp bot:/data/payments.db $(BACKUP_DIR)/payments-$(STAMP).db
	@echo "✅ $(BACKUP_DIR)/payments-$(STAMP).db"

restore:
	@test -n "$(FILE)" || (echo "Ishlatish: make restore FILE=backups/payments-....db" && exit 1)
	docker compose stop bot
	docker compose cp $(FILE) bot:/data/payments.db
	docker compose start bot
	@echo "✅ Tiklandi: $(FILE)"
