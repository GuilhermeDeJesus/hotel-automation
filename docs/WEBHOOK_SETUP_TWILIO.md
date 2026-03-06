# Setup do Webhook Twilio

Configuração mínima para Twilio chamar sua API.

## Endpoint de destino

`POST /webhook/whatsapp/twilio`

## Configuração

1. Subir stack com profile de túnel: `docker compose --profile tunnel up -d --build`.
2. Obter URL pública: `curl -s http://localhost:4040/api/tunnels`.
3. Configurar URL no Twilio Sandbox.
4. Definir método `HTTP POST`.

URL final esperada no Twilio:

`https://SEU_DOMINIO_NGROK/webhook/whatsapp/twilio`

## Validação

- Entrada de mensagem aparece nos logs.
- Resposta retorna ao usuário via WhatsApp.

## Nota de depreciação

Passo genérico de `ngrok` manual foi descontinuado na documentação principal em favor do fluxo Docker padronizado.
