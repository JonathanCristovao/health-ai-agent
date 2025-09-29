#!/usr/bin/env python3
"""
Setup inicial do banco DATASUS
================================
        print(f"Tamanho do banco: {stats['tamanho_mb']} MB")
        print(f"Total de registros: {stats['total_registros']:,}")
        print(f"Período: {stats['periodo']}")
        print(f"Anos disponíveis: {stats['anos_disponiveis']}")

        print("\nStatus por ano:")
        for year, info in stats['status_por_ano'].items():
            status_emoji = "OK" if info['status'] == 'SUCCESS' else "ERRO"rint(f"Anos disponíveis: {stats['anos_disponiveis']}")

        print("\nStatus por ano:")
        for year, info in stats['status_por_ano'].items():
            status_emoji = "OK" if info['status'] == 'SUCCESS' else "ERRO" para inicializar o sistema pela primeira vez:
1. Executar ETL completo
2. Verificar integridade dos dados
3. Gerar relatório de status

Uso:
    python setup_datasus.py
    python setup_datasus.py --quick  # Apenas anos mais recentes
"""

from database.datasus_client import DataSUSDatabase, check_database
from scripts.datasus_etl import DataSUSETL
import os
import sys
import time
import argparse
from pathlib import Path


sys.path.append(str(Path(__file__).parent))


def setup_database(quick_mode: bool = False):
    """Setup completo do banco DATASUS"""

    print("INICIANDO SETUP DO BANCO DATASUS")
    print("=" * 50)

    start_time = time.time()
    etl = DataSUSETL()

    if quick_mode:
        years = [2023, 2024]
        print("Modo rápido: processando apenas 2023-2024")
    else:
        years = list(etl.DATASUS_URLS.keys())
        print(f"Modo completo: processando {len(years)} anos")

    successful = 0
    failed = 0

    for year in years:
        print(f"\n{'='*30}")
        print(f"Processando {year}...")
        print(f"{'='*30}")

        success = etl.process_year(year)
        if success:
            successful += 1
            print(f"{year} processado com sucesso")
        else:
            failed += 1
            print(f"Falha no processamento de {year}")

    total_time = time.time() - start_time

    print(f"\nSETUP CONCLUÍDO EM {total_time:.2f}s")
    print("=" * 50)
    print(f"Sucessos: {successful}")
    print(f"Falhas: {failed}")
    print(f"Total: {successful + failed}")

    if successful > 0:
        print("\nRELATÓRIO DO BANCO:")
        generate_status_report()
    else:
        print("\nNENHUM DADO FOI PROCESSADO COM SUCESSO")
        return False

    return failed == 0


def generate_status_report():
    """Gerar relatório de status do banco"""

    try:
        if not check_database():
            print("Banco não está disponível")
            return

        db = DataSUSDatabase()
        stats = db.get_database_info()

        print(f"Tamanho do banco: {stats['tamanho_mb']} MB")
        print(f"Total de registros: {stats['total_registros']:,}")
        print(f"Período: {stats['periodo']}")
        print(f"Anos disponíveis: {stats['anos_disponiveis']}")

        print("\nStatus por ano:")
        for year, info in stats['status_anos'].items():
            status_emoji = "v" if info['status'] == 'SUCCESS' else "X"
            print(f"  {status_emoji} {year}: {info['registros']:,} registros (qualidade: {info['qualidade']:.1%})")

        print("\nTeste de funcionalidade:")

        available_years = db.get_years_available()
        if available_years:
            test_year = available_years[-1]
            test_data = db.get_data(year=test_year, limit=10)

            if len(test_data) > 0:
                print(f"Consulta básica: {len(test_data)} registros obtidos para {test_year}")
                try:
                    from database.datasus_client import get_vaccination_answer
                    vaccination_result = get_vaccination_answer("teste", test_year)
                    if "Erro" not in vaccination_result:
                        print("Análise de vacinação: funcionando")
                    else:
                        print("Análise de vacinação: com problemas")
                except Exception as e:
                    print(f"Análise de vacinação: erro ({str(e)})")
            else:
                print(f"Consulta básica: nenhum registro encontrado para {test_year}")
        else:
            print("Nenhum ano disponível no banco")

        print("\nBANCO CONFIGURADO E FUNCIONAL!")

    except Exception as e:
        print(f"Erro ao gerar relatório: {str(e)}")


def check_prerequisites():
    """Verificar pré-requisitos do sistema"""

    print("Verificando pré-requisitos...")

    required_modules = ['pandas', 'numpy', 'requests', 'sqlite3', 'tqdm']
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"OK {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"ERRO {module}")

    if missing_modules:
        print(f"\nMódulos faltando: {', '.join(missing_modules)}")
        print("Execute: pip install -r requirements.txt")
        return False

    try:
        disk_space = os.statvfs('.').f_bavail * os.statvfs('.').f_frsize / (1024 * 1024)  # MB
        if disk_space < 1000:  # 1GB de margem
            print(f"ATENÇÃO: Pouco espaço em disco: {disk_space:.0f} MB disponível")
        else:
            print(f"Espaço em disco: {disk_space:.0f} MB disponível")
    except BaseException:
        print("Não foi possível verificar espaço em disco")

    return len(missing_modules) == 0


def main():
    """Função principal"""

    parser = argparse.ArgumentParser(description="Setup inicial do banco DATASUS")
    parser.add_argument("--quick", action="store_true", help="Processar apenas anos recentes (2023-2024)")
    parser.add_argument("--force", action="store_true", help="Forçar reprocessamento mesmo se dados existirem")
    parser.add_argument("--status", action="store_true", help="Apenas mostrar status atual")

    args = parser.parse_args()

    if args.status:
        print("STATUS ATUAL DO BANCO DATASUS")
        print("=" * 40)
        generate_status_report()
        return

    if not check_prerequisites():
        print("\nPré-requisitos não atendidos. Corrija os problemas acima.")
        sys.exit(1)

    if not args.force and check_database():
        print("\nBanco DATASUS já existe e está funcional!")
        print("Use --force para reprocessar ou --status para ver detalhes")

        generate_status_report()
        return

    success = setup_database(quick_mode=args.quick)

    if success:
        print("\nSETUP CONCLUÍDO COM SUCESSO!")
        print("O sistema está pronto para uso!")
        print("Execute o frontend: streamlit run frontend.py")
    else:
        print("\nSETUP FALHOU")
        print("Verifique os logs de erro acima")
        sys.exit(1)


if __name__ == "__main__":
    main()
