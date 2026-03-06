# Melhorias da Orquestração de Reserva — Passo a Passo

Este documento descreve as melhorias necessárias na orquestração dos casos de uso para cobrir a jornada completa do hóspede: **do primeiro contato até o checkout**. Cada passo é explicado com clareza e simplicidade.

---

## Índice

1. [Análise da situação atual](#1-análise-da-situação-atual)
2. [Lacunas identificadas](#2-lacunas-identificadas)
3. [Passo a passo das melhorias](#3-passo-a-passo-das-melhorias)
4. [Ordem recomendada de implementação](#4-ordem-recomendada-de-implementação)
5. [Documentos relacionados](#5-documentos-relacionados)
6. [Sugestões de evolução para automação total](#6-sugestões-de-evolução-para-automação-total)

---

## 1. Análise da situação atual

### 1.1 Fluxo atual (o que existe hoje)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MENSAGEM WHATSAPP                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  HandleWhatsAppMessageUseCase.execute()                                      │
│  - Verifica flow_state (cache)                                               │
│  - Se fluxo de confirmação ativo → _handle_confirm_reservation_flow         │
│  - Se "confirmar reserva" → _start_confirm_reservation_flow                   │
│  - Se "check-in" ou "checkin" → CheckInViaWhatsAppUseCase                   │
│  - Se "reserva" ou "booking" → ConversationUseCase (IA)                      │
│  - Caso contrário → ConversationUseCase (IA)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 O que funciona

| Fluxo | Status | Observação |
|-------|--------|------------|
| Confirmação de reserva (SIM/NÃO/EDITAR) | ✅ | Só para reservas **já existentes** |
| Troca de quarto no fluxo de confirmação | ⚠️ | Funciona, mas **viola domínio** (mutação direta) |
| Check-in | ⚠️ | Funciona, mas cache tem **bug** (retorna sucesso sem executar) |
| Conversa com IA | ✅ | Responde perguntas, mas **não cria reserva** |
| Alteração de datas | ❌ | Mensagem fixa "não disponível" |
| Check-out | ❌ | Domínio pronto, **sem use case nem orquestração** |
| Cancelamento | ❌ | Domínio pronto, **sem fluxo guiado** |
| Extensão de reserva | ❌ | **Não implementado** |
| Criação de reserva | ❌ | **Não existe** — IA só responde texto, não persiste |

### 1.3 Problemas críticos

1. **Não há fluxo de criação de reserva**  
   Quando o hóspede diz "quero fazer uma reserva" ou envia datas, a IA responde com texto (disponibilidade, preços), mas **nenhuma reserva é criada no sistema**. As reservas hoje vêm apenas de seed manual ou inserção direta no banco.

2. **Mutação fora do domínio**  
   Em `_handle_room_selection`, o código faz:
   ```python
   reservation.room_number = selected_room
   reservation_repository.save(reservation)
   ```
   A troca de quarto deveria ser um método de domínio (`reservation.change_room(room_number)`), com validação de disponibilidade.

3. **Bug no cache de check-in**  
   O `CheckInViaWhatsAppUseCase` verifica cache e, se encontrar algo, retorna "Check-in feito com sucesso!" **sem executar** `reservation.check_in()`. O cache parece armazenar dados da reserva, não o resultado do check-in — a lógica está incorreta.

4. **ConfirmReservationUseCase expõe repositório**  
   O `HandleWhatsAppMessageUseCase` acessa `confirm_reservation_use_case.reservation_repository` diretamente. O use case não deveria expor dependências internas.

5. **Check-out e cancelamento sem orquestração**  
   O domínio tem `check_out()` e `cancel()`, mas não há use cases nem roteamento no `HandleWhatsAppMessageUseCase`.

6. **Pagamento não está integrado à jornada**  
   Existe entidade de domínio `Payment` e tabela `payments`, mas o fluxo atual de reserva não considera pagamento em nenhum momento (nem como obrigatório, nem como opcional). Hoje, na prática, **toda reserva é \"de graça\"** do ponto de vista do sistema: não há status financeiro nem regras ligando confirmação de reserva a pagamento.

---

## 2. Lacunas identificadas

| Lacuna | Impacto | Prioridade |
|--------|--------|------------|
| Criação de reserva | Jornada incompleta — primeiro contato não gera reserva | Alta |
| Check-out | Hóspede não consegue encerrar estadia via WhatsApp | Alta |
| Pagamento e confirmação financeira | Reserva não considera pagamento, risco operacional alto | Alta |
| Troca de quarto no domínio | Viola Clean Architecture, difícil evoluir | Média |
| Bug do cache de check-in | Pode retornar sucesso falso | Alta |
| Cancelamento guiado | Hóspede não cancela de forma guiada | Média |
| Extensão de reserva | Não é possível estender estadia | Média |
| Alteração de datas | Fluxo inexistente | Média |
| Encapsulamento do ConfirmReservationUseCase | Acoplamento desnecessário | Baixa |

---

## 3. Passo a passo das melhorias

### Passo 1 — Corrigir bug do cache de check-in

**Objetivo:** O cache não deve substituir a execução do check-in.

**Problema atual:** Se existir chave no cache para o telefone, o use case retorna sucesso sem chamar `reservation.check_in()`.

**Solução:**

1. Definir o propósito do cache:  
   - Opção A: cache de **resultado** de check-in (evitar repetição) — nesse caso, a chave deve ser algo como `checkin_done:{phone}` e só ser setada **após** check-in bem-sucedido.  
   - Opção B: remover cache de check-in — sempre executar no repositório.

2. Se manter cache (Opção A):
   - Usar chave `checkin_done:{phone}` com TTL (ex.: 24h).
   - Só gravar após `reservation.check_in()` e `save()`.
   - Na leitura, se existir `checkin_done:{phone}`, retornar mensagem tipo "Você já realizou o check-in."

3. **Arquivos:** `app/application/use_cases/checkin_via_whatsapp.py`

**Critério de aceite:** Check-in sempre executa `reservation.check_in()` quando há reserva válida; cache não retorna sucesso sem ter executado.

---

### Passo 2 — Mover troca de quarto para o domínio

**Objetivo:** A alteração de quarto deve ser uma operação de domínio, não mutação direta no use case.

**O que fazer:**

1. Em `Reservation`, criar método:
   ```python
   def change_room(self, room_number: str) -> None:
       """Altera quarto. Só permitido antes do check-in."""
       if self.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
           raise InvalidRoomChangeState("Só é possível trocar quarto antes do check-in.")
       if self.status == ReservationStatus.CHECKED_IN:
           raise InvalidRoomChangeState("Já fez check-in.")
       self.room_number = room_number
   ```

2. Adicionar exceção `InvalidRoomChangeState` em `app/domain/exceptions.py`.

3. No `HandleWhatsAppMessageUseCase._handle_room_selection`:
   - Antes de chamar o domínio, validar com `RoomRepository.is_available(selected_room, start, end)`.
   - Chamar `reservation.change_room(selected_room)` em vez de `reservation.room_number = selected_room`.
   - Persistir com `reservation_repository.save(reservation)`.

4. **Arquivos:**  
   - `app/domain/entities/reservation/reservation.py`  
   - `app/domain/exceptions.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`

**Critério de aceite:** Troca de quarto passa por método de domínio; use case não muta `room_number` diretamente.

---

### Passo 3 — Encapsular ConfirmReservationUseCase

**Objetivo:** O orquestrador não deve acessar o repositório através do use case de confirmação.

**O que fazer:**

1. No `ConfirmReservationUseCase`, adicionar método:
   ```python
   def get_formatted_summary_for_phone(self, phone: str) -> str | None:
       """Retorna resumo formatado ou None se não houver reserva."""
       reservation = self.reservation_repository.find_by_phone_number(phone)
       if not reservation:
           return None
       return self.get_formatted_summary(reservation)
   ```

2. No `HandleWhatsAppMessageUseCase._start_confirm_reservation_flow`:
   - Trocar a chamada direta ao repositório por `confirm_reservation_use_case.get_formatted_summary_for_phone(phone)`.

3. No `_handle_edit_choice` e `_handle_room_selection`, o orquestrador precisa de reserva e quartos disponíveis. Duas opções:
   - **A)** Adicionar métodos no `ConfirmReservationUseCase`: `get_reservation_for_edit(phone)` e `get_available_rooms_for_reservation(phone)` que encapsulam a lógica.
   - **B)** Injetar `ReservationRepository` e `RoomRepository` no `HandleWhatsAppMessageUseCase` (já existe `RoomRepository`). O problema é o uso de `confirm_reservation_use_case.reservation_repository` — isso pode ser resolvido injetando `ReservationRepository` no orquestrador e removendo o acesso ao use case interno.

4. Decisão recomendada: o `HandleWhatsAppMessageUseCase` já recebe `room_repository`. Para reserva, injetar `ReservationRepository` e usá-lo diretamente no orquestrador, em vez de acessar via `confirm_reservation_use_case`. Assim, cada use case mantém suas dependências encapsuladas.

5. **Arquivos:**  
   - `app/application/use_cases/confirm_reservation.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`  
   - `app/interfaces/dependencies.py` (verificar se `ReservationRepository` já é injetado no orquestrador)

**Critério de aceite:** Nenhum use case expõe repositório para outro use case; orquestrador usa suas próprias dependências.

---

### Passo 4 — Implementar CheckoutViaWhatsAppUseCase

**Objetivo:** Permitir check-out via WhatsApp.

**O que fazer:**

1. Criar DTOs em `app/application/dto/`:
   - `CheckoutRequestDTO(phone: str)`
   - `CheckoutResponseDTO(message: str, success: bool, error: str | None = None)`

2. Criar `app/application/use_cases/checkout_via_whatsapp.py`:
   ```python
   class CheckoutViaWhatsAppUseCase:
       def __init__(self, reservation_repository: ReservationRepository):
           self.reservation_repository = reservation_repository

       def execute(self, request_dto: CheckoutRequestDTO) -> CheckoutResponseDTO:
           reservation = self.reservation_repository.find_by_phone_number(request_dto.phone)
           if not reservation:
               return CheckoutResponseDTO(message="Nenhuma reserva encontrada.", success=False)
           try:
               reservation.check_out()
               self.reservation_repository.save(reservation)
               return CheckoutResponseDTO(message="Check-out realizado com sucesso!", success=True)
           except InvalidCheckOutState as e:
               return CheckoutResponseDTO(message=str(e), success=False, error=str(e))
   ```

3. No `HandleWhatsAppMessageUseCase`:
   - Injetar `CheckoutViaWhatsAppUseCase`.
   - Detectar intenção de check-out (ex.: "checkout", "check-out", "encerrar hospedagem").
   - Chamar `checkout_use_case.execute(CheckoutRequestDTO(phone=phone))`.

4. Registrar no `dependencies.py` e injetar no orquestrador.

5. **Arquivos:**  
   - `app/application/dto/checkout_request_dto.py`  
   - `app/application/dto/checkout_response_dto.py`  
   - `app/application/use_cases/checkout_via_whatsapp.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`  
   - `app/interfaces/dependencies.py`

**Critério de aceite:** Mensagem "quero fazer checkout" executa `reservation.check_out()` e persiste; resposta amigável em caso de erro.

---

### Passo 5 — Implementar CancelReservationUseCase e fluxo guiado

**Objetivo:** Permitir cancelamento guiado via WhatsApp.

**O que fazer:**

1. Criar `CancelReservationUseCase`:
   - `prepare_cancellation(phone)` → retorna resumo e `can_cancel`
   - `cancel(phone)` → chama `reservation.cancel()` e persiste

2. Criar fluxo no `HandleWhatsAppMessageUseCase`:
   - Detectar intenção "cancelar reserva".
   - Iniciar fluxo com confirmação (SIM/NÃO).
   - Usar `flow_state` com `action: "cancel_reservation"`.

3. **Arquivos:**  
   - `app/application/use_cases/cancel_reservation.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`  
   - `app/interfaces/dependencies.py`

**Critério de aceite:** Fluxo "cancelar reserva" → confirmação → `reservation.cancel()` quando usuário confirma.

---

### Passo 6 — Implementar CreateReservationUseCase (núcleo da jornada)

**Objetivo:** Criar reserva a partir da conversa (datas, quarto, nome).

**Desafio:** A IA hoje só gera texto. É preciso um fluxo **determinístico** que colete dados e persista — e que consiga, depois, se conectar com pagamento.

**Abordagem recomendada (fluxo guiado):**

1. Detectar intenção de nova reserva (ex.: "fazer reserva", "quero reservar", "reservar quarto").

2. Iniciar fluxo com estados:
   - `awaiting_dates` → coleta check-in e check-out
   - `awaiting_room_choice` → lista quartos disponíveis, usuário escolhe
   - `awaiting_name` → coleta nome do hóspede
   - `awaiting_confirmation` → mostra resumo, SIM/NÃO

3. Criar `CreateReservationUseCase`:
   - `check_availability(check_in, check_out)` → retorna quartos disponíveis
   - `create(dates, room_number, guest_name, phone)` → cria `Reservation` (PENDING), persiste

4. O fluxo usa `RoomRepository.find_available` e `ReservationRepository.save`.

5. **Arquivos:**  
   - `app/application/use_cases/create_reservation.py`  
   - `app/application/use_cases/handle_whatsapp_message.py` (novo fluxo)  
   - `app/application/dto/create_reservation_request_dto.py`  
   - `app/domain/entities/reservation/reservation.py` (factory ou construtor para nova reserva)

**Critério de aceite:** Fluxo guiado coleta datas, quarto e nome; cria reserva PENDING; hóspede pode em seguida confirmar — com ou sem pagamento, dependendo da regra de negócio (ver Passo 10).

**Alternativa:** Manter IA na coleta inicial e adicionar um "webhook" ou parser que, quando a IA identificar datas + quarto + nome, chame `CreateReservationUseCase`. Isso é mais complexo e menos determinístico.

---

### Passo 7 — Implementar alteração de datas no fluxo de confirmação

**Objetivo:** Permitir alterar datas no fluxo EDITAR.

**O que fazer:**

1. Em `Reservation`, criar `change_dates(new_period: StayPeriod)`:
   - Validar que status permite (PENDING ou CONFIRMED).
   - Validar que novo período é válido.
   - Atualizar `stay_period` e recalcular `total_amount` (via `RoomRepository.get_by_number` para obter diária).

2. No `_handle_edit_choice`, quando usuário escolhe "DATAS":
   - Ir para `awaiting_new_dates`.
   - Coletar novas datas (formato DD/MM/AAAA).
   - Validar com `RoomRepository.is_available(room_number, new_start, new_end)`.
   - Chamar `reservation.change_dates(StayPeriod(new_start, new_end))`.
   - Recalcular total e pedir confirmação.

3. **Arquivos:**  
   - `app/domain/entities/reservation/reservation.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`

**Critério de aceite:** No fluxo EDITAR → DATAS, usuário informa novas datas, sistema valida e atualiza reserva.

---

### Passo 8 — Implementar ExtendReservationUseCase

**Objetivo:** Permitir estender estadia durante a hospedagem.

**O que fazer:**

1. Em `Reservation`, criar `extend_stay(new_checkout: date)`:
   - Só se `status in (CONFIRMED, CHECKED_IN)`.
   - `new_checkout` deve ser > `stay_period.end`.
   - Validar disponibilidade do quarto atual para o período estendido.
   - Atualizar `stay_period` e `total_amount`.

2. Criar `ExtendReservationUseCase`:
   - `prepare_extension(phone)` → retorna reserva ativa e data atual de saída
   - `extend(phone, new_checkout)` → chama `reservation.extend_stay(new_checkout)` e persiste

3. No orquestrador, detectar intenção ("estender", "ficar mais X dias") e iniciar fluxo guiado.

4. **Arquivos:**  
   - `app/domain/entities/reservation/reservation.py`  
   - `app/application/use_cases/extend_reservation.py`  
   - `app/application/use_cases/handle_whatsapp_message.py`

**Critério de aceite:** Hóspede com reserva ativa consegue estender datas e o sistema atualiza período e valor.

---

### Passo 9 — Job de No-show (opcional, operacional)

**Objetivo:** Marcar automaticamente reservas CONFIRMED como NO_SHOW quando a data de check-in passou.

**O que fazer:**

1. Criar script ou job (ex.: cron):
   - Buscar reservas com `status=CONFIRMED` e `check_in_date < hoje`.
   - Para cada uma, chamar `reservation.mark_as_no_show()` e persistir.

2. **Arquivos:**  
   - `scripts/mark_no_show.py` ou similar  
   - Pode usar `ReservationRepository` com método `find_confirmed_past_checkin_date()` se necessário

**Critério de aceite:** Job diário marca reservas não utilizadas como NO_SHOW.

---

### Passo 10 — Planejar e integrar pagamentos na jornada de reserva

**Objetivo:** Permitir que o hóspede faça reserva **com pagamento**, de forma realista para a operação do hotel, começando simples e evoluindo depois.

---

#### 10.1 Visão de negócio (como o hóspede enxerga)

Fluxo ideal na cabeça do hóspede:

1. \"Quero reservar\" → bot coleta **datas**, **tipo de quarto** e **nome**.
2. Bot mostra **resumo da reserva** (datas, quarto, valor total, política).
3. Bot oferece opções:
   - **Confirmar e pagar agora** (link ou instrução de pagamento).
   - **Reservar sem pagamento imediato** (casos em que o hotel permite).
4. Ao pagar (ou o hotel confirmar manualmente o pagamento), a reserva fica **CONFIRMED** e o hóspede recebe mensagem de confirmação.

---

#### 10.2 Modelo de pagamento recomendado (MVP realista)

Em vez de começar diretamente com integração pesada de gateway, é mais realista seguir por **fases**, alinhadas ao dia a dia de hotéis/pousadas:

- **Fase 0 — Pagamento manual / comprovante**  
  - O sistema cria a reserva `PENDING`.  
  - O bot envia instruções (PIX, TED, link fixo de checkout do hotel, etc.).  
  - O hóspede envia comprovante ou o time do hotel confirma pagamento em um sistema externo (ou painel simples futuro).  
  - Alguém do hotel muda o status para `CONFIRMED` (manual) — por enquanto, fora deste backend, ou via script/painel futuro.

- **Fase 1 — Link de pagamento simples (sem webhook)**  
  - Integração leve com um provedor (ex.: Stripe, Pagar.me, Asaas, Mercado Pago, etc.) apenas para **gerar link de pagamento**.  
  - O backend chama o provedor, recebe uma URL e o bot envia essa URL para o hóspede.  
  - A confirmação de pagamento ainda pode ser manual (hotel verifica no painel do provedor) e, ao ver \"pago\", troca a reserva para `CONFIRMED`.

- **Fase 2 — Integração completa com webhook e entidade Payment**  
  - Usar a entidade `Payment` já existente no domínio (`app/domain/entities/payment/payment.py`) e a tabela `payments`.  
  - Quando o hotel quer cobrar online, o sistema cria um `Payment` ligado à `Reservation` e chama o provedor para criar a cobrança.  
  - O provedor chama um **webhook de pagamento** no backend; o backend então:
    - Marca o `Payment` como `APPROVED`/`REJECTED`/`EXPIRED`.  
    - Atualiza a reserva conforme regras de domínio (ex.: pagamento aprovado → permitir `confirm()`; expirado ou rejeitado → opcionalmente cancelar ou manter `PENDING`).

Essa evolução permite começar a operar rapidamente (Fase 0), sem travar o produto em decisões de gateway, e ir sofisticando quando houver mais tração.

---

#### 10.3 Regras de negócio entre reserva e pagamento

Recomendações de regra (podem virar Cursor Rules depois, no domínio de Payment/Reservation):

- **Reserva sem pagamento**  
  - Permitida em cenários específicos (baixa temporada, clientes recorrentes, acordos B2B).  
  - Reserva pode ser `CONFIRMED` sem `Payment.APPROVED`, mas isso deve ser decisão explícita do hotel.

- **Reserva com pagamento obrigatório**  
  - Para tarifas flexíveis: exigir **pagamento parcial** (ex.: 1 diária) para confirmar.  
  - Para tarifas não reembolsáveis: exigir **pagamento total** para confirmar.

- **Ligação entre status de Payment e Reservation** (exemplo simples):  
  - `Payment.APPROVED` → permitir `reservation.confirm()` (ou até confirmar automaticamente).  
  - `Payment.EXPIRED` e reserva ainda `PENDING` → opcionalmente cancelar reserva depois de um tempo.  
  - `Payment.REFUNDED` → não altera o status da reserva automaticamente; decisão de negócio do hotel (pode cancelar ou manter como cortesia).

Do ponto de vista técnico, essas regras moram em entidades de domínio (`Reservation`, `Payment`) ou em um use case de \"Confirmar reserva com pagamento\", nunca em controller.

---

#### 10.4 Orquestração do fluxo com pagamento (sem código ainda)

Fluxo completo sugerido (coerente com os passos anteriores):

1. **Intenção de reservar** → `HandleWhatsAppMessageUseCase` desvia para fluxo de criação.  
2. **Coleta de dados** (datas, quarto, nome) → `CreateReservationUseCase` cria `Reservation` `PENDING`.  
3. **Resumo da reserva** → bot exibe valor total e políticas.  
4. **Escolha de pagamento** (menu simples):  
   - `1. Confirmar e pagar agora`  
   - `2. Confirmar sem pagamento imediato` (se permitido)  
5. Se **pagar agora**:  
   - Fase 0: bot envia instruções de pagamento + mensagem \"sua reserva será confirmada após confirmação do pagamento\".  
   - Fase 1: bot gera link de pagamento via provedor e envia ao hóspede.  
   - Fase 2: além do link, o backend cria um `Payment` e aguarda webhook para mudar estado.  
6. Se **sem pagamento imediato**:  
   - `ConfirmReservationUseCase` confirma a reserva direto, seguindo regra de negócio definida para esse tipo de tarifa.  
7. **Check-in, extensão, alteração de datas, check-out** seguem as regras já descritas nos outros passos — mas agora com a informação de pagamento disponível para decisões futuras (ex.: bloquear extensão se pagamento pendente, etc.).

---

#### 10.5 Como isso entra no roadmap técnico

- **Curto prazo (MVP)**  
  - Adotar Fase 0: fluxo de reserva funcionando ponta a ponta, com mensagem clara sobre pagamento manual.  
  - Nenhuma dependência forte de gateway; decisão pode ser tomada depois.

- **Médio prazo**  
  - Implementar Fase 1: gerar link de pagamento com provedor simples.  
  - A confirmação pode continuar manual no início.

- **Longo prazo**  
  - Implementar Fase 2: webhooks de pagamento, entidade `Payment` integrada e regras automáticas entre `PaymentStatus` e `ReservationStatus`.

Tudo isso pode ser feito **sem mexer agora no código**, apenas guiando as próximas iterações com este documento.

---

#### 10.6 Configuração do hotel (exige ou não pagamento)

O hotel deve poder **configurar** se exige pagamento no ato da reserva. Isso permite que o bot se comporte de forma diferente conforme a política do estabelecimento.

**Campos sugeridos** (a serem adicionados ao `HotelModel` ou a uma entidade de configuração):

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `requires_payment_for_confirmation` | boolean | Se `true`, a reserva **só** pode ser confirmada após pagamento aprovado. O bot não oferece "Confirmar sem pagamento". |
| `allows_reservation_without_payment` | boolean | Se `true`, o bot oferece as duas opções: "Pagar agora" e "Confirmar sem pagamento imediato". |

**Onde definir:** Painel administrativo (futuro), API de configuração ou seed/migração inicial. O `HotelContextService` (que já injeta contexto no prompt da IA) deve expor essa regra para o fluxo determinístico de reserva.

**Evolução:** A configuração pode ser global (por hotel) ou granular (por tipo de quarto/tarifa — ex.: suíte sempre exige pagamento; quarto simples pode permitir reserva sem pagamento).

---

#### 10.7 Fluxo do bot baseado na configuração

O comportamento do bot na etapa de pagamento depende da configuração do hotel:

- **Se `requires_payment_for_confirmation = true`**  
  - O bot **não** oferece "Confirmar sem pagamento imediato".  
  - Mostra apenas: "Para confirmar sua reserva, efetue o pagamento:" + link PIX ou instruções.  
  - A reserva permanece `PENDING` até o pagamento ser aprovado (webhook) ou confirmado manualmente.

- **Se `allows_reservation_without_payment = true`**  
  - O bot oferece menu:  
    - `1. Confirmar e pagar agora`  
    - `2. Confirmar sem pagamento imediato`  
  - Se o hóspede escolher 2, o `ConfirmReservationUseCase` confirma a reserva direto (PENDING → CONFIRMED), seguindo a regra de negócio definida para esse cenário.

---

#### 10.8 Visão do trampolim (automação total até a chegada)

**Objetivo final:** Tudo automatizado, sem intervenção humana, até o hóspede chegar no hotel e apenas pegar as chaves no balcão.

| Etapa | Hoje | Trampolim (fim do caminho) |
|-------|------|----------------------------|
| Reserva | Manual / seed | Bot coleta datas, quarto, nome → cria reserva |
| Pagamento | Não integrado | Webhook confirma pagamento → reserva vira CONFIRMED automaticamente |
| Confirmação | Manual ou via "SIM" | Automática quando pagamento aprova (Fase 2) |
| Check-in | Bot detecta "check-in" | Bot detecta "acabei de chegar" ou self-check-in → CHECKED_IN |
| Chegada física | — | Hóspede vai ao balcão → recepcionista vê reserva confirmada + check-in feito → entrega chaves |

**Fases como caminho até zero intervenção:**

- **Fase 0** — Ainda há intervenção humana (alguém confirma pagamento manualmente).
- **Fase 1** — Menos intervenção (link de pagamento), mas confirmação ainda manual.
- **Fase 2** — **Zero intervenção no fluxo financeiro:** webhook aprova pagamento → reserva confirmada automaticamente.

O trampolim é chegar na **Fase 2** e ter:

1. Reserva automática (CreateReservationUseCase).
2. Pagamento automático (webhook).
3. Confirmação automática (Payment.APPROVED → reservation.confirm()).
4. Check-in automático via WhatsApp (hóspede avisa que chegou → bot executa check-in).
5. Na chegada física: recepcionista só entrega chaves (tudo já está resolvido no sistema).

O único ponto que pode continuar "humano" é a entrega física das chaves; depois isso pode evoluir para self-check-in (código/cartão/digital lock).

---

## 4. Ordem recomendada de implementação

| Ordem | Passo | Esforço | Impacto |
|-------|-------|---------|---------|
| 1 | Corrigir bug do cache de check-in | Baixo | Alto |
| 2 | Mover troca de quarto para o domínio | Baixo | Médio |
| 3 | Encapsular ConfirmReservationUseCase | Baixo | Baixo |
| 4 | CheckoutViaWhatsAppUseCase | Baixo | Alto |
| 5 | CancelReservationUseCase + fluxo | Médio | Médio |
| 6 | CreateReservationUseCase + fluxo | Alto | Muito alto |
| 7 | Alteração de datas no fluxo EDITAR | Médio | Médio |
| 8 | ExtendReservationUseCase | Médio | Médio |
| 9 | Job de No-show | Baixo | Baixo |
| 10 | Planejar e integrar pagamentos na jornada | Médio | Muito alto |

**Sugestão:** Fazer na ordem 1 → 2 → 3 → 4 primeiro (correções e check-out). Depois 6 (criação de reserva) e 5 (cancelamento). Por último, 7, 8 e 9.

---

## 5. Documentos relacionados

- `.cursor/rules/domain-reservation-rules.mdc` — Regras de negócio do domínio
- `docs/GUIA_100_PERCENT_CASOS_REAIS.md` — Casos de uso completos
- `docs/ARQUITETURA_COMPLETA.md` — Visão geral da arquitetura
- `docs/WHATSAPP_ORQUESTRACAO_GUIA.md` — Padrões de orquestração

---

## 6. Sugestões de evolução para automação total

Esta seção lista evoluções adicionais para aproximar o modelo de uma operação 100% automatizada, sem intervenção humana até o hóspede chegar e pegar as chaves.

---

### 6.1 Check-in antecipado (pré-arrival)

Antes da chegada física, o bot pode:

- Coletar **documentos** (CPF, RG) para emissão de nota fiscal e registro hoteleiro.
- Confirmar **horário estimado de chegada**.
- Enviar **instruções de acesso** (endereço, estacionamento, mapa).
- Fazer um **mini-check-in** (aceitar termos, confirmar dados) para reduzir o que falta no balcão.

Na chegada física, o recepcionista só valida identidade e entrega chaves.

---

### 6.2 Comunicação proativa

O bot envia mensagens automáticas em momentos-chave:

- **24h antes** da reserva: "Sua reserva é amanhã. Check-in a partir das 14h."
- **No dia do check-in**: "Hoje é o dia! Quando chegar, responda 'cheguei' para finalizar."
- **1 dia antes do checkout**: "Checkout amanhã às 12h. Quer estender a estadia?"
- **Pós-checkout**: "Obrigado pela estadia. Como foi sua experiência?" (feedback/NPS)

---

### 6.3 Fallback humano explícito

Mesmo em 100% automatizado, o hóspede precisa saber que pode falar com alguém:

- Mensagem padrão: "Se precisar de atendimento humano, digite ATENDENTE ou ligue para [número]."
- Quando o bot não entende ou não consegue resolver: oferece automaticamente transferência para humano.
- Fila de atendimento ou integração com sistema de tickets (ex.: Zendesk, Intercom).

---

### 6.4 Self-check-in e chave digital

Para eliminar o balcão:

- **QR code** ou **link** enviado no WhatsApp após o check-in.
- Integração com **fechaduras inteligentes** (ex.: Nuki, Yale, sistemas de hotel).
- Ou **código numérico** temporário enviado por mensagem.

O hóspede chega, usa o código/QR na fechadura e entra no quarto sem passar pelo balcão.

---

### 6.5 Pedidos durante a estadia

Durante a hospedagem:

- Cardápio de **room service** via WhatsApp.
- Pedidos de **toalhas extras**, **troca de roupa de cama**, etc.
- Cobrança automática na conta do quarto (conta de consumo).

---

### 6.6 Resolução de problemas automatizada

- Hóspede: "O ar condicionado não está funcionando".
- Bot cria **ticket** e notifica o hotel.
- Bot envia: "Registramos seu problema. Nossa equipe foi acionada e deve resolver em até X minutos."
- Possibilidade de **troca de quarto** automática se o problema for grave.

---

### 6.7 Recuperação de pagamento

- Se o pagamento falhar ou expirar: bot envia novo link com prazo de X horas.
- Oferece **alternativa** (ex.: cartão vs PIX).
- Se ainda assim não pagar: aviso de cancelamento automático após Y horas.

---

### 6.8 Segurança e compliance

- **LGPD**: consentimento explícito para armazenar dados e enviar mensagens.
- **PCI-DSS**: não armazenar dados de cartão; usar tokenização do gateway.
- **Auditoria**: logs de quem fez o quê em cada etapa.

---

### 6.9 Integração com OTAs

- Sincronização de calendário com **Booking.com**, **Airbnb**, etc.
- Reservas vindas de OTA podem seguir o mesmo fluxo de WhatsApp (confirmação, check-in, checkout).

---

### 6.10 Priorização sugerida

| Prioridade | Item | Impacto |
|------------|------|---------|
| Alta | Comunicação proativa | Reduz no-show e dúvidas |
| Alta | Fallback humano | Confiança e suporte em casos difíceis |
| Alta | Check-in antecipado | Menos fricção na chegada |
| Média | Recuperação de pagamento | Menos reservas perdidas |
| Média | Resolução de problemas | Melhora experiência |
| Média | Segurança e compliance | Necessário para produção |
| Longo prazo | Chave digital | Automação total |
| Longo prazo | Pedidos durante estadia | Receita adicional |
| Longo prazo | Integração com OTAs | Reservas de múltiplos canais |
