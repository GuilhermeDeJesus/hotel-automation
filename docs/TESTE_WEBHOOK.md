# Teste Rápido de Webhook Twilio

Validação ponta a ponta em poucos passos.

## Passos

1. Suba stack com túnel ngrok:

```bash
docker compose --profile tunnel up -d --build
```

2. Obtenha URL pública:

```bash
curl -s http://localhost:4040/api/tunnels
```

3. Configure Twilio Sandbox para:

`https://<url-publica>/webhook/whatsapp/twilio`

4. Envie mensagem no WhatsApp e valide resposta.

## Evidências

- Logs com marcador `[TWILIO]`.
- Requisição `200` no túnel.

## Comandos úteis

```bash
make whatsapp-test
make logs
```

## Nota de depreciação

Fluxo manual `uvicorn` + `ngrok http 8000` foi substituído pelo fluxo Docker com profile `tunnel`.
