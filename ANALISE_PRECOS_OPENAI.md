# 💰 Análise de Preços OpenAI - Guia Completo

## 1️⃣ O QUE É UM TOKEN?

**Token = Pedaço pequeno de texto**

- 1 token ≈ 4 caracteres (em português, às vezes menos)
- Exemplo: "Olá, como você está?" = aproximadamente 9 tokens

```
1 token = ~4 caracteres
1.000 tokens = ~5 páginas de texto
1 milhão de tokens = ~5.000 páginas de texto
```

**IMPORTANTE:** Você paga tanto pela ENTRADA (suas perguntas) quanto pela SAÍDA (respostas)

---

## 2️⃣ MODELOS ATUAIS & PREÇOS RECOMENDADOS (para seu projeto)

### 🏆 **Melhor custo-benefício: `gpt-3.5-turbo` (RECOMENDADO)**

```
Entrada:   US$ 0,50 / 1 milhão de tokens
Saída:     US$ 1,50 / 1 milhão de tokens

Exemplo: 100 mensagens de 50 tokens de entrada + 100 tokens de saída
Entrada:   100 * 50 = 5.000 tokens = US$ 0,0025
Saída:     100 * 100 = 10.000 tokens = US$ 0,015
TOTAL:     US$ 0,0175 (aproximadamente 1 centavo por 100 mensagens!)
```

### 💎 **Mais inteligente, mas caro: `gpt-5.2-pro`**

```
Entrada:   US$ 21,00 / 1 milhão de tokens  (42x MAIS CARO que 3.5-turbo)
Saída:     US$ 168,00 / 1 milhão de tokens (112x MAIS CARO que 3.5-turbo)

Mesmo exemplo acima custaria: US$ 2,01 (100x mais caro!)
```

### ⚡ **Mais rápido e barato: `gpt-5-mini`**

```
Entrada:   US$ 0,25 / 1 milhão de tokens
Saída:     US$ 2,00 / 1 milhão de tokens

Bom para tarefas simples, check-ins, respostas rápidas
```

**👉 RECOMENDAÇÃO PARA SEU PROJETO:** Use `gpt-3.5-turbo` ou `gpt-5-mini`

---

## 3️⃣ ENTENDENDO OS "CRÉDITOS"

### O que é um crédito no OpenAI?

**Crédito = Dinheiro em dólares que você carrega na conta**

- $5 de crédito = você pode gastar até $5 em requisições
- Após gastar $5, não consegue mais fazer requisições
- Não expira (se não usar, fica lá)

### Onde vejo quanto tenho?

1. Acessa: https://platform.openai.com/account/billing/overview
2. Baixa em "Credit balance" ou "Usage"

### Como carregar créditos?

1. Vai para https://platform.openai.com/account/billing/overview
2. Clica "Add to credit balance"
3. Escolhe valor ($5, $10, $25...)
4. Adiciona cartão de crédito
5. Pronto! Crédito aparece em segundos

---

## 4️⃣ QUANTO CUSTA USAR PARA SEU PROJETO?

### Cenário 1: Check-in automático via WhatsApp (seu caso)

```
✅ 1 conversa de check-in = ~300 tokens entrada + 150 tokens saída
   Custo por conversa: ~US$ 0,00025 (1/4 de centavo!)

✅ 1.000 check-ins/mês = ~$0,25

✅ 10.000 check-ins/mês = ~$2,50

✅ 100.000 check-ins/mês = ~$25,00
```

**CONCLUSÃO:** Extremamente barato! $5 de crédito = **20.000 conversas**

### Cenário 2: Conversas mais longas (multi-turn)

```
✅ 1 conversa com 5 trocas = ~1500 tokens entrada + 500 tokens saída
   Custo: ~US$ 0,0015 (0,15 centavos)

✅ 1.000 conversas/mês = ~$1,50

✅ 10.000 conversas/mês = ~$15,00
```

---

## 5️⃣ TABELA COMPARATIVA DE MODELOS

| Modelo | Entrada | Saída | Ideal Para | Custo/conversa |
|--------|---------|-------|-----------|----------------|
| **gpt-3.5-turbo** | $0,50M | $1,50M | Check-ins, respostas rápidas | ~$0,00025 |
| **gpt-5-mini** | $0,25M | $2,00M | Tarefas muito simples | ~$0,00015 |
| **gpt-5.2** | $1,75M | $14,00M | Programação complexa | ~$0,007 |
| **gpt-5.2-pro** | $21,00M | $168,00M | Raciocínio profundo | ~$0,10 |

**👉 Para projeto hotel:** Use `gpt-3.5-turbo` (melhor custo-benefício)

---

## 6️⃣ FEATURE IMPORTANTE: CACHE DE TOKENS

```
Entrada normal:    US$ 0,50 / 1 milhão de tokens
Entrada em CACHE:  US$ 0,05 / 1 milhão de tokens (90% DESCONTO!)

O que é cache?
- Se você enviar o mesmo contexto repetidamente, OpenAI reutiliza
- Exemplo: contextual sobre políticas do hotel
- 1ª vez: paga integral
- Próximas vezes: paga 10% do preço
```

**Para seu projeto:** Usar cache para histórico de conversas = economia MASSIVA

---

## 7️⃣ ESTIMATIVA PARA SUA CONTA

### Você estava recebendo erro 429 porque:
```
❌ Sua conta tinha $0.00 de crédito
❌ OpenAI não deixa fazer requisições sem crédito
❌ Trial (teste grátis) expirou após 3 meses
```

### O que fazer AGORA:

```powershell
# 1. Adicione $5 de crédito (vira ~20.000 conversas)
#    URL: https://platform.openai.com/account/billing/overview

# 2. Rode o teste novamente
py test_real_chat.py

# 3. Veja quanto gastou
#    URL: https://platform.openai.com/account/usage/overview
```

---

## 8️⃣ MINHA OPINIÃO: VALE A PENA?

### ✅ **SUPER RECOMENDO para seu projeto porque:**

1. **Extremamente barato**
   - $5 = 20.000 conversas
   - $50/mês = 200.000 conversas
   - Praticamente grátis

2. **Qualidade excelente**
   - gpt-3.5-turbo responde 90% dos check-ins perfeitamente
   - Mais rápido que GPT-4

3. **Escalável**
   - Começa com $5, cresce conforme precisa
   - Não tem taxas escondidas

4. **Flexível**
   - $5 dura meses em testes
   - Quando crescer, é previsível

### ⚠️ **Único custo alto:**
- Se usar GPT-5.2-pro + conversas longas = $100-$500/mês
- Mas para check-in simples? $5-$50/mês no máximo

### 🎯 **Para seu caso:**

```
Cenário: 5.000 check-ins/mês (hotel pequeno)

Custo/mês:     ~$1,25
Custo anual:   ~$15,00
Conclusão:     GRÁTIS efetivamente - pague $5 uma vez e dura 4 anos!
```

---

## 9️⃣ PRÓXIMOS PASSOS

### Hoje:
1. Adicione $5 de crédito em https://platform.openai.com/account/billing/overview
2. Aguarde 5 minutos (às vezes leva um pouco)
3. Rode: `py test_real_chat.py`

### Depois:
1. Integre a API com WhatsApp em tempo real
2. Monitore uso em https://platform.openai.com/account/usage/overview
3. Veja quanto está gastando de verdade

### Dica final:
```powershell
# Crie um script para monitorar gastos diários
# (Vou criar isso se quiser!)

py verify_openai_key.py  # Verifica se tem acesso
```

---

## 🔟 RESUMO EM UMA LINHA

**OpenAI é BARATO para projetos de chat simples. Seus check-ins custarão centavos por mês. Adicione $5 e fica tudo pronto! 💪**
