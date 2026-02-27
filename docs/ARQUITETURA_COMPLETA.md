# Arquitetura do Projeto

Este documento descreve a arquitetura atual do sistema.

## Camadas

### Domain (`app/domain`)
- Entidades e regras de negócio.
- Value objects e exceções de domínio.
- Interfaces de repositório.

### Application (`app/application`)
- Use cases: check-in, conversa, confirmação de reserva e tratamento de mensagem.
- Serviços de contexto de hotel e reserva.
- DTOs de entrada/saída.

### Infrastructure (`app/infrastructure`)
- SQLAlchemy para persistência.
- Redis para cache.
- OpenAI e clientes WhatsApp (Meta/Twilio).
- Logging técnico de conversas.

### Interfaces (`app/interfaces`)
- Rotas FastAPI de webhook.
- Conversão entre payload HTTP e DTOs.
- Injeção de dependências (`dependencies.py`).

## Fluxo principal

1. Webhook recebe mensagem.
2. `HandleWhatsAppMessageUseCase` escolhe o fluxo.
3. `ConversationUseCase` combina contexto de hotel + reserva.
4. OpenAI gera resposta.
5. Cliente de mensageria envia resposta ao usuário.

## Endpoints disponíveis

- `GET /webhook/whatsapp` (verificação Meta)
- `POST /webhook/whatsapp` (recebimento Meta)
- `POST /webhook/whatsapp/twilio` (recebimento Twilio)

## Pontos de atenção

- Ainda não existe endpoint dedicado de healthcheck.
- `app/main.py` contém comentários legados e pode ser simplificado.

## Guia detalhado de estudo

Para uma explicação didática (camada por camada, classe por classe, método por método), com fluxogramas e diagramas, consulte:

- `docs/EXAMPLE_FLOW.md`
