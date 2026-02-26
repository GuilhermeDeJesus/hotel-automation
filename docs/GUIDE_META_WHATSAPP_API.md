# 🔧 Guide Completo: Meta WhatsApp Cloud API

**Status:** Setup para receber e enviar mensagens  
**Tempo:** 30 min para setup + testes  
**Resultado:** Seu app recebendo mensagens do WhatsApp + respondendo automaticamente

---

## 📋 Pré-Requisitos

```
✅ Conta Meta/Facebook Developer (você tem)
✅ Aplicativo criado no Meta (você tem)
✅ Número de telefone de teste (você tem?)
✅ WhatsApp Business Account (verificar)
✅ FastAPI rodando (você tem)
✅ ngrok ou tunneling para webhook (precisar)
```

---

## 1️⃣ Setup na Console Meta (CRÍTICO)

### A. Verificar Credenciais

```
Vá para: https://developers.facebook.com/

1. Seu App → Settings → Basic
   ├─ App ID: _____________ (SALVA)
   └─ App Secret: _____________ (SALVA)

2. App → Configuração → WhatsApp
   ├─ WhatsApp Business Account ID: _____________ (SALVA)
   └─ Phone Number ID: _____________ (SALVA)

3. App → WhatsApp → API Setup
   ├─ Clica em "Generate Token"
   └─ Access Token: _____________ (SALVA - validade 60 dias!)
```

### B. Configurar Webhook

```
1. App → Configuração → Webhooks
   ├─ Clica "Adicionar Webhook"
   └─ Object: whatsapp_business_account

2. Configurar Callback URL:
   ├─ URL: https://seu-dominio.com/webhook/whatsapp
   ├─ OU (testing): https://seu-ngrok-url.ngrok.io/webhook/whatsapp
   └─ Clica "Verificar e Salvar"

3. Verificação automática:
   ├─ Meta enviará GET com query params
   ├─ Seu endpoint precisa responder com challenge
   └─ Vamos implementar isso abaixo
```

### C. Inscrever em Webhooks

```
1. App → WhatsApp → Configuration
2. Em "Webhook fields" → Seleciona:
   ├─ ✅ messages
   ├─ ✅ message_template_status_update
   ├─ ✅ message_status
   ├─ ✅ phone_number_name_update
   └─ Clica "Save"
```

---

## 2️⃣ Setup Local (ngrok para Testing)

Enquanto não tem domínio público:

```bash
# 1. Download ngrok: https://ngrok.com/download
# 2. Unzip e adiciona ao PATH
# 3. No terminal:

ngrok http 8000

# Resultado:
# Forwarding https://1234abc.ngrok.io -> http://localhost:8000

# Use: https://1234abc.ngrok.io/webhook/whatsapp
# na config do Meta
```

---

## 3️⃣ Código FastAPI (O Importante!)

### A. Instalar Dependencies

```bash
pip install pydantic requests python-dotenv
```

### B. Variáveis de Ambiente (.env)

```env
# Meta WhatsApp
META_ACCESS_TOKEN=EAABs...seu_token...
PHONE_NUMBER_ID=123456789
META_VERIFY_TOKEN=seu_verify_token_qualquer_string

# Seu domínio (webhook verification)
WEBHOOK_VERIFY_TOKEN=qualquer_coisa_segura_123

# Para logging
LOG_LEVEL=INFO
```

### C. Atualizar requirements.txt

```
requests==2.31.0
pydantic==2.5.0
python-dotenv==1.0.0
```

---

## 4️⃣ Estrutura de Código (Implementar)

Crie arquivo: `app/infrastructure/messaging/whatsapp_meta_client.py`

```python
import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class WhatsAppMetaClient:
    """Cliente para Meta WhatsApp Cloud API"""
    
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("PHONE_NUMBER_ID")
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def send_text_message(self, to_phone: str, message: str) -> dict:
        """Envia mensagem de texto via WhatsApp"""
        
        # Formata número: remove caracteres, adiciona código país se necessário
        to_phone = self._format_phone(to_phone)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False, 
                    "error": response.text,
                    "status_code": response.status_code
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_button_message(self, to_phone: str, message: str, buttons: list) -> dict:
        """Envia mensagem com botões"""
        
        to_phone = self._format_phone(to_phone)
        
        # buttons = [
        #     {"id": "1", "title": "Fazer Reserva"},
        #     {"id": "2", "title": "Estender Estadia"}
        # ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn["id"],
                                "title": btn["title"]
                            }
                        }
                        for btn in buttons[:3]  # Max 3 botões
                    ]
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mark_as_read(self, message_id: str) -> dict:
        """Marca mensagem como lida"""
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            return {"success": response.status_code == 200}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _format_phone(phone: str) -> str:
        """Formata número para padrão WhatsApp (code + number)"""
        # Remove caracteres especiais
        phone = "".join(filter(str.isdigit, phone))
        
        # Se não tem código país (55), adiciona
        if not phone.startswith("55"):
            phone = "55" + phone
        
        return phone
```

---

## 5️⃣ Webhook Handler (CRÍTICO)

Atualize: `app/interfaces/api/whatsapp_webhook.py`

```python
import os
import json
import logging
from fastapi import APIRouter, Request, Response, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.interfaces.dependencies import get_checkin_use_case
from app.infrastructure.messaging.whatsapp_meta_client import WhatsAppMetaClient

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)
whatsapp_client = WhatsAppMetaClient()

# ==================== WEBHOOK VERIFICATION ====================
@router.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """
    Meta envia GET com query params para verificar webhook.
    Você precisa responder com o challenge.
    """
    
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN")
    
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Webhook verification: mode={mode}, token={token}")
    
    if mode == "subscribe" and token == verify_token:
        logger.info("✅ Webhook verified successfully!")
        return Response(content=challenge, status_code=200)
    else:
        logger.error("❌ Webhook verification failed!")
        return Response(content="Unauthorized", status_code=403)


# ==================== WEBHOOK RECEIVER ====================
@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    use_case: CheckInViaWhatsAppUseCase = Depends(get_checkin_use_case)
):
    """
    Recebe mensagens do WhatsApp via Meta Cloud API.
    """
    
    try:
        body = await request.json()
        logger.info(f"Webhook received: {json.dumps(body, indent=2)}")
        
        # Meta envia formato específico
        if body.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}
        
        # Extrai mudanças (changes)
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])
        
        for change in changes:
            value = change.get("value", {})
            
            # Processa mensagens recebidas
            messages = value.get("messages", [])
            for message in messages:
                await _handle_incoming_message(message, use_case)
            
            # Processa status de mensagens (se quer rastrear)
            statuses = value.get("statuses", [])
            for status in statuses:
                _handle_message_status(status)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ==================== HELPERS ====================
async def _handle_incoming_message(message: dict, use_case: CheckInViaWhatsAppUseCase):
    """Processa mensagem recebida"""
    
    message_id = message.get("id")
    from_phone = message.get("from")  # Somethone: '5511987654321'
    timestamp = message.get("timestamp")
    type_ = message.get("type")  # "text", "image", "document", etc
    
    logger.info(f"📱 Mensagem recebida de {from_phone}: type={type_}")
    
    # Marca como lida
    whatsapp_client.mark_as_read(message_id)
    
    # Extrai conteúdo baseado no tipo
    content = ""
    
    if type_ == "text":
        content = message.get("text", {}).get("body", "")
    
    elif type_ == "button":
        # Quando usuário clica num botão
        content = message.get("button", {}).get("text", "")
    
    elif type_ == "interactive":
        # Resposta interativa
        interactive = message.get("interactive", {})
        button_reply = interactive.get("button_reply", {})
        content = button_reply.get("title", "")
    
    else:
        # Para outros tipos (imagem, arquivo, etc)
        content = f"[{type_.upper()}]"
    
    logger.info(f"📝 Conteúdo: {content}")
    
    # AQUI: Você processa com sua IA/use case
    try:
        # Se a mensagem é "checkin", executa use case
        if "checkin" in content.lower():
            response_dto = use_case.execute(
                CheckinRequestDTO(phone=from_phone)
            )
            reply = response_dto.message
        else:
            # Caso contrário, responde genérico (ou chama sua IA)
            reply = f"Recebi sua mensagem: {content}\n\nComo posso ajudar?"
        
        # Envia resposta via WhatsApp
        result = whatsapp_client.send_text_message(from_phone, reply)
        
        if result["success"]:
            logger.info(f"✅ Resposta enviada para {from_phone}")
        else:
            logger.error(f"❌ Erro ao enviar resposta: {result['error']}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {str(e)}")
        # Envia mensagem de erro
        whatsapp_client.send_text_message(
            from_phone,
            "Desculpa, ocorreu um erro. Tente novamente."
        )


def _handle_message_status(status: dict):
    """Processa status de entrega (opcional)"""
    
    message_id = status.get("id")
    status_type = status.get("status")  # "sent", "delivered", "read", "failed"
    
    logger.info(f"📊 Status de mensagem {message_id}: {status_type}")
    
    # Você pode guardar isso no banco se quiser rastrear
    # Exemplo: update message_log set status = 'delivered' where id = message_id
```

---

## 6️⃣ Testar Localmente

### A. Setup Environment

```bash
# 1. Criar .env
cd e:\Desenvolvimento\hotel-automation

cat > .env << EOF
META_ACCESS_TOKEN=EAABs...seu_token...
PHONE_NUMBER_ID=123456789
WEBHOOK_VERIFY_TOKEN=meu_token_super_secreto

LOG_LEVEL=INFO
EOF
```

### B. Rodar ngrok

```bash
# Terminal 1
ngrok http 8000

# Copia a URL - exemplo: https://1234abc.ngrok.io
```

### C. Atualizar Meta Console

```
1. Vá para: https://developers.facebook.com/
2. App → Configuração → Webhooks
3. Edit webhook:
   - Callback URL: https://1234abc.ngrok.io/webhook/whatsapp
   - Verify Token: meu_token_super_secreto
   - Clica "Verificação"
```

### D. Rodar FastAPI

```bash
# Terminal 2
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### E. Testar

```bash
# Terminal 3
# 1. Enviar mensagem para seu número de teste do WhatsApp
#    (seu número configurado no Meta)

# 2. Ver logs no Terminal 2 (FastAPI)
# 3. Mensagem deve chegar!

# DEBUG: Se não funcionar, check logs:
# - Webhook verification OK?
# - Token correto?
# - Número de telefone com código país?
# - Firewall bloqueando?
```

---

## 7️⃣ Troubleshooting

### ❌ "Webhook verification failed"

```
Problema: Token não bate

Solução:
├─ Verifica .env - é o mesmo token?
├─ Copia exatamente (sem espaços)
└─ Reinicia FastAPI
```

### ❌ "Message not received"

```
Problema: Mensagens não chegam

Verificar:
├─ Número de telefone correto?
│  └─ Deve ser: 5511987654321 (código 55 + sem travessão)
├─ Access Token válido?
│  └─ Expira em 60 dias, importante renovar
├─ Phone Number ID correto?
└─ ngrok rodando?
```

### ❌ "Failed to send message"

```json
{
  "error": {
    "message": "Invalid recipient",
    "type": "OAuthException",
    "code": 400
  }
}
```

Soluções:
- Número sem código país → adiciona prefix "55"
- Número inválido → confere no WhatsApp

### ❌ "Access Token expired"

```
Problema: Token venceu (60 dias)

Solução:
├─ Vai em: https://developers.facebook.com/
├─ App → Configuração → WhatsApp
├─ Gera novo token
└─ Atualiza .env
```

---

## 8️⃣ Exemplo Prático (Passo-a-Passo)

### Teste Manual

```bash
# 1. Seu número WhatsApp recebe um código - confirma no App
# 2. Setup webhook no Meta (token + URL)
# 3. FastAPI rodando localmente com ngrok
# 4. Envia mensagem via WhatsApp para seu número

# Esperado:
# ✅ FastAPI recebe em logs
# ✅ Marca como lida (checkmark azul no WhatsApp)
# ✅ Responde automaticamente
```

### Resposta Esperada

```
Você:   "Quero fazer check-in"
Bot:    "Recebi sua mensagem: Quero fazer check-in
         
         Como posso ajudar?"
```

---

## 9️⃣ Production Checklist

Antes de ir para produção:

```
✅ Access Token guardado com segurança (não no GitHub!)
✅ Domínio próprio (não ngrok)
✅ SSL Certificate (HTTPS obrigatório)
✅ Logging centralizado (Sentry/CloudWatch)
✅ Monitoramento de uptime (StatusPage)
✅ Backup do banco (PostgreSQL backup)
✅ Rate limiting (evita DDoS)
✅ Tests de integração
✅ SLA 99.9% de uptime
✅ Suporte 24/7 para customers
```

---

## 🔟 Próximo Passo Depois Disso

Quando WhatsApp funcionar 100%:

1. **Integrar com sua IA** (OpenAI)
   - Em vez de resposta estática, chama GPT
   
2. **Adicionar conversação multi-turn**
   - Guarda contexto (já tem ConversationCache)
   
3. **Fluxo de reserva**
   - Pergunta: nome, datas, quantos quartos, etc
   - Valida com seu banco de dados
   - Cria reserva
   
4. **Pagamento**
   - Link de Stripe
   - Envia via WhatsApp
   - Confirma quando pago

---

## 📞 Referências

- [Meta WhatsApp Cloud API Docs](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Message Types](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
- [Webhook Events](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components)
- [Error Codes](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes)

---

**Próximo:** Quer que eu adapte seu código agora? 🚀
