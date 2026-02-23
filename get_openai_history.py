#!/usr/bin/env python3.14
"""
Ferramentas para acessar histórico de uso OpenAI via API.

OpenAI NÃO fornece API para recuperar logs de conversas passadas, mas você pode:
1. Ver tudo no dashboard web
2. Consultar dados de uso/faturamento
3. Manter seu próprio log das conversas
"""
import sys
import os
from datetime import datetime, timedelta

if 'msys64' in sys.executable.lower():
    print("❌ Use: py get_openai_history.py")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import openai


def metodo_1_dashboard_web():
    """Método 1: Mais fácil e completo - Dashboard Web"""
    print("\n" + "=" * 70)
    print("📊 MÉTODO 1: Ver Histórico no Dashboard Web (RECOMENDADO)")
    print("=" * 70)
    print("""
    ✅ LINKS DOS DASHBOARDS:
    
    1️⃣ Ver todas as requisições
       https://platform.openai.com/account/usage/overview
       
    2️⃣ Ver detalhes de faturamento
       https://platform.openai.com/account/billing/history
       
    3️⃣ Dados em tempo real
       https://platform.openai.com/account/usage/detailed
    
    ✅ O QUE VOCÊ VÊ LÁ:
    • Data/hora de cada requisição
    • Modelo usado (gpt-3.5-turbo, etc)
    • Tokens de entrada/saída
    • Custo em dólares
    • Tempo de processamento
    
    ⚠️ IMPORTANTE:
    • Leva alguns minutos para atualizar
    • Agrupa por dia/hora
    • NÃO mostra conteúdo das mensagens (privado)
    """)


def metodo_2_api_dados_uso():
    """Método 2: Via API (apenas dados de uso, sem conteúdo)"""
    print("\n" + "=" * 70)
    print("🔗 MÉTODO 2: Via OpenAI API (Apenas Dados de Uso)")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY não configurada")
        return
    
    print("\n⏳ Consultando dados de uso da API...")
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Infelizmente, OpenAI deprecated a API de usage em favor do dashboard
        print("""
        ⚠️  OpenAI removeu a API pública de histórico de requisições.
        
        Opções disponíveis:
        1. Dashboard web (acima)
        2. Exportar dados de faturamento (abaixo)
        3. Manter seu próprio log (meu_log_requisicoes.py)
        """)
        
    except Exception as e:
        print(f"❌ Erro: {e}")


def metodo_3_seu_proprio_log():
    """Método 3: Manter seu próprio log"""
    print("\n" + "=" * 70)
    print("📝 MÉTODO 3: Manter Seu Próprio Log (Recomendado para App)")
    print("=" * 70)
    print("""
    ✅ CRIE UM ARQUIVO: app/infrastructure/logging/conversation_logger.py
    
    Ele mantém registro de TODAS as conversas:
    • Timestamp
    • Phone/User ID
    • Mensagem do usuário
    • Resposta do AI
    • Tokens gastos
    • Custo estimado
    
    Exemplo em: meu_log_requisicoes.py (criado neste diretório)
    """)


def example_seu_proprio_log():
    """Mostrar exemplo de como implementar seu próprio log"""
    print("\n" + "=" * 70)
    print("💡 EXEMPLO: Implementar Seu Próprio Log")
    print("=" * 70)
    
    exemplo = '''
import json
from datetime import datetime

class ConversationLogger:
    """Registra todas as conversas com timestamps e custos."""
    
    def __init__(self, log_file: str = "conversation_history.json"):
        self.log_file = log_file
        self.load_or_create()
    
    def load_or_create(self):
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.conversations = json.load(f)
        except FileNotFoundError:
            self.conversations = []
    
    def log_interaction(self, phone: str, user_msg: str, ai_response: str, 
                       tokens_used: int, cost: float):
        """Registra uma interação."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phone": phone,
            "user_message": user_msg,
            "ai_response": ai_response,
            "tokens_used": tokens_used,
            "estimated_cost_usd": cost
        }
        self.conversations.append(entry)
        self.save()
    
    def save(self):
        """Salva em arquivo JSON."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversations, f, indent=2, ensure_ascii=False)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas."""
        total = len(self.conversations)
        total_tokens = sum(c["tokens_used"] for c in self.conversations)
        total_cost = sum(c["estimated_cost_usd"] for c in self.conversations)
        
        return {
            "total_interactions": total,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_cost_per_interaction": total_cost / total if total > 0 else 0
        }


# Uso:
logger = ConversationLogger()
logger.log_interaction(
    phone="5511999999999",
    user_msg="Olá, preciso de check-in",
    ai_response="Bem-vindo ao hotel!",
    tokens_used=45,
    cost=0.00015
)
    '''
    print(exemplo)


def links_uteis():
    """Mostrar links úteis"""
    print("\n" + "=" * 70)
    print("🔗 LINKS ÚTEIS")
    print("=" * 70)
    print("""
    📊 DASHBOARDS:
    • Usage & Billing: https://platform.openai.com/account/usage/overview
    • Detailed Usage: https://platform.openai.com/account/usage/detailed
    • Billing Overview: https://platform.openai.com/account/billing/overview
    • API Keys: https://platform.openai.com/api-keys
    
    📚 DOCUMENTAÇÃO:
    • OpenAI API Docs: https://platform.openai.com/docs/api-reference
    • Usage Documentation: https://platform.openai.com/docs/guides/rate-limits
    • Billing Guide: https://platform.openai.com/docs/guides/tokens
    
    🛠️ FERRAMENTAS:
    • OpenAI Python SDK: https://github.com/openai/openai-python
    • CLI Tool: https://github.com/openai/openai-python#command-line-interface
    """)


def main():
    print("\n" + "=" * 70)
    print("🔍 COMO VER HISTÓRICO DE REQUISIÇÕES OpenAI")
    print("=" * 70)
    
    metodo_1_dashboard_web()
    metodo_2_api_dados_uso()
    metodo_3_seu_proprio_log()
    example_seu_proprio_log()
    links_uteis()
    
    print("\n" + "=" * 70)
    print("✅ RESUMO")
    print("=" * 70)
    print("""
    🥇 MELHOR OPÇÃO: Dashboard Web
       → https://platform.openai.com/account/usage/overview
       → Veja tudo em detalhes
       → Atualiza em tempo real
    
    🥈 PARA SEU PROJETO: Implementar seu próprio log
       → Crie conversation_logger.py
       → Salve em JSON/banco de dados
       → Controle total de dados
    
    🔔 IMPORTANTE:
       • OpenAI NÃO fornece API para recuperar histórico de chats completo
       • Eles ocultam conteúdo (privacidade)
       • Você só vê estatísticas (tokens, custo, timestamp)
       • Implementar seu próprio log é a melhor prática!
    """)


if __name__ == "__main__":
    main()
