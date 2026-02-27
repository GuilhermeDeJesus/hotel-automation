# Teste Rápido de Webhook Twilio

Validação ponta a ponta em poucos passos.

## Passos

1. Inicie API:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

2. Inicie túnel:

```bash
ngrok http 8000
```

3. Configure Twilio Sandbox para:

`https://<url-publica>/webhook/whatsapp/twilio`

4. Envie mensagem no WhatsApp e valide resposta.

## Evidências

- Logs com marcador `[TWILIO]`.
- Requisição `200` no túnel.
