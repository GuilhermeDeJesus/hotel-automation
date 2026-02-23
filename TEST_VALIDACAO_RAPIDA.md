# 🧪 Validação Rápida: Testar META API sem Python

Se quer testar ANTES de rodar código Python, use esse method.

## Opção 1: Postman (GUI Fácil)

```
1. Abre Postman
2. Clica "+" (new request)
3. Muda para POST
4. URL: https://graph.facebook.com/v18.0/PHONE_NUMBER_ID/messages
   (substitui PHONE_NUMBER_ID pelo seu)

5. Na aba "Headers":
   Authorization: Bearer EAABs...seu_token...
   Content-Type: application/json

6. Na aba "Body" → raw → JSON:

{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "5561998776092",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Teste simples do Postman"
  }
}

7. Clica "Send"
8. Esperado: Status 200 + {"messages": [{"id": "wamid.xxx"}]}
```

## Opção 2: cURL (Terminal)

```bash
# Copie e cole no PowerShell/Terminal:

curl -X POST https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID/messages `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": "5561998776092",
    "type": "text",
    "text": {
      "preview_url": false,
      "body": "Teste do cURL"
    }
  }'

# Substitua:
# - YOUR_PHONE_NUMBER_ID → seu valor (ex: 101652038203517)
# - YOUR_ACCESS_TOKEN → seu token (ex: EAABs...)
# - to: 5561998776092 → seu número
```

## Opção 3: Python One-Liner

```bash
python -c "
import requests
requests.post(
    'https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID/messages',
    json={
        'messaging_product': 'whatsapp',
        'to': '5561998776092',
        'type': 'text',
        'text': {'body': 'Teste Python'}
    },
    headers={'Authorization': 'Bearer YOUR_ACCESS_TOKEN'}
).json()
" | python -m json.tool
```

## Esperado em Todos os Casos

```json
{
  "messages": [
    {
      "id": "wamid.ABCDEFxyz123=="
    }
  ]
}
```

## Se Não Funcionar

| Status | Significado | Solução |
|--------|------------|---------|
| 200 ✅ | OK | Teste funcionou! |
| 400 | Invalid recipient | Número errado ou sem código país |
| 401 | Unauthorized | Token inválido |
| 403 | Forbidden | Sem permissão |
| 429 | Rate limited | Aguarda 60 seg |

---

## Próximo: Rodas os Testes Python

Se o simples (cURL/Postman) funcionou, rode:

```bash
python test_whatsapp_meta.py
```

🎉 **Mensagens devem chegar no seu WhatsApp!**
