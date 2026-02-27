# Guia Meta WhatsApp Cloud API

Guia enxuto para integrar o webhook Meta no projeto.

## Endpoints usados

- `GET /webhook/whatsapp` (verificação)
- `POST /webhook/whatsapp` (eventos)

## Variáveis obrigatórias

```env
META_ACCESS_TOKEN=...
PHONE_NUMBER_ID=...
WEBHOOK_VERIFY_TOKEN=...
```

## Configuração no Meta

1. Configurar callback URL para `https://<dominio>/webhook/whatsapp`.
2. Configurar verify token igual ao `.env`.
3. Assinar ao menos o campo `messages`.

## Teste rápido

1. Subir API local.
2. Expor com ngrok.
3. Configurar webhook.
4. Enviar mensagem e validar resposta.
