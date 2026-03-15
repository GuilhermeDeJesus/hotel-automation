"""Test runner para todos os testes de multi-tenancy."""

import pytest
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tenant_tests():
    """Executa todos os testes de multi-tenancy."""
    
    test_modules = [
        "tests.test_multi_tenant_isolation",
        "tests.test_tenant_api_isolation", 
        "tests.test_tenant_performance"
    ]
    
    print("🧪 Executando Testes de Multi-Tenancy")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for module in test_modules:
        print(f"\n📋 Testando módulo: {module}")
        print("-" * 40)
        
        try:
            result = pytest.main([module, "-v", "--tb=short"])
            
            # pytest retorna 0 para sucesso, 1 para falha
            if result == 0:
                print(f"✅ {module}: Todos os testes passaram")
                total_passed += 1
            else:
                print(f"❌ {module}: Alguns testes falharam")
                total_failed += 1
                
        except Exception as e:
            print(f"⚠️  {module}: Erro ao executar - {str(e)}")
            total_failed += 1
    
    print("\n" + "=" * 60)
    print("📊 Resumo dos Testes de Multi-Tenancy")
    print("=" * 60)
    print(f"✅ Módulos passados: {total_passed}")
    print(f"❌ Módulos falhados: {total_failed}")
    print(f"📈 Taxa de sucesso: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    
    if total_failed == 0:
        print("\n🎉 Todos os testes de multi-tenancy passaram!")
        print("🔒 Isolamento de dados está funcionando corretamente.")
    else:
        print(f"\n⚠️  {total_failed} módulo(s) falharam. Verifique os logs acima.")
    
    return total_failed == 0


def run_isolation_tests_only():
    """Executa apenas testes de isolamento (críticos)."""
    print("🔒 Executando Testes Críticos de Isolamento")
    print("=" * 60)
    
    critical_tests = [
        "tests.test_multi_tenant_isolation::TestMultiTenantIsolation::test_room_isolation_between_hotels",
        "tests.test_multi_tenant_isolation::TestMultiTenantIsolation::test_reservation_isolation_between_hotels", 
        "tests.test_multi_tenant_isolation::TestMultiTenantIsolation::test_cross_hotel_data_leak_prevention",
        "tests.test_tenant_api_isolation::TestTenantAPIIsolation::test_user_cannot_access_other_hotel_rooms"
    ]
    
    result = pytest.main(critical_tests + ["-v", "--tb=short"])
    
    if result == 0:
        print("\n✅ Testes críticos de isolamento passaram!")
        print("🔒 Sistema está seguro contra vazamento de dados entre hotéis.")
    else:
        print("\n❌ Testes críticos de isolamento falharam!")
        print("🚨 RISCO DE SEGURANÇA: Isolamento de dados comprometido!")
    
    return result == 0


def run_performance_tests_only():
    """Executa apenas testes de performance."""
    print("⚡ Executando Testes de Performance")
    print("=" * 60)
    
    result = pytest.main([
        "tests.test_tenant_performance",
        "-v", 
        "--tb=short"
    ])
    
    if result == 0:
        print("\n✅ Testes de performance passaram!")
        print("🚀 Isolamento multi-tenant não impacta performance.")
    else:
        print("\n❌ Testes de performance falharam!")
        print("⚠️  Performance pode estar comprometida.")
    
    return result == 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test runner para multi-tenancy")
    parser.add_argument(
        "--type", 
        choices=["all", "isolation", "performance"],
        default="all",
        help="Tipo de teste para executar"
    )
    
    args = parser.parse_args()
    
    if args.type == "all":
        success = run_all_tenant_tests()
    elif args.type == "isolation":
        success = run_isolation_tests_only()
    elif args.type == "performance":
        success = run_performance_tests_only()
    
    sys.exit(0 if success else 1)
