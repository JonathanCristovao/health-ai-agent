"""
🗄️ Módulo de Acesso aos Dados DATASUS SQLite
=============================================

Fornece interface simples e otimizada para acessar dados do DATASUS
armazenados em banco SQLite local.

Substitui downloads repetidos por consultas rápidas no banco.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataSUSDatabase:
    """Interface para acessar dados DATASUS no banco SQLite"""

    def __init__(self, db_path: str = "data/datasus.db"):
        """Inicializar conexão com banco DATASUS"""
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Banco DATASUS não encontrado: {db_path}\n"
                f"Execute: python scripts/datasus_etl.py --all-years"
            )

    def get_connection(self) -> sqlite3.Connection:
        """Obter conexão com banco"""
        return sqlite3.connect(self.db_path)

    def check_data_availability(self, year: int) -> Dict:
        """Verificar disponibilidade dos dados para um ano"""
        with self.get_connection() as conn:
            # Verificar se tem dados
            result = conn.execute(
                "SELECT COUNT(*) as records FROM srag_data WHERE year = ?",
                (year,)
            ).fetchone()

            records = result[0] if result else 0

            # Verificar metadados do ETL
            metadata = conn.execute(
                """SELECT status, data_quality_score, download_date, total_records
                   FROM etl_metadata WHERE year = ?""",
                (year,)
            ).fetchone()

            if metadata:
                status, quality_score, download_date, total_records = metadata
                return {
                    'available': records > 0,
                    'records': records,
                    'status': status,
                    'quality_score': quality_score,
                    'download_date': download_date,
                    'total_records': total_records
                }
            else:
                return {
                    'available': False,
                    'records': 0,
                    'status': 'NOT_PROCESSED',
                    'quality_score': 0,
                    'download_date': None,
                    'total_records': 0
                }

    def get_years_available(self) -> List[int]:
        """Obter lista de anos disponíveis"""
        with self.get_connection() as conn:
            result = conn.execute(
                "SELECT DISTINCT year FROM srag_data ORDER BY year"
            ).fetchall()
            return [row[0] for row in result]

    def get_data(self,
                 year: Optional[int] = None,
                 years: Optional[List[int]] = None,
                 states: Optional[List[str]] = None,
                 limit: Optional[int] = None,
                 columns: Optional[List[str]] = None,
                 filters: Optional[Dict] = None) -> pd.DataFrame:
        """
        Obter dados do DATASUS com filtros

        Args:
            year: Ano específico
            years: Lista de anos
            states: Lista de UFs (ex: ['SP', 'RJ'])
            limit: Limitar número de registros
            columns: Colunas específicas
            filters: Filtros adicionais (ex: {'evolucao': 2} para óbitos)

        Returns:
            DataFrame com dados filtrados
        """

        # Construir query
        query = "SELECT "

        if columns:
            query += ", ".join(columns)
        else:
            query += "*"

        query += " FROM srag_data WHERE 1=1"
        params = []

        # Filtrar por ano
        if year:
            query += " AND year = ?"
            params.append(year)
        elif years:
            placeholders = ", ".join(["?" for _ in years])
            query += f" AND year IN ({placeholders})"
            params.extend(years)

        # Filtrar por estados
        if states:
            placeholders = ", ".join(["?" for _ in states])
            query += f" AND sg_uf IN ({placeholders})"
            params.extend(states)

        # Filtros adicionais
        if filters:
            for column, value in filters.items():
                if isinstance(value, list):
                    placeholders = ", ".join(["?" for _ in value])
                    query += f" AND {column} IN ({placeholders})"
                    params.extend(value)
                else:
                    query += f" AND {column} = ?"
                    params.append(value)

        # Ordenar e limitar
        query += " ORDER BY dt_notific DESC"

        if limit:
            query += f" LIMIT {limit}"

        # Executar query
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

            # Converter datas
            date_columns = ['dt_notific', 'dt_sin_pri', 'dt_interna', 'dt_evoluca', 'created_at']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            logger.info(f"Dados obtidos: {len(df)} registros")
            return df

    def get_vaccination_data(self, year: int, by_state: bool = True) -> pd.DataFrame:
        """Obter dados específicos de vacinação"""

        base_query = """
            SELECT sg_uf, vacina, vacina_desc, COUNT(*) as casos,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
            FROM srag_data
            WHERE year = ? AND vacina IS NOT NULL
        """

        if by_state:
            base_query += " GROUP BY sg_uf, vacina, vacina_desc"
            base_query += " ORDER BY sg_uf, vacina"
        else:
            base_query += " GROUP BY vacina, vacina_desc"
            base_query += " ORDER BY vacina"

        with self.get_connection() as conn:
            return pd.read_sql_query(base_query, conn, params=[year])

    def get_mortality_data(self, year: int, by_state: bool = True) -> pd.DataFrame:
        """Obter dados de mortalidade"""

        base_query = """
            SELECT
                sg_uf,
                COUNT(*) as total_casos,
                SUM(CASE WHEN evolucao = 2 THEN 1 ELSE 0 END) as obitos,
                ROUND(SUM(CASE WHEN evolucao = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as taxa_mortalidade
            FROM srag_data
            WHERE year = ? AND evolucao IS NOT NULL
        """

        if by_state:
            base_query += " GROUP BY sg_uf ORDER BY taxa_mortalidade DESC"
        else:
            base_query = base_query.replace("sg_uf,", "").replace("GROUP BY sg_uf", "")

        with self.get_connection() as conn:
            return pd.read_sql_query(base_query, conn, params=[year])

    def get_temporal_trends(self, year: int, granularity: str = 'month') -> pd.DataFrame:
        """Obter tendências temporais"""

        if granularity == 'month':
            date_part = "strftime('%Y-%m', dt_notific)"
            date_label = 'mes_ano'
        elif granularity == 'week':
            date_part = "strftime('%Y-%W', dt_notific)"
            date_label = 'semana_ano'
        else:  # day
            date_part = "strftime('%Y-%m-%d', dt_notific)"
            date_label = 'data'

        query = f"""
                    SELECT
                        {date_part} as {date_label},
                        COUNT(*) as casos_notificados,
                        SUM(CASE WHEN evolucao = 2 THEN 1 ELSE 0 END) as obitos,
                        SUM(CASE WHEN uti = 1 THEN 1 ELSE 0 END) as uti_casos
                    FROM srag_data
                    WHERE year = ? AND dt_notific IS NOT NULL
                    GROUP BY {date_part}
                    ORDER BY {date_part} """

        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=[year])

    def get_demographic_analysis(self, year: int) -> Dict[str, pd.DataFrame]:
        """Análise demográfica completa"""

        results = {}

        # Por sexo
        with self.get_connection() as conn:
            results['por_sexo'] = pd.read_sql_query("""
                SELECT cs_sexo_desc, COUNT(*) as casos,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
                FROM srag_data
                WHERE year = ? AND cs_sexo_desc IS NOT NULL
                GROUP BY cs_sexo_desc
                """, conn, params=[year])

            # Por faixa etária
            results['por_idade'] = pd.read_sql_query("""
                SELECT faixa_etaria, COUNT(*) as casos,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
                FROM srag_data
                WHERE year = ? AND faixa_etaria IS NOT NULL AND faixa_etaria != 'nan'
                GROUP BY faixa_etaria
                ORDER BY
                    CASE faixa_etaria
                        WHEN '0-2' THEN 1
                        WHEN '3-12' THEN 2
                        WHEN '13-18' THEN 3
                        WHEN '19-30' THEN 4
                        WHEN '31-50' THEN 5
                        WHEN '51-65' THEN 6
                        WHEN '65+' THEN 7
                        ELSE 8
                    END
                """, conn, params=[year])

            # Por região
            results['por_regiao'] = pd.read_sql_query("""
                SELECT regiao, COUNT(*) as casos,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
                FROM srag_data
                WHERE year = ? AND regiao IS NOT NULL
                GROUP BY regiao
                ORDER BY casos DESC
            """, conn, params=[year])

        return results

    def get_clinical_indicators(self, year: int) -> Dict[str, any]:
        """Indicadores clínicos principais"""

        with self.get_connection() as conn:
            # Taxa de mortalidade geral
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_casos,
                    SUM(CASE WHEN evolucao = 2 THEN 1 ELSE 0 END) as obitos,
                    SUM(CASE WHEN uti = 1 THEN 1 ELSE 0 END) as uti_casos,
                    SUM(CASE WHEN vacina = 1 THEN 1 ELSE 0 END) as vacinados
                FROM srag_data
                WHERE year = ?
            """, (year,)).fetchone()

            if result:
                total_casos, obitos, uti_casos, vacinados = result

                return {
                    'total_casos': total_casos,
                    'obitos': obitos,
                    'uti_casos': uti_casos,
                    'vacinados': vacinados,
                    'taxa_mortalidade': round((obitos / total_casos) * 100, 2) if total_casos > 0 else 0,
                    'taxa_uti': round((uti_casos / total_casos) * 100, 2) if total_casos > 0 else 0,
                    'taxa_vacinacao': round((vacinados / total_casos) * 100, 2) if total_casos > 0 else 0
                }
            else:
                return {}

    def get_state_vaccination_ranking(self, year: int) -> pd.DataFrame:
        """Ranking de vacinação por estado"""

        query = """
            SELECT
                sg_uf,
                COUNT(*) as total_casos,
                SUM(CASE WHEN vacina = 1 THEN 1 ELSE 0 END) as vacinados,
                ROUND(SUM(CASE WHEN vacina = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as cobertura_vacinal
            FROM srag_data
            WHERE year = ? AND vacina IS NOT NULL AND sg_uf IS NOT NULL
            GROUP BY sg_uf
            HAVING COUNT(*) >= 10  -- Mínimo de casos para ser significativo
            ORDER BY cobertura_vacinal ASC
        """

        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=[year])

    def search_data(self, query_text: str, year: Optional[int] = None) -> pd.DataFrame:
        """Busca textual nos dados (para perguntas específicas)"""

        # Mapear termos de busca para filtros
        filters = {}

        if 'obito' in query_text.lower() or 'morte' in query_text.lower():
            filters['evolucao'] = 2

        if 'uti' in query_text.lower():
            filters['uti'] = 1

        if 'vacin' in query_text.lower():
            filters['vacina'] = 1

        # Estados específicos
        estados = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
                   'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
        state_filter = None

        for estado in estados:
            if estado.lower() in query_text.lower():
                state_filter = [estado]
                break

        return self.get_data(
            year=year,
            states=state_filter,
            filters=filters,
            limit=1000
        )

    def get_database_info(self) -> Dict:
        """Informações gerais do banco"""

        with self.get_connection() as conn:
            # Estatísticas gerais
            stats = conn.execute("""
                SELECT
                    COUNT(DISTINCT year) as anos_disponiveis,
                    COUNT(*) as total_registros,
                    MIN(year) as ano_min,
                    MAX(year) as ano_max,
                    MIN(dt_notific) as data_min,
                    MAX(dt_notific) as data_max
                FROM srag_data
            """).fetchone()

            # Tamanho do banco
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)

            # Status por ano
            anos_status = conn.execute("""
                SELECT year, status, data_quality_score, total_records
                FROM etl_metadata
                ORDER BY year
            """).fetchall()

            return {
                'anos_disponiveis': stats[0] if stats else 0,
                'total_registros': stats[1] if stats else 0,
                'periodo': f"{stats[2]} - {stats[3]}" if stats and stats[2] else "N/A",
                'data_range': f"{stats[4]} - {stats[5]}" if stats and stats[4] else "N/A",
                'tamanho_mb': round(db_size_mb, 2),
                'status_anos': {
                    year: {
                        'status': status,
                        'qualidade': score,
                        'registros': records
                    }
                    for year, status, score, records in anos_status
                }
            }


# Instância global (lazy loading)
_datasus_db = None


def get_datasus_db():
    """Obter instância do banco (lazy loading)"""
    global _datasus_db
    if _datasus_db is None:
        _datasus_db = DataSUSDatabase()
    return _datasus_db

# Funções de conveniência


def get_data_for_year(year: int, **kwargs) -> pd.DataFrame:
    """Função de conveniência para obter dados de um ano"""
    return get_datasus_db().get_data(year=year, **kwargs)


def check_database() -> bool:
    """Verificar se o banco está disponível e populado"""
    try:
        db_path = Path("data/datasus.db")
        if not db_path.exists():
            return False

        info = get_datasus_db().get_database_info()
        return info['total_registros'] > 0
    except BaseException:
        return False


def get_vaccination_answer(question: str, year: int = 2024) -> str:
    """Responder perguntas sobre vacinação usando o banco"""

    try:
        db = get_datasus_db()

        # Verificar se dados estão disponíveis
        availability = db.check_data_availability(year)
        if not availability['available']:
            return f"Dados de {year} não disponíveis. Execute o ETL primeiro."

        # Obter ranking de vacinação
        ranking = db.get_state_vaccination_ranking(year)

        if len(ranking) == 0:
            return f"Dados de vacinação não encontrados para {year}"

        # Resposta formatada
        menor_estado = ranking.iloc[0]
        maiores_estados = ranking.tail(3)

        response = f"""
ANÁLISE DE VACINAÇÃO - {year}
(Baseado em dados DATASUS locais)

MENOR COBERTURA VACINAL:
{menor_estado['sg_uf']}: {menor_estado['cobertura_vacinal']:.1f}%
({menor_estado['vacinados']:,} de {menor_estado['total_casos']:,} casos)

TOP 3 MAIORES COBERTURAS:
"""

        for _, row in maiores_estados[::-1].iterrows():
            response += f"• {row['sg_uf']}: {row['cobertura_vacinal']:.1f}%\n"

        # Média nacional
        media_nacional = ranking['cobertura_vacinal'].mean()
        response += f"\nMÉDIA NACIONAL: {media_nacional:.1f}%"
        response += f"\nTotal de estados analisados: {len(ranking)}"
        response += f"\nFonte: Banco DATASUS local ({availability['records']:,} registros)"

        return response.strip()

    except Exception as e:
        return f"Erro ao consultar dados: {str(e)}"
