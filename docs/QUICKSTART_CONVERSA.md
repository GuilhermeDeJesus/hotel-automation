# Quick Start de Conversa Local

Teste rápido do fluxo de conversa fora do webhook.

## Pré-requisitos

- `pip install -r requirements.txt`
- `.env` com `OPENAI_API_KEY`

## Execução

```bash
python scripts/interactive_conversation.py
```

## Testes úteis

```bash
python tests/test_conversation_mock.py
python tests/test_openai_simple.py
```

## Falhas comuns

- Sem crédito/chave inválida na OpenAI.
- Ambiente Python diferente do esperado.
