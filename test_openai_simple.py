#!/usr/bin/env python3.14
"""
Simple test of OpenAI integration without interactive input.
"""
import sys
import os

# Force use of the correct Python installation (skip MSYS)
if 'msys64' in sys.executable.lower():
    print("❌ ERROR: Using wrong Python (MSYS). Use 'py test_openai_simple.py' instead")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.ai.openai_client import OpenAIClient
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.application.use_cases.conversation import ConversationUseCase

class SimpleCache:
    def __init__(self):
        self.store = {}
    
    def get(self, key):
        return self.store.get(key)
    
    def set(self, key, value):
        self.store[key] = value

class SimpleMessenger:
    def send(self, phone, message):
        print(f"[MESSENGER] Enviando para {phone}: {message}")

def main():
    # Verify API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)
    
    print("=" * 70)
    print("🤖 OpenAI Integration Test")
    print("=" * 70)
    print(f"API Key configurada: ✓")
    print("")
    
    try:
        # Initialize
        print("⏳ Inicializando OpenAIClient...")
        ai_client = OpenAIClient(api_key=api_key)
        print("✓ OpenAIClient inicializado")
        
        print("⏳ Inicializando repositórios...")
        repo = ReservationRepositoryMemory()
        cache = SimpleCache()
        messenger = SimpleMessenger()
        print("✓ Repositórios inicializados")
        
        print("⏳ Criando ConversationUseCase...")
        use_case = ConversationUseCase(
            ai_service=ai_client,
            reservation_repo=repo,
            cache_repository=cache,
            messaging=messenger,
        )
        print("✓ ConversationUseCase criada")
        
        phone = "test-user"
        
        # Test 1: Simple greeting
        print("📝 Test 1: Enviando 'Olá, como você está?'")
        print("-" * 70)
        response1 = use_case.execute(phone, "Olá, como você está?")
        print(f"✓ Resposta: {response1}\n")
        
        # Test 2: Follow-up with history
        print("📝 Test 2: Enviando 'Qual é o seu nome?'")
        print("-" * 70)
        response2 = use_case.execute(phone, "Qual é o seu nome?")
        print(f"✓ Resposta: {response2}\n")
        
        # Check history
        history = cache.get(phone)
        print("=" * 70)
        print(f"📊 Histórico de conversa: {len(history)} mensagens")
        print("=" * 70)
        for i, msg in enumerate(history, 1):
            role = "👤 User" if msg.get("role") == "user" else "🤖 AI"
            content = msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
            print(f"{i}. {role}: {content}")
        
        print("\n✅ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
