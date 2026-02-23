#!/usr/bin/env python3.14
"""
Visualizador de Histórico de Conversas OpenAI.

Mostra todas as interações registradas em JSON com estatísticas de uso e custo.
"""
import sys
import os
from datetime import datetime

if 'msys64' in sys.executable.lower():
    print("❌ Use: py view_conversation_history.py")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.logging.conversation_logger import ConversationLogger


def print_menu():
    """Print main menu."""
    print("\n" + "=" * 70)
    print("📝 VISUALIZADOR DE HISTÓRICO DE CONVERSAS")
    print("=" * 70)
    print("""
  1. Ver estatísticas gerais
  2. Ver últimas conversas
  3. Buscar por número de telefone
  4. Buscar por data
  5. Exportar para CSV
  6. Limpar histórico
  0. Sair
    """)


def view_stats(logger: ConversationLogger):
    """View general statistics."""
    logger.print_stats()


def view_recent(logger: ConversationLogger):
    """View recent conversations."""
    try:
        n = int(input("\nQuantos últimas conversas deseja ver? (padrão: 5): ") or "5")
        logger.print_recent(n)
    except ValueError:
        print("❌ Número inválido")


def search_by_phone(logger: ConversationLogger):
    """Search by phone number."""
    phone = input("\nDigite o número de telefone: ").strip()
    
    interactions = logger.get_by_phone(phone)
    
    if not interactions:
        print(f"\n❌ Nenhuma conversa encontrada para {phone}")
        return
    
    print(f"\n📱 {len(interactions)} conversa(s) para {phone}:")
    print("-" * 70)
    
    for i in interactions:
        print(f"\n[{i['id']}] {i['timestamp']}")
        print(f"  User: {i['user_message'][:60]}...")
        print(f"  AI:   {i['ai_response'][:60]}...")
        print(f"  Cost: ${i['cost']['total_usd']:.6f}")


def search_by_date(logger: ConversationLogger):
    """Search by date."""
    date_str = input("\nDigite a data (YYYY-MM-DD), ou deixe em branco para hoje: ").strip()
    
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    interactions = logger.get_by_date(date_str)
    
    if not interactions:
        print(f"\n❌ Nenhuma conversa em {date_str}")
        return
    
    print(f"\n📅 {len(interactions)} conversa(s) em {date_str}:")
    print("-" * 70)
    
    total_cost = sum(i['cost']['total_usd'] for i in interactions)
    total_tokens = sum(i['tokens']['total'] for i in interactions)
    
    for i in interactions:
        print(f"\n[{i['id']}] {i['time']} - {i['phone']}")
        print(f"  User: {i['user_message'][:50]}...")
        print(f"  AI:   {i['ai_response'][:50]}...")
        print(f"  Cost: ${i['cost']['total_usd']:.6f}")
    
    print(f"\n📊 Total do dia: {total_tokens} tokens | ${total_cost:.6f}")


def export_csv(logger: ConversationLogger):
    """Export to CSV."""
    output_file = input("\nNome do arquivo CSV (padrão: conversation_export.csv): ").strip()
    if not output_file:
        output_file = "conversation_export.csv"
    
    try:
        logger.export_csv(output_file)
    except Exception as e:
        print(f"❌ Erro ao exportar: {e}")


def clear_history(logger: ConversationLogger):
    """Clear conversation history."""
    confirm = input("\n⚠️  Tem certeza que quer deletar TODO o histórico? (s/n): ").lower()
    
    if confirm == 's':
        logger.conversations = []
        logger._save()
        print("✅ Histórico deletado")
    else:
        print("❌ Cancelado")


def main():
    """Main menu loop."""
    # Load logger
    log_file = "logs/conversation_history.json"
    
    if not os.path.exists(log_file):
        print("\n❌ Nenhum histórico encontrado!")
        print(f"   Execute primeiro: py scripts/interactive_conversation.py")
        print(f"   Arquivo esperado: {log_file}")
        return
    
    logger = ConversationLogger()
    
    if not logger.conversations:
        print("\n⚠️  Histórico vazio!")
        return
    
    print("\n✅ Histórico carregado")
    print(f"   Total de conversas: {len(logger.conversations)}")
    
    while True:
        print_menu()
        choice = input("Escolha uma opção: ").strip()
        
        try:
            if choice == "1":
                view_stats(logger)
            elif choice == "2":
                view_recent(logger)
            elif choice == "3":
                search_by_phone(logger)
            elif choice == "4":
                search_by_date(logger)
            elif choice == "5":
                export_csv(logger)
            elif choice == "6":
                clear_history(logger)
            elif choice == "0":
                print("\n👋 Até logo!")
                break
            else:
                print("❌ Opção inválida")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrompido pelo usuário")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
