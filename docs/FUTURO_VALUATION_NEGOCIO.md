# FUTURO: Valuation e Estratégia de Negócio

Este documento descreve uma visão mais completa para evolução comercial do projeto, com foco em validação real de mercado, unit economics e preparação para valuation.

## 1) Tese de valor

O produto resolve um problema recorrente da hotelaria: perda de atendimento e baixa eficiência operacional em canais de alta demanda (principalmente WhatsApp).

### Valor entregue para o hotel

- Atendimento 24/7 sem depender de equipe disponível em tempo integral.
- Menor tempo de resposta ao hóspede.
- Padronização de respostas com contexto real de hotel e reserva.
- Redução de tarefas repetitivas da recepção.
- Melhora da experiência do hóspede e potencial de conversão.

### Valor entregue para o hóspede

- Resposta rápida no canal que já utiliza.
- Informações consistentes sobre políticas, horários e reserva.
- Menos fricção para resolver dúvidas comuns.

## 2) Perfil de cliente ideal (ICP)

### ICP primário

- Hotéis independentes e pousadas com operação enxuta.
- Forte dependência de WhatsApp para atendimento.
- Ausência de automação ou uso de automações limitadas.

### ICP secundário

- Redes pequenas (2 a 10 unidades) com necessidade de padronização.
- Operações com picos de mensagens em check-in/check-out.

### Critérios de priorização comercial

1. Dor explícita com volume de atendimento.
2. Responsável com poder de decisão acessível.
3. Disponibilidade para piloto curto.
4. Facilidade de integração operacional.

## 3) Modelo de receita

### Estrutura sugerida

Combinação de assinatura mensal + componente por uso:

1. **Plano Base** (plataforma): acesso ao bot e fluxos principais.
2. **Uso Variável**: cobrança por volume de conversas/mensagens.
3. **Serviços** (opcional): onboarding premium, customizações e treinamento.

### Exemplo de pacotes (sem preços fixos)

- **Start**: volume baixo, recursos essenciais.
- **Growth**: volume médio, mais recursos e suporte prioritário.
- **Scale**: multiunidade, SLA e governança operacional.

### Princípios de precificação

- Preço deve capturar parte da economia gerada para o hotel.
- Margem bruta saudável mesmo com crescimento de uso.
- Estrutura simples o suficiente para venda rápida.

## 4) Unit economics (base para valuation)

Métricas mínimas para acompanhar por cliente:

- `MRR_cliente` = receita mensal recorrente do cliente.
- `Custo_IA` = custo mensal com chamadas de IA.
- `Custo_WhatsApp` = custo mensal de mensageria.
- `Custo_Infra` = custo mensal de banco/cache/hospedagem.
- `Margem_Bruta` = `(MRR_cliente - Custos_Diretos) / MRR_cliente`.

Onde:

- `Custos_Diretos = Custo_IA + Custo_WhatsApp + Custo_Infra`.

### Indicadores críticos

- Margem bruta por cliente.
- Payback de aquisição (`CAC payback`).
- Taxa de retenção mensal (`logo churn` e `revenue churn`).
- LTV/CAC.

## 5) Métricas de produto e operação

### Adoção

- Hotéis ativos no mês.
- Usuários operacionais ativos por hotel.
- Percentual de funcionalidades usadas por cliente.

### Performance de atendimento

- Tempo médio de primeira resposta.
- Taxa de resolução sem intervenção humana.
- Taxa de fallback para atendimento manual.

### Qualidade

- Taxa de respostas incorretas reportadas.
- Taxa de reabertura do mesmo assunto.
- Satisfação do operador/hóspede (NPS/CSAT simplificado).

## 6) Estratégia de validação por fases

### Fase 1 — Prova de valor (0–3 meses)

Objetivo: confirmar dor real e capacidade de entrega.

- Selecionar 3 a 5 pilotos com perfis diferentes.
- Definir baseline operacional antes de ativar o bot.
- Medir ganho em tempo de resposta e redução de carga manual.
- Coletar depoimentos e estudos de caso.

### Fase 2 — Repetibilidade comercial (3–6 meses)

Objetivo: provar que o processo de venda e implantação escala.

- Padronizar onboarding.
- Criar playbook de implantação por tipo de hotel.
- Formalizar proposta comercial e política de renovação.
- Instrumentar funil de vendas (lead → piloto → contrato).

### Fase 3 — Escala controlada (6–12 meses)

Objetivo: crescer com eficiência e previsibilidade.

- Automatizar rotinas de sucesso do cliente.
- Fortalecer observabilidade e gestão de incidentes.
- Expandir canais de aquisição com CAC controlado.
- Estruturar time (vendas, implantação, suporte técnico).

## 7) Cenários de crescimento (framework)

Use três cenários em vez de uma projeção única:

1. **Conservador**: maior ciclo de venda e expansão lenta.
2. **Base**: conversão e retenção conforme meta.
3. **Agressivo**: aceleração de aquisição + expansão por indicação.

Para cada cenário, projete:

- Número de clientes ativos.
- MRR total.
- Margem bruta.
- Necessidade de caixa para operação.

## 8) Como pensar valuation (sem número mágico)

Valuation em SaaS B2B costuma depender de qualidade de receita e previsibilidade, não apenas crescimento bruto.

### Fatores que aumentam valuation

- Retenção alta e churn baixo.
- Crescimento consistente de MRR.
- Margem bruta saudável.
- Produto com implementação simples e repetível.
- Baixa dependência de serviço manual para operar.

### Fatores que reduzem valuation

- Churn alto no início.
- Dependência excessiva de customização por cliente.
- Custo variável descontrolado (IA/mensageria).
- Falta de indicadores confiáveis.

## 9) Riscos e mitigação

### Risco: custo variável subir rápido

- Mitigação: governança de prompts, limites por plano e monitoramento de custo por cliente.

### Risco: baixa retenção após piloto

- Mitigação: onboarding forte + metas de sucesso em 30/60/90 dias.

### Risco: dependência de poucos canais de aquisição

- Mitigação: combinar outbound, parcerias e indicação.

### Risco: dependência operacional do fundador

- Mitigação: documentar processos e transformar operação em playbooks.

## 10) Roadmap executivo (12 meses)

### Trimestre 1

- Validar 3 a 5 pilotos com métricas claras.
- Fechar primeiros contratos pagos.
- Consolidar baseline de unit economics.

### Trimestre 2

- Padronizar onboarding e suporte.
- Melhorar produto baseado em dados dos pilotos.
- Estruturar funil comercial com metas mensais.

### Trimestre 3

- Escalar aquisição com controle de CAC.
- Reduzir tempo de implantação por cliente.
- Aumentar retenção e expansão em contas existentes.

### Trimestre 4

- Consolidar previsibilidade de receita.
- Preparar data room com métricas históricas.
- Definir estratégia de captação/parcerias (se desejado).

## 11) Checklist prático para os próximos 30 dias

1. Definir ICP oficial e critérios de qualificação.
2. Criar dashboard mínimo de métricas (MRR, churn, margem, tempo de resposta).
3. Rodar pilotos com contrato e objetivo mensurável.
4. Publicar versão 1 do playbook de onboarding.
5. Definir proposta comercial padrão (planos + escopo).

## 12) Conclusão

O caminho de maior valor para valuation é: **provar impacto real**, **padronizar entrega** e **crescer com retenção**.  
Sem isso, projeções financeiras ficam frágeis; com isso, o negócio ganha previsibilidade e múltiplos melhores ao longo do tempo.

## 13) Faixa de valuation hoje (sem tração relevante)

Com base no estágio atual descrito neste repositório (produto funcional, boa base técnica, mas sem histórico robusto de receita recorrente), uma faixa **indicativa** de mercado costuma ficar em:

- **Conservador:** R$ 120 mil a R$ 250 mil
- **Base:** R$ 250 mil a R$ 600 mil
- **Oportunidade estratégica (comprador específico):** até ~R$ 1,0 milhão

> Observação: esta faixa é uma referência prática para negociação inicial e não substitui avaliação financeira formal.

## 14) Modelo de cálculo de valuation com tração (ARR)

Quando houver receita recorrente validada, use abordagem por múltiplo de ARR:

- `ARR = MRR * 12`
- `Valuation = ARR * Multiplo`

### Múltiplos de referência (SaaS B2B inicial)

- **Conservador:** 2x a 3x ARR
- **Base:** 3x a 5x ARR
- **Agressivo:** 5x a 7x ARR

Os múltiplos dependem de churn, margem, crescimento, previsibilidade e risco operacional.

## 15) Tabela de cenários (exemplo prático)

Valores abaixo são **simulação** para tomada de decisão e planejamento:

| Cenário | Clientes Ativos | Ticket Médio Mensal | MRR | ARR | Múltiplo | Faixa de Valuation |
|---|---:|---:|---:|---:|---:|---:|
| Conservador | 10 | R$ 700 | R$ 7.000 | R$ 84.000 | 2x–3x | R$ 168.000 – R$ 252.000 |
| Base | 25 | R$ 900 | R$ 22.500 | R$ 270.000 | 3x–5x | R$ 810.000 – R$ 1.350.000 |
| Agressivo | 50 | R$ 1.200 | R$ 60.000 | R$ 720.000 | 5x–7x | R$ 3.600.000 – R$ 5.040.000 |

## 16) Como ajustar para sua realidade (passo a passo)

1. Defina `Clientes Ativos` e `Ticket Médio Mensal` realistas para 12 meses.
2. Calcule `MRR` e `ARR`.
3. Escolha múltiplo conforme qualidade de receita:
	- churn alto / crescimento instável → múltiplo menor
	- retenção forte / crescimento consistente → múltiplo maior
4. Gere faixa de valuation (`ARR * mínimo` e `ARR * máximo`).

## 17) Regras de negociação (práticas)

### Piso de negociação

Use o cenário conservador para definir preço mínimo defensável.

### Preço-alvo

Use o cenário base como referência principal em proposta comercial/investidor.

### Teto aspiracional

Use cenário agressivo apenas quando já houver evidência forte de crescimento e retenção.

## 18) Marcos que aumentam valuation rapidamente

Priorize estes marcos para subir de faixa:

1. 10+ clientes pagantes com 3+ meses de retenção.
2. Churn mensal controlado e previsível.
3. Margem bruta consistente.
4. Playbook de onboarding replicável.
5. Funil comercial com conversão monitorada.

## 19) Mini-template para preencher mensalmente

Copie e atualize este bloco no fechamento de cada mês:

```text
Mês:
Clientes ativos:
Ticket médio (R$/mês):
MRR (R$):
ARR (R$):
Churn mensal (%):
Margem bruta (%):

Múltiplo usado (mín-máx):
Valuation estimado mínimo (R$):
Valuation estimado máximo (R$):

Justificativa do múltiplo:
```
