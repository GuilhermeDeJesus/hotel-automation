#!/usr/bin/env python3.14
"""
Test conversation using mocks (no API calls, no quota needed).
"""
import sys
import os

# Force use of the correct Python installation
if 'msys64' in sys.executable.lower():
    print("❌ ERROR: Using wrong Python. Use 'py' instead")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.application.use_cases.conversation import ConversationUseCase
from tests.unit.mocks.ai_service_mock import AIServiceMock

class SimpleCache:
    def __init__(self):
        self.store = {}
    
    def get(self, key):
        return self.store.get(key)
    
    def set(self, key, value, ttl_seconds: int = 3600):
        self.store[key] = value
    
    def delete(self, key):
        self.store.pop(key, None)
    
    def exists(self, key):
        return key in self.store
    
    def clear(self):
        self.store.clear()

class SimpleMessenger:
    def send(self, phone, message):
        print(f"[MESSENGER] Para {phone}: {message}")

def main():
    print("=" * 70)
    print("💬 Test Conversation (Using Mocks - No API Calls)")
    print("=" * 70)
    print("")
    
    try:
        # Configure mock to return specific responses
        mock_ai = AIServiceMock(
            responses={
                "Olá, como você está?": "Olá! Tudo bem com você?",
                "Qual é o seu nome?": "Sou um assistente de IA para hotel",
                "Me ajude com um check-in": "Claro! Vou ajudar com o check-in",
            }
        )
        
        repo = ReservationRepositoryMemory()
        cache = SimpleCache()
        messenger = SimpleMessenger()
        
        use_case = ConversationUseCase(
            ai_service=mock_ai,
            reservation_repo=repo,
            cache_repository=cache,
            messaging=messenger,
        )
        
        phone = "mock-user"
        
        # Test 1
        print("📝 Enviando mensagem 1: 'Olá, como você está?'")
        response1 = use_case.execute(phone, "Olá, como você está?")
        print(f"✓ Resposta: {response1}\n")
        
        # Test 2 (with history)
        print("📝 Enviando mensagem 2: 'Qual é o seu nome?'")
        response2 = use_case.execute(phone, "Qual é o seu nome?")
        print(f"✓ Resposta: {response2}\n")
        
        # Test 3 (with more history)
        print("📝 Enviando mensagem 3: 'Me ajude com um check-in'")
        response3 = use_case.execute(phone, "Me ajude com um check-in")
        print(f"✓ Resposta: {response3}\n")
        
        # Show full history
        history = cache.get(phone) or []
        print("=" * 70)
        print(f"📊 Histórico Completo ({len(history)} mensagens)")
        print("=" * 70)
        for i, msg in enumerate(history, 1):
            role = "👤 User" if msg.get("role") == "user" else "🤖 AI"
            content = msg.get("content", "")[:60]
            print(f"{i}. {role}: {content}")
        
        print("\n✅ Teste concluído com sucesso!")
        print(f"✅ Total de iterações com IA: {len([m for m in history if m.get('role') == 'assistant'])}")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
