# Setup do Webhook Twilio

Configuração mínima para Twilio chamar sua API.

## Endpoint de destino

`POST /webhook/whatsapp/twilio`

## Configuração

1. Subir API local.
2. Expor URL pública com ngrok.
3. Configurar URL no Twilio Sandbox.
4. Definir método `HTTP POST`.

## Validação

- Entrada de mensagem aparece nos logs.
- Resposta retorna ao usuário via WhatsApp.
