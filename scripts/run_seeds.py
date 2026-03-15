"""Script para executar todos os seeds multi-tenant."""
import subprocess
import sys
import os

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_seed_script(script_name: str, args: list = None) -> bool:
    """Executa um script de seed e retorna se teve sucesso."""
    try:
        cmd = [sys.executable, f"scripts/{script_name}"]
        if args:
            cmd.extend(args)
        
        print(f"🚀 Executando: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ {script_name} executado com sucesso!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Erro ao executar {script_name}:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Exceção ao executar {script_name}: {str(e)}")
        return False


def seed_all_multi_tenant_data():
    """Executa todos os scripts de seed multi-tenant."""
    print("🏨 Iniciando seed completo de dados multi-tenant...")
    print("=" * 60)
    
    scripts = [
        ("seed_multi_tenant.py", []),
        ("seed_test_users.py", []),
    ]
    
    success_count = 0
    
    for script_name, args in scripts:
        if run_seed_script(script_name, args):
            success_count += 1
        print()
    
    print("=" * 60)
    if success_count == len(scripts):
        print("🎉 TODOS os seeds multi-tenant executados com sucesso!")
        print("\n📊 Dados criados:")
        print("  • 3 hotéis completos com quartos")
        print("  • 11+ usuários de teste com diferentes permissões")
        print("  • Clientes e reservas de exemplo")
        print("  • Cenários completos para testar isolamento")
        
        print("\n🔑 Principais credenciais de teste:")
        print("  • Super Admin: superadmin.test@system.com / test123")
        print("  • Admin Paradise: admin.test@paradise.com / test123")
        print("  • User Paradise: user.test@paradise.com / test123")
        print("  • Admin Montanha: admin.test@montanha.com / test123")
        
        print("\n🧪 Para testar isolamento:")
        print("  1. Execute os testes: python -m pytest tests/test_simple_tenant_isolation.py -v")
        print("  2. Faça login com usuários diferentes e verifique o isolamento")
        print("  3. Teste acesso cross-hotel com super admin")
        
        return True
    else:
        print(f"⚠️  {len(scripts) - success_count} scripts falharam. Verifique os erros acima.")
        return False


def seed_single_hotel_mode():
    """Executa apenas o seed de hotel único (modo compatibilidade)."""
    print("🏨 Executando seed de hotel único (modo compatibilidade)...")
    print("=" * 60)
    
    success = run_seed_script("seed_hotel.py")
    
    if success:
        print("✅ Seed de hotel único executado!")
        print("📝 Use este modo para desenvolvimento single-tenant")
    else:
        print("❌ Falha no seed de hotel único")
    
    return success


def seed_performance_mode():
    """Executa seeds para testes de performance."""
    print("⚡ Executando seeds para testes de performance...")
    print("=" * 60)
    
    scripts = [
        ("seed_multi_tenant.py", []),
        ("seed_test_users.py", ["--performance"]),
    ]
    
    success_count = 0
    for script_name, args in scripts:
        if run_seed_script(script_name, args):
            success_count += 1
        print()
    
    print("=" * 60)
    if success_count == len(scripts):
        print("⚡ Seeds de performance executados com sucesso!")
        print("📊 Dados criados:")
        print("  • 3 hotéis com dados completos")
        print("  • 100+ usuários distribuídos nos hotéis")
        print("  • Cenários para testes de carga")
        return True
    else:
        print(f"⚠️  {len(scripts) - success_count} scripts falharam")
        return False


def reset_all_data():
    """Remove todos os dados do banco (cuidado!)."""
    print("🗑️  ATENÇÃO: Isso vai APAGAR todos os dados do banco!")
    print("Deseja continuar? (y/N)")
    
    response = input().strip().lower()
    if response != 'y':
        print("❌ Operação cancelada.")
        return False
    
    # Aqui poderíamos adicionar código para limpar tabelas
    # Por enquanto, apenas instruímos o usuário
    print("\n📝 Para resetar completamente o banco:")
    print("  1. Docker: docker compose down -v && docker compose up -d")
    print("  2. Ou manualmente: DROP DATABASE hotel; CREATE DATABASE hotel;")
    print("  3. Depois execute: python scripts/run_seeds.py --multi")
    
    return True


def show_help():
    """Mostra ajuda de uso."""
    print("🚀 Script de Seeds Multi-Tenant")
    print("=" * 40)
    print("\nUso:")
    print("  python scripts/run_seeds.py [opção]")
    print("\nOpções:")
    print("  --multi      : Executa seeds multi-tenant completo (padrão)")
    print("  --single     : Executa apenas hotel único (compatibilidade)")
    print("  --performance: Executa seeds para testes de performance")
    print("  --reset      : Instruções para resetar banco de dados")
    print("  --help       : Mostra esta ajuda")
    print("\nExemplos:")
    print("  python scripts/run_seeds.py")
    print("  python scripts/run_seeds.py --multi")
    print("  python scripts/run_seeds.py --single")
    print("  python scripts/run_seeds.py --performance")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        option = sys.argv[1]
        
        if option == "--multi":
            success = seed_all_multi_tenant_data()
        elif option == "--single":
            success = seed_single_hotel_mode()
        elif option == "--performance":
            success = seed_performance_mode()
        elif option == "--reset":
            success = reset_all_data()
        elif option == "--help":
            show_help()
            success = True
        else:
            print(f"❌ Opção desconhecida: {option}")
            show_help()
            success = False
    else:
        # Padrão: executar seeds multi-tenant
        success = seed_all_multi_tenant_data()
    
    sys.exit(0 if success else 1)
