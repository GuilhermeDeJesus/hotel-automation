# 💡 Example: End-to-End Context Flow

Este arquivo demonstra como os contextos (Passo 3 + Passo 4) fluem através do sistema.

---

## 🎬 Cenário

**Hóspede**: João Silva  
**Reserva**: 20-25 de Dezembro 2024, Quarto 302  
**Pergunta**: "Qual é o horário de check-in? Qual é a política de cancelamento?"

---

## 📱 Passo 1: WhatsApp Message Received

```
Hóspede (WhatsApp):
"Qual é o horário de check-in? Qual é a política de cancelamento?"

from: +5561987654321 (João Silva)
```

---

## 🔌 Passo 2: Webhook Receives Message

```python
# app/interfaces/api/whatsapp_webhook.py
@router.post("/webhook/whatsapp")
async def handle_whatsapp(
    request: WhatsAppMessage,
    conversation_use_case = Depends(get_conversation_use_case)
):
    phone = request.messages[0].from  # +5561987654321
    message = request.messages[0].text.body
    
    response = await conversation_use_case.execute(
        phone=phone,
        message=message
    )
    
    return send_whatsapp_reply(phone, response)
```

---

## 🔄 Passo 3: ConversationUseCase Executes

```python
# app/application/use_cases/conversation.py
class ConversationUseCase:
    async def execute(self, phone: str, message: str) -> str:
        
        # ✅ PASSO 4: Get Hotel Context
        hotel_context = self.hotel_context_service.get_context()
        # Returns:
        # """CONTEXTO DO HOTEL:
        # - Nome: Hotel Automation
        # - Endereco: Avenida Central, 123, Brasilia - DF
        # - Check-in: 14:00
        # - Check-out: 12:00
        # - Politicas: Cancelamento: Cancelamento gratis ate 24h antes do check-in | 
        #   Pets: Nao aceitamos pets | Criancas: Criancas ate 6 anos nao pagam
        # - Servicos: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento
        # - Contato: +55 61 99999-0000"""
        
        # ✅ PASSO 3: Get Reservation Context
        reservation_context = self.context_service.get_context_for_phone(phone)
        # Returns:
        # """CONTEXTO DE RESERVA:
        # - Hospede: João Silva
        # - Status: Confirmada
        # - Check-in: 20 de Dezembro de 2024
        # - Check-out: 25 de Dezembro de 2024
        # - Quarto: 302
        # - Notas: Cliente VIP, avisar sobre upgrade disponível"""
        
        # 🎯 COMBINE BOTH CONTEXTS FOR SYSTEM PROMPT
        system_message = "You are a helpful and friendly hotel assistant."
        
        if hotel_context:
            system_message += f"\n\n{hotel_context}"
        
        if reservation_context:
            system_message += f"\n\n{reservation_context}"
        
        # Final system_message:
        system_message = """You are a helpful and friendly hotel assistant.

CONTEXTO DO HOTEL:
- Nome: Hotel Automation
- Endereco: Avenida Central, 123, Brasilia - DF
- Check-in: 14:00
- Check-out: 12:00
- Politicas: Cancelamento: Cancelamento gratis ate 24h antes do check-in | Pets: Nao aceitamos pets | Criancas: Criancas ate 6 anos nao pagam
- Servicos: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento
- Contato: +55 61 99999-0000

CONTEXTO DE RESERVA:
- Hospede: João Silva
- Status: Confirmada
- Check-in: 20 de Dezembro de 2024
- Check-out: 25 de Dezembro de 2024
- Quarto: 302
- Notas: Cliente VIP, avisar sobre upgrade disponível"""
        
        # 📚 Build conversation history
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": "Qual é o horário de check-in? Qual é a política de cancelamento?"}
        ]
        
        # 🤖 Send to AI with FULL CONTEXT
        response = self.ai_service.get_response(messages)
        
        # Save to cache and return
        self.cache_repository.save(phone, message, response)
        
        return response
```

---

## 🧠 Passo 4: AI Processes with Full Context

```
INPUT to OpenAI:
{
    "temperature": 0.7,
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful and friendly hotel assistant.

CONTEXTO DO HOTEL:
- Nome: Hotel Automation
- Endereco: Avenida Central, 123, Brasilia - DF
- Check-in: 14:00
- Check-out: 12:00
- Politicas: Cancelamento: Cancelamento gratis ate 24h antes do check-in | Pets: Nao aceitamos pets | Criancas: Criancas ate 6 anos nao pagam
- Servicos: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento
- Contato: +55 61 99999-0000

CONTEXTO DE RESERVA:
- Hospede: João Silva
- Status: Confirmada
- Check-in: 20 de Dezembro de 2024
- Check-out: 25 de Dezembro de 2024
- Quarto: 302
- Notas: Cliente VIP, avisar sobre upgrade disponível"
        },
        {
            "role": "user",
            "content": "Qual é o horário de check-in? Qual é a política de cancelamento?"
        }
    ]
}

AI REASONING:
✓ Hotel context provides: check-in is 14:00, cancellation policy is free until 24h before
✓ Reservation context provides: João has reservation Dec 20-25, room 302
✓ AI combines both to give personalized response

AI RESPONSE:
"Olá João! 👋

Bem-vindo ao Hotel Automation! Temos prazer em hospedá-lo.

Respondendo suas perguntas:

**Check-in**: Você pode fazer check-in a partir das 14:00 de hoje (20 de Dezembro). Você está reservado para o Quarto 302. Se chegar mais cedo, nossa recepção pode guardar suas malas.

**Política de Cancelamento**: Ótima notícia! Oferecemos cancelamento **gratuito até 24 horas antes do seu check-in** (19 de Dezembro às 14:00). Após esse horário, a cobrança será integral.

Como cliente VIP em nosso sistema, estou preparando um pequeno upgrade para você ao chegar!

Qualquer dúvida, estou por aqui. 😊"
```

---

## 🎯 Passo 5: Response Sent Back

```python
# Response logged and cached
conversation_cache.save(
    phone="+5561987654321",
    user_message="Qual é o horário de check-in? Qual é a política de cancelamento?",
    ai_response="Olá João! 👋...",
    timestamp=datetime.utcnow()
)

# Sent back to WhatsApp
send_whatsapp_reply(
    to="+5561987654321",
    message="Olá João! 👋\n\nBem-vindo ao Hotel Automation!...",
    message_id="wamid.123456"
)
```

---

## 📊 Database State During Execution

### customers table
```sql
SELECT * FROM customers WHERE phone_number = '+5561987654321';

id  | name        | phone_number    | created_at
----|-------------|-----------------|----------
c1  | João Silva  | +5561987654321  | 2024-12-20 10:00:00
```

### reservations table
```sql
SELECT * FROM reservations WHERE guest_id = 'c1';

id  | guest_id | check_in_date | check_out_date | room_number | status
----|----------|---------------|----------------|------------|----------
r1  | c1       | 2024-12-20    | 2024-12-25    | 302        | confirmed
```

### hotels table
```sql
SELECT * FROM hotels WHERE is_active = true;

id   | name              | address                        | checkin_time | checkout_time | cancellation_policy              | pet_policy         | child_policy              | amenities
-----|------------------|--------------------------------|--------------|---------------|----------------------------------|--------------------|---------------------------|---------------------------------------------
h1   | Hotel Automation | Avenida Central, 123, Brasilia | 14:00        | 12:00         | Cancelamento gratis ate 24h...  | Nao aceitamos pets | Criancas ate 6 anos...   | Wi-Fi, Piscina, Academia, Restaurante...
```

### conversation_cache table
```sql
SELECT * FROM conversation_cache WHERE phone_number = '+5561987654321' ORDER BY created_at DESC LIMIT 1;

id  | phone_number    | user_message                                  | ai_response                | created_at
----|-----------------|-----------------------------------------------|----------------------------|----------
cc1 | +5561987654321  | Qual é o horário de check-in? Qual é...      | Olá João! 👋 Bem-vindo... | 2024-12-20 13:45:30
```

---

## 🔍 Code Trace: Where Contexts Come From

### HotelContextService.get_context()

```python
class HotelContextService:
    def get_context(self) -> str:
        # 1. Query database
        hotel = self.hotel_repository.get_active_hotel()  # SQL query
        
        # 2. Check result
        if not hotel:
            return ""  # No hotel = no context (prevent hallucinations)
        
        # 3. Format
        context = f"""CONTEXTO DO HOTEL:
- Nome: {hotel.name}
- Endereco: {hotel.address}
- Check-in: {hotel.policies.checkin_time}
- Check-out: {hotel.policies.checkout_time}
- Politicas: Cancelamento: {hotel.policies.cancellation_policy} | \
Pets: {hotel.policies.pet_policy} | Criancas: {hotel.policies.child_policy}
- Servicos: {hotel.policies.amenities}
- Contato: {hotel.contact_phone}"""
        
        return context

# SQL Query executed:
SELECT id, name, address, contact_phone, checkin_time, checkout_time,
       cancellation_policy, pet_policy, child_policy, amenities, is_active
FROM hotels
WHERE is_active = TRUE
LIMIT 1;

# Result:
# Hotel Automation | Avenida Central, 123... | 14:00 | 12:00 | ... (formatted above)
```

### ReservationContextService.get_context_for_phone()

```python
class ReservationContextService:
    def get_context_for_phone(self, phone: str) -> str:
        # 1. Query database
        reservation = self.reservation_repository.get_by_phone(phone)
        customer = self.customer_repository.get_by_phone(phone)
        
        # 2. Check result
        if not reservation or not customer:
            return ""  # No reservation = no context
        
        # 3. Format
        context = f"""CONTEXTO DE RESERVA:
- Hospede: {customer.name}
- Status: {reservation.status}
- Check-in: {reservation.check_in_date.strftime('%d de %B de %Y')}
- Check-out: {reservation.check_out_date.strftime('%d de %B de %Y')}
- Quarto: {reservation.room_number}
- Notas: {reservation.notes or 'Nenhuma'}"""
        
        return context

# SQL Query executed:
SELECT * FROM reservations 
WHERE phone_number = '+5561987654321'
AND status IN ('confirmed', 'checked_in')
ORDER BY created_at DESC
LIMIT 1;

# Result:
# João Silva | Confirmada | 20 de Dezembro de 2024 | 25 de Dezembro de 2024 | 302 | ...
```

---

## ⚡ Performance Impact

### Queries per WhatsApp Message
```
1. HotelContextService.get_context()
   → SELECT * FROM hotels WHERE is_active=TRUE LIMIT 1
   → Time: ~10ms (indexed on is_active)
   → Cached? No (queries DB each time - could optimize with Redis)

2. ReservationContextService.get_context_for_phone(phone)
   → SELECT * FROM reservations WHERE phone_number=? LIMIT 1
   → Time: ~20ms (indexed on phone_number)
   → Cached? No (queries DB each time)

3. AIService.get_response(messages)
   → OpenAI API call
   → Time: ~800-1500ms (depends on model and response length)
   → Cached? No (each request is unique)

Total API response time: ~850-1500ms
```

### Optimization Opportunity
```python
# Cache hotel context (changes rarely)
@functools.lru_cache(maxsize=1)
@functools.cache(ttl=86400)  # 24 hour TTL
def get_hotel_context() -> str:
    # Only query DB once per 24h
    # Result: Save 10ms per request
```

---

## 🛡️ Error Handling

### What if hotel context fails?
```python
try:
    hotel_context = self.hotel_context_service.get_context()
except DatabaseError:
    logger.error("Hotel context query failed")
    hotel_context = ""  # Fallback: empty string
    # AI still has reservation context, works but less informed

# Result: Graceful degradation
```

### What if AI fails?
```python
try:
    response = self.ai_service.get_response(messages)
except OpenAIError as e:
    logger.error(f"AI service failed: {e}")
    response = "Desculpe, estou com dificuldades no momento. Por favor tente novamente."
    
# Result: User notified, no system crash
```

---

## 📈 Scaling Considerations

### Multi-Hotel Support
```python
# Current: Single hotel in system
hotel = self.hotel_repository.get_active_hotel()

# Future: Multiple hotels per tenant
hotel = self.hotel_repository.get_active_hotel(hotel_id=request.context.hotel_id)

# Would require:
# - Pass hotel_id through webhook context
# - Update HotelRepository.get_active_hotel(hotel_id)
# - Database schema: add tenant_id or hotel_id
```

### High Volume (1000+ messages/sec)
```python
# Current architecture:
# - Database: ~30ms per request
# - AI: ~1000ms per request
# - Bottleneck: OpenAI API

# To scale:
# 1. Use Redis cache for duplicate questions
# 2. Queue AI requests with background workers
# 3. Load balance across multiple API keys
# 4. Implement rate limiting per phone
```

---

## 📚 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ WhatsApp User: João Silva                                   │
│ Message: "Qual é o horário de check-in?"                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ Twilio WebHook = handle_whatsapp(request)                   │
│ Extracts: phone=+5561987654321, message=...                │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ ConversationUseCase.execute(phone, message)                 │
├─────────────────┬───────────────────────────────────────────┤
│                 │                                            │
│    ┌────────────▼──────────┐                                │
│    │ HotelContextService   │                                │
│    │ .get_context()        │                                │
│    │ ↓                     │                                │
│    │ HotelRepositorySQL    │                                │
│    │ .get_active_hotel()   │                                │
│    │ ↓                     │                                │
│    │ SELECT * FROM hotels  │──────→ "CONTEXTO DO HOTEL: ..."│
│    └───────────────────────┘                                │
│                                                              │
│    ┌──────────────────────────┐                             │
│    │ ReservationContextService │                             │
│    │ .get_context_for_phone() │                             │
│    │ ↓                        │                             │
│    │ ReservationRepositorySQL │                             │
│    │ .get_by_phone()          │                             │
│    │ ↓                        │                             │
│    │ SELECT * FROM            │──────→ "CONTEXTO DE RESERVA..."│
│    │ reservations             │                             │
│    └──────────────────────────┘                             │
│                                                              │
│    Combine both contexts into system_message               │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ AIService.get_response(messages)                            │
│ [system_message + user_message]                            │
│                                                              │
│ POST https://api.openai.com/v1/chat/completions           │
│ With FULL CONTEXT:                                         │
│ - Hotel name, policies, services, contact                  │
│ - Guest name, reservation dates, room number              │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ ChatGPT Response (informed by full context)                 │
│ "Olá João! Check-in é às 14:00. Você pode usar..."        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ Cache in ConversationCache                                  │
│ INSERT INTO conversation_cache (phone, message, response)  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ Send via Twilio WhatsApp API                               │
│ Response to: +5561987654321                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ WhatsApp User receives response                             │
│ "Olá João! Check-in é às 14:00..."  ✓                     │
└─────────────────────────────────────────────────────────────┘
```

---

**Pronto! Agora você tem a visão completa do fluxo end-to-end.** 🎯
