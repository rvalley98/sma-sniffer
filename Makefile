# SMA Sniffer — Setup- und Betriebs-Helfer.
# Schnellstart:  make install

COMPOSE ?= docker compose
PYTHON  ?= python3
SERVICE ?= sma-decoder

.DEFAULT_GOAL := help

.PHONY: help install check-deps env discover build up down restart logs ps test-inverter clean

help: ## Diese Übersicht anzeigen
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: check-deps ## Erstinstallation: .env anlegen, Geräte finden, konfigurieren, starten
	@if [ ! -f .env ]; then cp .env.example .env && echo "✓ .env aus Vorlage erstellt"; \
		else echo "• .env existiert bereits"; fi
	@echo ""
	@echo "→ Suche SMA-Geräte im Netzwerk ..."
	@$(MAKE) --no-print-directory discover || true
	@echo ""
	@echo "→ Bitte in .env eintragen: MQTT_HOST/USER/PASS und die Geräte-IPs"
	@echo "  (PV_IP, BATTERY_IP, INVERTER_PASSWORD) anhand der gefundenen Geräte oben."
	@if [ -t 0 ]; then \
		printf "  .env jetzt bearbeiten? [J/n] "; read ans; \
		case "$$ans" in n|N) ;; *) $${EDITOR:-nano} .env;; esac; \
	else echo "  (nicht-interaktiv — .env bitte manuell bearbeiten)"; fi
	@echo ""
	@echo "→ Container bauen und starten ..."
	@$(MAKE) --no-print-directory up
	@echo ""
	@echo "✓ Fertig. Live-Logs ansehen mit:  make logs"

check-deps: ## Prüfen, ob docker, docker compose und python3 vorhanden sind
	@command -v docker >/dev/null 2>&1 || { echo "✗ docker fehlt"; exit 1; }
	@$(COMPOSE) version >/dev/null 2>&1 || { echo "✗ 'docker compose' fehlt"; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "✗ python3 fehlt"; exit 1; }
	@echo "✓ docker, docker compose und python3 vorhanden"

env: ## .env aus .env.example anlegen (falls nicht vorhanden)
	@if [ ! -f .env ]; then cp .env.example .env && echo "✓ .env erstellt — bitte Werte eintragen"; \
		else echo "• .env existiert bereits"; fi

discover: ## SMA-Geräte mit LAN-IP und Typ finden:  make discover [PW=0000] [GROUP=user]
	@$(PYTHON) app/discover_speedwire.py $(or $(PW),0000) $(or $(GROUP),user)

build: ## Container-Image bauen
	$(COMPOSE) build

up: ## Container bauen und im Hintergrund starten
	$(COMPOSE) up -d --build

down: ## Container stoppen und entfernen
	$(COMPOSE) down

restart: ## Container neu starten
	$(COMPOSE) restart $(SERVICE)

logs: ## Live-Logs anzeigen (Strg+C zum Beenden)
	$(COMPOSE) logs -f $(SERVICE)

ps: ## Status der Container anzeigen
	$(COMPOSE) ps

test-inverter: ## Wechselrichter direkt testen:  make test-inverter IP=192.168.178.79
	@test -n "$(IP)" || { echo "Bitte IP angeben:  make test-inverter IP=<ip> [PW=0000] [GROUP=user]"; exit 1; }
	$(PYTHON) app/speedwire_data2.py $(IP) $(or $(PW),0000) $(or $(GROUP),user)

clean: ## Container, Image und Volumes entfernen
	$(COMPOSE) down --rmi local --volumes --remove-orphans
