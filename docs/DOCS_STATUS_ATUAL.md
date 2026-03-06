# Status da Documentação (Mar/2026)

Este índice indica quais guias estão alinhados com a operação atual e quais são históricos.

## Guias operacionais principais (fonte de verdade)

- `README.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/QUICKSTART_TWILIO.md`
- `docs/QUICKSTART_META_WHATSAPP.md`
- `docs/TESTE_WEBHOOK.md`
- `docs/WEBHOOK_SETUP_TWILIO.md`
- `docs/CHECKLIST_PROXIMO_PASSOS.md`

## Guias de arquitetura e comportamento

- `docs/WHATSAPP_ORQUESTRACAO_GUIA.md`
- `docs/EXAMPLE_FLOW.md`
- `docs/ARQUITETURA_COMPLETA.md`
- `docs/MELHORIAS_ORQUESTRACAO_RESERVACAO.md` — passo a passo de melhorias (primeiro contato → checkout)

## Regras de domínio (Cursor Rules)

- `.cursor/rules/domain-reservation-rules.mdc` — regras de negócio da reserva (jornada do hóspede)

## Documentos de histórico/planejamento

- `docs/SAAS_MVP_4_FASES.md`
- `docs/FINAL_DELIVERY.md`
- `docs/REFACTOR_SUMMARY.md`
- `docs/CLEAN_ARCHITECTURE_REFACTOR.md`

## Convenções atuais de operação

- Fluxo padrão é Docker-first (`docker compose`).
- Túnel público recomendado via profile `tunnel` (ngrok em container).
- Redis armazena histórico de conversa e estado de fluxo `flow:<phone>` com TTL.
- Confirmar reserva depende de reserva já persistida em PostgreSQL.
