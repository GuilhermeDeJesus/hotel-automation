# Como Ver Histórico OpenAI

Há duas fontes principais de acompanhamento.

## 1) Painel da OpenAI

Use o dashboard da OpenAI para acompanhar consumo e faturamento da conta/projeto.

Observação: menus e URLs podem mudar ao longo do tempo.

## 2) Log local do projeto

O sistema registra conversas em:

`logs/conversation_history.json`

## Boas práticas

- Não versionar logs com dados sensíveis.
- Definir rotação/limpeza de histórico.
- Em produção, considerar exportação para observabilidade centralizada.
