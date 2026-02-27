# Guia 100% do Projeto (Casos Reais de Hotel)

Este documento é o plano mestre para levar o projeto do estado atual até operação completa, cobrindo toda a jornada do hóspede:

- Pré-estadia
- Check-in
- Estadia
- Extensão de reserva
- Check-out
- Pós-estadia

## 1) Definição de “100% concluído”

O projeto será considerado 100% quando atender os quatro blocos abaixo:

1. **Produto**: fluxos críticos implementados (confirmar, check-in, extensão, check-out, cancelamento, no-show).
2. **Operação**: monitoramento, saúde, logs, fallback e playbooks de incidente.
3. **Qualidade**: cobertura de testes unitários e integração dos fluxos principais.
4. **Negócio**: onboarding replicável + clientes ativos com métricas de retenção.

## 2) Estado atual (baseado no código)

### Já implementado

- Webhooks Meta e Twilio (`/webhook/whatsapp` e `/webhook/whatsapp/twilio`).
- Conversa com IA + contexto de hotel e de reserva.
- Fluxo de confirmação de reserva (SIM/NÃO/EDITAR).
- Edição de quarto dentro do fluxo de confirmação (com busca de disponibilidade).
- Check-in via mensagem.
- Camada de domínio com estados de reserva (`PENDING`, `CONFIRMED`, `CHECKED_IN`, `CHECKED_OUT`, `CANCELLED`, `NO_SHOW`).

### Parcial / pendente

- Alteração de datas (a resposta existe, mas o fluxo está pendente).
- Extensão de reserva (não implementado como caso de uso completo).
- Check-out via WhatsApp (domínio suporta, mas falta use case + orquestração).
- Cancelamento operacional via fluxo guiado (além de resposta genérica).
- No-show automatizado (regra existe no domínio, sem job operacional dedicado).

## 3) Jornada real do hóspede (fim a fim)

## 3.1 Pré-estadia

### Caso A — Perguntas frequentes do hotel

**Exemplos reais**
- “Qual horário de check-in?”
- “Vocês aceitam pets?”
- “Tem estacionamento?”

**Comportamento esperado**
1. Bot responde com contexto do hotel.
2. Mensagem consistente com políticas cadastradas.

**Status**: Implementado (via `ConversationUseCase` + `HotelContextService`).

### Caso B — Confirmação de reserva

**Exemplos reais**
- “Quero confirmar minha reserva.”
- “Confirmar booking.”

**Comportamento esperado**
1. Bot mostra resumo da reserva.
2. Cliente responde `SIM`, `NÃO` ou `EDITAR`.
3. Se `SIM`, status vira `CONFIRMED`.

**Status**: Implementado.

### Caso C — Alterar quarto antes da chegada

**Exemplos reais**
- “Quero editar.”
- “Trocar quarto.”

**Comportamento esperado**
1. Bot lista quartos disponíveis para o período da reserva.
2. Cliente escolhe o quarto.
3. Reserva é atualizada e confirmada.

**Status**: Implementado.

### Caso D — Alterar datas antes da chegada

**Comportamento esperado**
1. Bot coleta novas datas.
2. Valida disponibilidade.
3. Atualiza stay period, recalcula valor e pede confirmação final.

**Status**: Pendente.

## 3.2 Chegada (check-in)

### Caso E — Check-in no dia da entrada

**Exemplos reais**
- “Fazer check-in.”
- “Checkin agora.”

**Comportamento esperado**
1. Bot identifica reserva por telefone.
2. Valida status e regras do período.
3. Executa check-in e confirma ao hóspede.

**Status**: Implementado (com cache).

## 3.3 Durante estadia

### Caso F — Dúvidas e suporte de hospedagem

**Exemplos reais**
- “Qual senha do Wi-Fi?”
- “Até que horas funciona o restaurante?”

**Comportamento esperado**
1. Bot usa histórico da conversa.
2. Usa contexto de hotel e reserva para responder.

**Status**: Implementado (depende da qualidade dos dados no hotel/contexto).

## 3.4 Extensão de reserva

### Caso G — Estender estadia (1 ou mais noites)

**Exemplos reais**
- “Quero ficar mais 2 dias.”
- “Posso estender até domingo?”

**Comportamento esperado (100%)**
1. Bot identifica reserva ativa (`CHECKED_IN` ou `CONFIRMED`).
2. Coleta nova data de saída.
3. Verifica disponibilidade do quarto atual.
4. Se indisponível, oferece mudança de quarto.
5. Recalcula total e pede confirmação.
6. Atualiza reserva e registra histórico.

**Status**: Pendente.

## 3.5 Saída (check-out)

### Caso H — Check-out via WhatsApp

**Exemplos reais**
- “Quero fazer checkout.”
- “Encerrar hospedagem.”

**Comportamento esperado (100%)**
1. Bot valida que a reserva está `CHECKED_IN`.
2. Executa check-out.
3. Opcional: confirma pendências financeiras e envia resumo final.
4. Marca status `CHECKED_OUT`.

**Status**: Pendente (domínio pronto, falta caso de uso e fluxo).

## 3.6 Pós-estadia

### Caso I — No-show e encerramento operacional

**Comportamento esperado (100%)**
1. Job diário identifica reservas `CONFIRMED` com check-in vencido.
2. Marca como `NO_SHOW` conforme regra.
3. Registra no log para acompanhamento.

**Status**: Pendente.

## 4) Variedades reais de hotel (configuração de produto)

Para suportar diferentes perfis de hotel/pousada, padronize as seguintes variações:

1. **Políticas**
   - Check-in/check-out flexível
   - Pets permitido/restrito
   - Crianças por faixa etária
   - Regras de cancelamento por antecedência

2. **Quartos**
   - Tipos (`SINGLE`, `DOUBLE`, `SUITE`, etc.)
   - Capacidade máxima
   - Faixa de tarifa por categoria

3. **Serviços e amenidades**
   - Wi-Fi, estacionamento, academia, piscina, restaurante
   - Horários de operação

4. **Regras comerciais**
   - Early check-in / late check-out
   - Regras de extensão de estadia
   - Política de overbooking (se aplicável)

## 5) Implementação para chegar a 100% (passo a passo)

## Fase 1 — Fechar lacunas de jornada (core)

### 5.1 Alteração de datas

**Criar/ajustar**
- `app/application/use_cases/confirm_reservation.py`
- `app/application/use_cases/handle_whatsapp_message.py`
- `app/domain/entities/reservation/stay_period.py` (reuso de regras)
- `app/infrastructure/persistence/sql/room_repository_sql.py` (validação de disponibilidade)

**Regras mínimas**
1. Nova data de saída deve ser > check-in.
2. Não permitir datas inválidas/passadas conforme política.
3. Recalcular total da reserva.

**Critério de aceite**
- Cliente consegue alterar datas por WhatsApp e receber confirmação final.

### 5.2 Extensão de reserva

**Criar**
- `app/application/use_cases/extend_reservation.py`
- DTOs em `app/application/dto/` para solicitação e resposta da extensão

**Ajustar**
- `app/application/use_cases/handle_whatsapp_message.py` para rotear intenção de extensão

**Regras mínimas**
1. Permitir extensão para reserva ativa.
2. Validar disponibilidade do quarto atual.
3. Oferecer quarto alternativo se necessário.
4. Confirmar novo total e datas.

**Critério de aceite**
- “Quero ficar mais X noites” deve atualizar reserva com segurança.

### 5.3 Check-out

**Criar**
- `app/application/use_cases/checkout_via_whatsapp.py`
- DTOs de checkout em `app/application/dto/`

**Ajustar**
- `app/application/use_cases/handle_whatsapp_message.py` para reconhecer intenção de checkout

**Regras mínimas**
1. Só permitir checkout se status `CHECKED_IN`.
2. Persistir `checked_out_at`.
3. Retornar mensagem de fechamento.

**Critério de aceite**
- Comando de checkout altera status para `CHECKED_OUT`.

## Fase 2 — Robustez operacional

### 5.4 Healthcheck e readiness

**Criar**
- Endpoint `/health` e `/ready` (ou equivalente)

**Critério de aceite**
- Validação de API + dependências principais (DB/Redis).

### 5.5 Observabilidade

**Implementar**
- Correlação por `phone`/`message_id`
- Logs estruturados por fluxo
- Alertas para erro de integração (OpenAI/Meta/Twilio)

### 5.6 Jobs operacionais

**Implementar**
- Job de no-show
- Limpeza/rotação de cache

## Fase 3 — Qualidade e testes

### 5.7 Testes unitários novos

Criar testes para:
1. confirmação com edição de quarto
2. alteração de datas
3. extensão de reserva
4. checkout
5. no-show

### 5.8 Testes de integração

Validar:
1. webhook Meta ponta a ponta
2. webhook Twilio ponta a ponta
3. persistência correta de status em cada etapa da jornada

## 6) Playbook de mensagens (UX real)

## 6.1 Intenções de entrada (exemplos)

- Confirmar reserva: “confirmar reserva”, “confirm booking”
- Check-in: “fazer check-in”, “checkin”
- Extensão: “quero ficar mais 2 dias”, “estender estadia”
- Check-out: “quero fazer checkout”, “encerrar hospedagem”
- Cancelamento: “cancelar reserva”

## 6.2 Respostas padrão recomendadas

1. Sempre confirmar ação crítica com resumo.
2. Sempre oferecer próximo passo claro (“Responda SIM/NÃO”).
3. Em erro, devolver orientação acionável (não só mensagem técnica).

## 7) Métricas para considerar o projeto “100% em produção”

Metas sugeridas (ajuste conforme estratégia):

1. 95%+ de mensagens processadas sem falha técnica.
2. 80%+ de resoluções sem atendimento humano em dúvidas comuns.
3. Fluxos críticos (confirmar/check-in/extensão/check-out) com sucesso > 90%.
4. Tempo médio de primeira resposta dentro da meta operacional do hotel.

## 8) Checklist final de conclusão

## Produto
- [ ] Confirmação de reserva completa
- [ ] Check-in completo
- [ ] Extensão de reserva completa
- [ ] Check-out completo
- [ ] Cancelamento operacional completo
- [ ] No-show automatizado

## Operação
- [ ] Health/readiness
- [ ] Logs estruturados
- [ ] Alertas em integrações críticas
- [ ] Playbook de incidentes

## Qualidade
- [ ] Testes unitários dos fluxos críticos
- [ ] Testes de integração de webhook
- [ ] Cenários de regressão documentados

## Negócio
- [ ] Onboarding padrão de hotel
- [ ] Métricas de retenção e uso ativas
- [ ] Processo comercial replicável

## 9) Próxima ação recomendada

Começar por **extensão de reserva + checkout**, pois fecha a jornada fim a fim do hóspede e gera o maior salto para “produto completo”.