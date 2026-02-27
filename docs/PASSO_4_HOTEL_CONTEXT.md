# Hotel Context (Referência Atual)

Este recurso injeta informações do hotel no prompt da IA.

## Objetivo

Garantir respostas consistentes sobre horários, políticas e serviços.

## Como funciona

1. `HotelContextService` consulta hotel ativo no banco.
2. Serviço formata contexto textual.
3. `ConversationUseCase` combina contexto de hotel e reserva.
4. IA responde com base nesses dados.

## Pré-requisitos

- Migrations aplicadas.
- Dados de hotel semeados.
- Variáveis de ambiente configuradas.
