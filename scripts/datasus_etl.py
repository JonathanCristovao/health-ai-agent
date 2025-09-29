#!/usr/bin/env python3
"""
ETL Pipeline para Dados DATASUS
====================================

Script completo para:
1. Extrair dados do DATASUS (URLs oficiais)
2. Transformar e limpar dados
3. Carregar em banco SQLite

Uso:
    python scripts/datasus_etl.py --year 2024
    python scripts/datasus_etl.py --all-years
    python scripts/datasus_etl.py --update-all
"""

import sys
import sqlite3
import pandas as pd
import requests
import argparse
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, Optional
import hashlib
import time
from tqdm import tqdm
import warnings

# Suprimir warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('datasus_etl.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataSUSETL:
    """Pipeline ETL completo para dados DATASUS"""

    # URLs oficiais do DATASUS
    DATASUS_URLS = {
        2019: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2019/INFLUD19-26-06-2025.csv",
        2020: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2020/INFLUD20-26-06-2025.csv",
        2021: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2021/INFLUD21-26-06-2025.csv",
        2022: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2022/INFLUD22-26-06-2025.csv",
        2023: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2023/INFLUD23-26-06-2025.csv",
        2024: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2024/INFLUD24-26-06-2025.csv",
        2025: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-22-09-2025.csv"
    }

    # Colunas essenciais para manter
    ESSENTIAL_COLUMNS = [
        'DT_NOTIFIC',    # Data notificação
        'DT_SIN_PRI',    # Data primeiros sintomas
        'DT_INTERNA',    # Data internação
        'DT_EVOLUCA',    # Data evolução
        'SG_UF',         # UF
        'ID_MUNICIP',    # Município
        'CS_SEXO',       # Sexo
        'NU_IDADE_N',    # Idade
        'EVOLUCAO',      # Evolução (óbito/cura)
        'UTI',           # Internação UTI
        'VACINA',        # Vacinação
        'CLASSI_FIN',    # Classificação final
        'FEBRE',         # Sintomas
        'TOSSE',
        'GARGANTA',
        'DISPNEIA',
        'DESC_RESP',
        'SATURACAO',
        'DIARREIA',
        'VOMITO',
        'OUTRO_SIN',
        'CARDIOPATI',    # Comorbidades
        'HEMATOLOGI',
        'SIND_DOWN',
        'HEPATICA',
        'ASMA',
        'DIABETES',
        'NEUROLOGIC',
        'PNEUMOPATI',
        'IMUNODEPRE',
        'RENAL',
        'OBESIDADE'
    ]

    def __init__(self, db_path: str = "data/datasus.db"):
        """Inicializar ETL"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path("temp_downloads")
        self.temp_dir.mkdir(exist_ok=True)

        # Conectar banco
        self.init_database()

    def init_database(self):
        """Inicializar estrutura do banco SQLite"""
        logger.info("Inicializando banco de dados SQLite...")

        with sqlite3.connect(self.db_path) as conn:
            # Tabela principal de dados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS srag_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    dt_notific DATE,
                    dt_sin_pri DATE,
                    dt_interna DATE,
                    dt_evoluca DATE,
                    sg_uf TEXT,
                    id_municip TEXT,
                    cs_sexo INTEGER,
                    cs_sexo_desc TEXT,
                    nu_idade_n INTEGER,
                    faixa_etaria TEXT,
                    evolucao INTEGER,
                    evolucao_desc TEXT,
                    uti INTEGER,
                    uti_desc TEXT,
                    vacina INTEGER,
                    vacina_desc TEXT,
                    classi_fin INTEGER,
                    classi_fin_desc TEXT,

                    -- Sintomas (0=não, 1=sim, 2=ignorado, 9=não se aplica)
                    febre INTEGER,
                    tosse INTEGER,
                    garganta INTEGER,
                    dispneia INTEGER,
                    desc_resp INTEGER,
                    saturacao INTEGER,
                    diarreia INTEGER,
                    vomito INTEGER,
                    outro_sin INTEGER,

                    -- Comorbidades
                    cardiopati INTEGER,
                    hematologi INTEGER,
                    sind_down INTEGER,
                    hepatica INTEGER,
                    asma INTEGER,
                    diabetes INTEGER,
                    neurologic INTEGER,
                    pneumopati INTEGER,
                    imunodepre INTEGER,
                    renal INTEGER,
                    obesidade INTEGER,

                    -- Metadata
                    mes_notific INTEGER,
                    ano_notific INTEGER,
                    semana_epidemio INTEGER,
                    regiao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(year, dt_notific, sg_uf, cs_sexo, nu_idade_n, evolucao)
                )
            """)

            # Tabela de metadados do ETL
            conn.execute("""
                CREATE TABLE IF NOT EXISTS etl_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER UNIQUE,
                    url TEXT,
                    download_date TIMESTAMP,
                    file_hash TEXT,
                    total_records INTEGER,
                    processed_records INTEGER,
                    data_quality_score REAL,
                    processing_time_seconds REAL,
                    status TEXT,
                    error_log TEXT
                )
            """)

            # Índices para performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON srag_data(year)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_uf ON srag_data(sg_uf)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dt_notific ON srag_data(dt_notific)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evolucao ON srag_data(evolucao)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacina ON srag_data(vacina)")

            conn.commit()

        logger.info("✅ Banco de dados inicializado com sucesso")

    def download_data(self, year: int) -> Optional[Path]:
        """Download dos dados do DATASUS"""
        if year not in self.DATASUS_URLS:
            logger.error(f"Ano {year} não disponível")
            return None

        url = self.DATASUS_URLS[year]
        filename = f"INFLUD{year}.csv"
        filepath = self.temp_dir / filename

        logger.info(f"Baixando dados de {year}...")
        logger.info(f"URL: {url}")

        try:
            # Verificar se já existe e está atualizado
            if filepath.exists():
                # Verificar hash no banco
                with sqlite3.connect(self.db_path) as conn:
                    result = conn.execute(
                        "SELECT file_hash, download_date FROM etl_metadata WHERE year = ?",
                        (year,)
                    ).fetchone()

                    if result:
                        stored_hash, download_date = result
                        current_hash = self._calculate_file_hash(filepath)

                        if stored_hash == current_hash:
                            logger.info(f"Arquivo {year} já está atualizado")
                            return filepath

            # Download com progress bar
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            with open(filepath, 'wb') as f, tqdm(
                desc=f"Baixando {year}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            logger.info(f"✅ Download concluído: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Erro no download de {year}: {str(e)}")
            return None

    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calcular hash MD5 do arquivo"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def extract_data(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Extrair dados do CSV com múltiplas estratégias"""
        logger.info(f"Extraindo dados de {filepath.name}...")

        # Estratégias de parsing
        strategies = [
            {'encoding': 'latin1', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'utf-8', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'cp1252', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'latin1', 'sep': ',', 'on_bad_lines': 'skip'},
        ]

        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"Tentativa {i+1}: {strategy}")

                df = pd.read_csv(
                    filepath,
                    low_memory=False,
                    **strategy
                )

                logger.info(f"Sucesso! {len(df)} registros, {len(df.columns)} colunas")
                return df

            except Exception as e:
                logger.warning(f"Estratégia {i+1} falhou: {str(e)}")
                continue

        logger.error(f"Todas as estratégias falharam para {filepath.name}")
        return None

    def transform_data(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Transformar e limpar dados"""
        logger.info(f"Transformando dados de {year}...")

        # Manter apenas colunas essenciais que existem
        available_columns = [col for col in self.ESSENTIAL_COLUMNS if col in df.columns]
        logger.info(f"Colunas disponíveis: {len(available_columns)}/{len(self.ESSENTIAL_COLUMNS)}")

        df_clean = df[available_columns].copy()

        # Converter datas
        date_columns = ['DT_NOTIFIC', 'DT_SIN_PRI', 'DT_INTERNA', 'DT_EVOLUCA']
        for col in date_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

        # Adicionar colunas derivadas
        df_clean['year'] = year

        if 'DT_NOTIFIC' in df_clean.columns:
            df_clean['mes_notific'] = df_clean['DT_NOTIFIC'].dt.month
            df_clean['ano_notific'] = df_clean['DT_NOTIFIC'].dt.year
            df_clean['semana_epidemio'] = df_clean['DT_NOTIFIC'].dt.isocalendar().week

        # Faixa etária
        if 'NU_IDADE_N' in df_clean.columns:
            df_clean['faixa_etaria'] = pd.cut(
                df_clean['NU_IDADE_N'],
                bins=[0, 2, 12, 18, 30, 50, 65, 100],
                labels=['0-2', '3-12', '13-18', '19-30', '31-50', '51-65', '65+'],
                right=False
            ).astype(str)

        # Descrições dos códigos
        df_clean['cs_sexo_desc'] = df_clean.get('CS_SEXO', pd.Series()).map({
            1: 'Masculino', 2: 'Feminino', 9: 'Ignorado'
        })

        df_clean['evolucao_desc'] = df_clean.get('EVOLUCAO', pd.Series()).map({
            1: 'Cura', 2: 'Óbito', 3: 'Óbito por outras causas', 9: 'Ignorado'
        })

        df_clean['uti_desc'] = df_clean.get('UTI', pd.Series()).map({
            1: 'Sim', 2: 'Não', 9: 'Ignorado'
        })

        df_clean['vacina_desc'] = df_clean.get('VACINA', pd.Series()).map({
            1: 'Sim', 2: 'Não', 9: 'Ignorado'
        })

        # Regiões do Brasil
        regioes = {
            'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
            'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste',
            'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
            'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'DF': 'Centro-Oeste',
            'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
            'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
        }

        if 'SG_UF' in df_clean.columns:
            df_clean['regiao'] = df_clean['SG_UF'].map(regioes)

        # Limpar dados inválidos
        df_clean = df_clean.dropna(subset=['DT_NOTIFIC'] if 'DT_NOTIFIC' in df_clean.columns else [])

        # Converter colunas numéricas
        numeric_columns = ['CS_SEXO', 'NU_IDADE_N', 'EVOLUCAO', 'UTI', 'VACINA', 'CLASSI_FIN'] + \
            [col for col in df_clean.columns if col in self.ESSENTIAL_COLUMNS[13:]]  # Sintomas e comorbidades

        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        logger.info(f"Dados transformados: {len(df_clean)} registros finais")
        return df_clean

    def calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """Calcular score de qualidade dos dados"""
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        quality_score = 1 - (null_cells / total_cells)
        return round(quality_score, 3)

    def load_data(self, df: pd.DataFrame, year: int, url: str, filepath: Path, processing_time: float):
        """Carregar dados no banco SQLite"""
        logger.info(f"Carregando dados de {year} no banco...")

        start_time = time.time()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remover dados anteriores do mesmo ano
                conn.execute("DELETE FROM srag_data WHERE year = ?", (year,))

                # Inserir novos dados
                df.to_sql('srag_data', conn, if_exists='append', index=False)

                # Calcular métricas
                file_hash = self._calculate_file_hash(filepath)
                data_quality_score = self.calculate_data_quality_score(df)

                # Atualizar metadados
                conn.execute("""
                    INSERT OR REPLACE INTO etl_metadata
                    (year, url, download_date, file_hash, total_records, processed_records,
                     data_quality_score, processing_time_seconds, status, error_log)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SUCCESS', NULL)
                """, (
                    year, url, datetime.now(), file_hash,
                    len(df), len(df), data_quality_score, processing_time,
                ))

                conn.commit()

            load_time = time.time() - start_time
            logger.info(f" Dados carregados em {load_time:.2f}s")
            logger.info(f" Qualidade dos dados: {data_quality_score:.1%}")

        except Exception as e:
            logger.error(f" Erro ao carregar dados: {str(e)}")

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO etl_metadata
                    (year, url, download_date, file_hash, total_records, processed_records,
                     data_quality_score, processing_time_seconds, status, error_log)
                    VALUES (?, ?, ?, ?, 0, 0, 0, ?, 'ERROR', ?)
                """, (year, url, datetime.now(), "", processing_time, str(e)))
                conn.commit()

            raise e

    def process_year(self, year: int) -> bool:
        """Processar dados de um ano específico"""
        logger.info(f" Iniciando processamento para {year}")
        start_time = time.time()

        try:
            # 1. Download
            filepath = self.download_data(year)
            if not filepath:
                return False

            # 2. Extract
            df = self.extract_data(filepath)
            if df is None:
                return False

            # 3. Transform
            df_clean = self.transform_data(df, year)

            # 4. Load
            processing_time = time.time() - start_time
            self.load_data(df_clean, year, self.DATASUS_URLS[year], filepath, processing_time)

            # 5. Cleanup
            filepath.unlink()  # Deletar arquivo temporário

            total_time = time.time() - start_time
            logger.info(f" Processamento de {year} concluído em {total_time:.2f}s")
            return True

        except Exception as e:
            logger.error(f" Erro no processamento de {year}: {str(e)}")
            return False

    def get_database_stats(self) -> Dict:
        """Obter estatísticas do banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            # Estatísticas gerais
            stats = {}

            # Total de registros por ano
            years_data = conn.execute("""
                SELECT year, COUNT(*) as records, MIN(dt_notific) as min_date, MAX(dt_notific) as max_date
                FROM srag_data
                GROUP BY year
                ORDER BY year
            """).fetchall()

            stats['years'] = {
                year: {
                    'records': records,
                    'min_date': min_date,
                    'max_date': max_date
                }
                for year, records, min_date, max_date in years_data
            }

            # Total geral
            total_records = conn.execute("SELECT COUNT(*) FROM srag_data").fetchone()[0]
            stats['total_records'] = total_records

            # Qualidade dos dados
            quality_data = conn.execute("""
                SELECT year, data_quality_score, status
                FROM etl_metadata
                ORDER BY year
            """).fetchall()

            stats['data_quality'] = {
                year: {'score': score, 'status': status}
                for year, score, status in quality_data
            }

            # Tamanho do banco
            db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
            stats['database_size_mb'] = round(db_size, 2)

            return stats


def main():
    """Função principal do script"""
    parser = argparse.ArgumentParser(description="ETL Pipeline para dados DATASUS")
    parser.add_argument("--year", type=int, help="Ano específico para processar")
    parser.add_argument("--all-years", action="store_true", help="Processar todos os anos disponíveis")
    parser.add_argument("--update-all", action="store_true", help="Atualizar todos os anos")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas do banco")
    parser.add_argument("--db-path", default="data/datasus.db", help="Caminho do banco SQLite")

    args = parser.parse_args()

    # Inicializar ETL
    etl = DataSUSETL(db_path=args.db_path)

    if args.stats:
        # Mostrar estatísticas
        stats = etl.get_database_stats()
        print("\n ESTATÍSTICAS DO BANCO DATASUS")
        print("=" * 50)
        print(f" Tamanho do banco: {stats['database_size_mb']} MB")
        print(f" Total de registros: {stats['total_records']:,}")
        print("\n Dados por ano:")

        for year, data in stats['years'].items():
            quality = stats['data_quality'].get(year, {})
            status = quality.get('status', 'N/A')
            score = quality.get('score', 0)
            print(f"  {year}: {data['records']:,} registros | Qualidade: {score:.1%} | Status: {status}")

        return

    if args.year:
        # Processar ano específico
        success = etl.process_year(args.year)
        if success:
            print(f" Processamento de {args.year} concluído com sucesso!")
        else:
            print(f" Falha no processamento de {args.year}")
            sys.exit(1)

    elif args.all_years or args.update_all:
        # Processar todos os anos
        years = list(etl.DATASUS_URLS.keys())
        successful = 0
        failed = 0

        for year in years:
            print(f"\n{'='*50}")
            success = etl.process_year(year)
            if success:
                successful += 1
            else:
                failed += 1

        print("\n RESUMO FINAL:")
        print(f" Sucessos: {successful}")
        print(f" Falhas: {failed}")
        print(f" Total: {successful + failed}")

        if failed > 0:
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
