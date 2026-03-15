.PHONY: up up-tunnel up-all down logs ngrok-url migrate unit integration e2e whatsapp-test seed-saas mark-no-show phase2-1 phase2-3 snapshot-audit snapshot-audit-backfill snapshot-audit-gaps snapshot-audit-repair snapshot-audit-repair-dry-run frontend clean-for-testing

up:
	docker compose up -d --build app db redis

up-all:
	docker compose up -d --build app db redis frontend

frontend:
	docker compose up -d --build frontend

up-tunnel:
	docker compose --profile tunnel up -d --build

down:
	docker compose --profile tunnel down

logs:
	docker compose logs -f app ngrok

ngrok-url:
	curl -s http://localhost:4040/api/tunnels

migrate:
	docker compose run --rm app alembic upgrade head

unit:
	docker compose run --rm --build unit-tests sh -c "alembic upgrade head && python -m pytest tests/unit -q"

integration:
	docker compose run --rm --build integration-tests sh -c "alembic upgrade head && python -m pytest tests/integration -q"

e2e:
	docker compose run --rm --build integration-tests sh -c "alembic upgrade head && python -m pytest tests/integration/test_business_e2e_postgres_redis_real.py -vv"

seed-saas:
	docker compose exec -T app python scripts/seed_saas_metrics.py

mark-no-show:
	docker compose exec -T app python scripts/mark_no_show.py $(if $(DATE),--date $(DATE),)

phase2-1:
	docker compose run --rm --build integration-tests sh -c "alembic upgrade head && python -m pytest tests/integration/test_saas_dashboard_endpoints.py -vv"

phase2-3:
	docker compose run --rm --build integration-tests sh -c "alembic upgrade head && python -m pytest tests/integration/test_saas_dashboard_endpoints.py -vv"

snapshot-audit:
	docker compose exec -T app python scripts/generate_audit_metrics_snapshot.py $(if $(DATE),--date $(DATE),)

snapshot-audit-backfill:
	docker compose exec -T app python scripts/generate_audit_metrics_snapshot.py --backfill-from $(FROM) --backfill-to $(TO) $(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE),) $(if $(SUMMARY_ONLY),--summary-only,) $(if $(REQUEST_ID),--request-id $(REQUEST_ID),)

snapshot-audit-gaps:
	docker compose exec -T app python scripts/generate_audit_metrics_snapshot.py --gaps-from $(FROM) --gaps-to $(TO)

snapshot-audit-repair:
	docker compose exec -T app python scripts/generate_audit_metrics_snapshot.py --repair-from $(FROM) --repair-to $(TO) $(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE),) $(if $(SUMMARY_ONLY),--summary-only,) $(if $(REQUEST_ID),--request-id $(REQUEST_ID),)

snapshot-audit-repair-dry-run:
	docker compose exec -T app python scripts/generate_audit_metrics_snapshot.py --repair-from $(FROM) --repair-to $(TO) --repair-dry-run $(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE),) $(if $(SUMMARY_ONLY),--summary-only,) $(if $(REQUEST_ID),--request-id $(REQUEST_ID),)

limpa-cache-redis:
	docker compose exec -T redis redis-cli FLUSHDB && docker compose exec -T redis redis-cli DBSIZE

clean-for-testing:
	docker compose run --rm --build app python scripts/clean_for_testing.py

whatsapp-test: up-tunnel ngrok-url
	@echo ""
	@echo "Configure no Twilio Sandbox:"
	@echo "https://SEU_NGROK_URL/webhook/whatsapp/twilio"
	@echo ""
	@echo "Use 'make logs' para acompanhar app/ngrok em tempo real."

flow-debug:
	@echo "Iniciando flow debug terminal (Redis + Postgres)..."
	docker compose exec app python scripts/flow_debug_terminal.py
