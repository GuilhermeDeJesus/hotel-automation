# Análise de Custos OpenAI (Atualizável)

Este documento descreve como calcular custo sem depender de preços fixos (que mudam com frequência).

## Conceitos

- O custo total depende de tokens de entrada e de saída.
- Cada modelo tem precificação própria.
- Preços podem mudar; confirme no painel oficial antes de qualquer decisão.

## Fórmula

Se:

- `Tin` = tokens de entrada
- `Tout` = tokens de saída
- `Pin` = preço por 1M tokens de entrada
- `Pout` = preço por 1M tokens de saída

Então:

`Custo = (Tin / 1_000_000) * Pin + (Tout / 1_000_000) * Pout`

## Aplicação no projeto

1. Meça média de tokens por conversa real.
2. Multiplique pela volumetria mensal.
3. Compare custo x qualidade x latência entre modelos.

## Práticas recomendadas

- Definir teto mensal de gasto.
- Criar alerta de consumo.
- Manter um modelo alternativo para contingência.
