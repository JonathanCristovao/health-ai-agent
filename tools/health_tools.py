from langchain.tools import BaseTool
import warnings
import logging

# Importar cliente do banco DATASUS
from database.datasus_client import get_datasus_db, check_database, get_vaccination_answer

# Suprimir warnings específicos do pandas
warnings.filterwarnings('ignore', message=".*'M' is deprecated.*")
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger(__name__)

# Classe legada removida - agora usa banco SQLite local via datasus_client


class CalculateMetricsTool(BaseTool):
    name: str = "calculate_health_metrics"
    description: str = "Calcula métricas de saúde baseadas nos dados do DATASUS (banco SQLite local)"

    def _run(self, year: int = 2024) -> str:
        try:
            # Verificar se banco está disponível
            if not check_database():
                return "Banco DATASUS não disponível. Execute: python scripts/datasus_etl.py --all-years"

            # Obter instância do banco
            db = get_datasus_db()

            # Verificar dados do ano específico
            availability = db.check_data_availability(year)
            if not availability['available']:
                return f"Dados de {year} não disponíveis. Execute: python scripts/datasus_etl.py --year {year}"

            logger.info(f"Calculando métricas para {year} (banco local)")

            # Obter indicadores clínicos
            indicators = db.get_clinical_indicators(year)

            if not indicators:
                return f"Não foi possível calcular indicadores para {year}"

            # Obter tendências temporais para calcular crescimento
            temporal_data = db.get_temporal_trends(year, 'month')
            taxa_crescimento = "N/A"

            if len(temporal_data) > 1:
                primeiro_mes = temporal_data.iloc[0]['casos_notificados']
                ultimo_mes = temporal_data.iloc[-1]['casos_notificados']
                if primeiro_mes > 0:
                    crescimento = ((ultimo_mes - primeiro_mes) / primeiro_mes) * 100
                    taxa_crescimento = f"{crescimento:.2f}%"

            # Montar resposta
            metrics = {
                'ano': year,
                'total_casos': f"{indicators['total_casos']:,}",
                'taxa_mortalidade': f"{indicators['taxa_mortalidade']:.2f}%",
                'taxa_ocupacao_uti': f"{indicators['taxa_uti']:.2f}%",
                'taxa_vacinacao': f"{indicators['taxa_vacinacao']:.2f}%",
                'taxa_crescimento_anual': taxa_crescimento,
                'qualidade_dados': f"{availability['quality_score']:.1%}",
                'fonte': "Banco DATASUS local",
                'registros_analisados': f"{availability['records']:,}"
            }

            logger.info(f"Métricas calculadas com sucesso para {year}")
            return str(metrics)

        except Exception as e:
            logger.error(f"Erro ao calcular métricas: {str(e)}")
            return f"Erro ao calcular métricas: {str(e)}"

    async def _arun(self, year: int = 2024) -> str:
        return self._run(year)


class GenerateChartsTool(BaseTool):
    name: str = "generate_health_charts"
    description: str = "Gera análises e gráficos baseados nos dados do DATASUS (banco SQLite local)"

    def _run(self, year: int = 2024) -> str:
        try:
            # Verificar se banco está disponível
            if not check_database():
                return "Banco DATASUS não disponível. Execute: python scripts/datasus_etl.py --all-years"

            # Obter instância do banco
            db = get_datasus_db()

            # Verificar dados do ano específico
            availability = db.check_data_availability(year)
            if not availability['available']:
                return f"Dados de {year} não disponíveis. Execute: python scripts/datasus_etl.py --year {year}"

            logger.info(f"Gerando análises para {year} (banco local)")

            charts_info = []

            # Análise temporal
            temporal_data = db.get_temporal_trends(year, 'month')
            if len(temporal_data) > 0:
                charts_info.append(f"Tendências mensais ({len(temporal_data)} meses)")

            # Análise demográfica
            demo_data = db.get_demographic_analysis(year)
            for analysis_type, df in demo_data.items():
                if len(df) > 0:
                    charts_info.append(f"Demografia {analysis_type.replace('_', ' ')} ({len(df)} categorias)")

            # Análise de vacinação
            vaccination_data = db.get_vaccination_data(year, by_state=True)
            if len(vaccination_data) > 0:
                charts_info.append(f"Vacinação por estado ({len(vaccination_data)} registros)")

            # Análise de mortalidade
            mortality_data = db.get_mortality_data(year, by_state=True)
            if len(mortality_data) > 0:
                charts_info.append(f"Mortalidade por estado ({len(mortality_data)} estados)")

            # Indicadores clínicos gerais
            clinical_indicators = db.get_clinical_indicators(year)
            if clinical_indicators:
                charts_info.append("Indicadores clínicos gerais")

            # Período dos dados
            data_sample = db.get_data(year=year, limit=1)
            if len(data_sample) > 0:
                period = "Dados completos do ano"
            else:
                period = "N/A"

            result = f"ANÁLISE COMPLETA DATASUS - {year}\n"
            result += f"Fonte: Banco SQLite local ({availability['records']:,} registros)\n"
            result += "Análises geradas:\n"

            for i, chart in enumerate(charts_info, 1):
                result += f"  {i}. {chart}\n"

            result += f"\n� Período: {period}"
            result += f"\nQualidade dos dados: {availability['quality_score']:.1%}"
            result += f"\nTotal de análises: {len(charts_info)}"

            return result

        except Exception as e:
            logger.error(f"Erro ao gerar análises: {str(e)}")
            return f"Erro ao gerar análises: {str(e)}"

    async def _arun(self, year: int = 2024) -> str:
        return self._run(year)


class VaccinationAnalysisTool(BaseTool):
    name: str = "analyze_vaccination_data"
    description: str = "Análise específica de dados de vacinação por estado (banco SQLite local)"

    def _run(self, question: str, year: int = 2024) -> str:
        try:
            # Usar função específica do cliente
            return get_vaccination_answer(question, year)

        except Exception as e:
            logger.error(f"Erro na análise de vacinação: {str(e)}")
            return f"Erro na análise de vacinação: {str(e)}"

    async def _arun(self, question: str, year: int = 2024) -> str:
        return self._run(question, year)


class NewsSearchTool(BaseTool):
    name: str = "search_health_news"
    description: str = "Busca notícias recentes sobre saúde pública e epidemiologia"

    def _run(self, query: str = "saúde pública epidemiologia brasil") -> str:
        try:
            # Simulação de busca de notícias
            news_data = {
                "total_news": 5,
                "headlines": [
                    "Ministério da Saúde atualiza protocolo de vigilância epidemiológica",
                    "Nova variante de vírus respiratório detectada no país",
                    "Campanha de vacinação mostra resultados positivos",
                    "Ocupação de UTIs reduz em 10% no último mês",
                    "Pesquisa aponta melhoria nos indicadores de saúde"
                ],
                "summary": "Notícias recentes indicam melhorias nos indicadores de saúde pública"
            }

            return str(news_data)

        except Exception as e:
            return f"Erro ao buscar notícias: {str(e)}"

    async def _arun(self, query: str = "saúde pública epidemiologia brasil") -> str:
        return self._run(query)


class GenerateReportTool(BaseTool):
    name: str = "generate_health_report"
    description: str = "Gera relatório completo com métricas, análises e contexto"

    def _run(self, metrics: str, news_context: str, year: int = 2024) -> str:
        try:
            report = """
# RELATÓRIO DE SAÚDE PÚBLICA - {year}

## MÉTRICAS PRINCIPAIS
{metrics}

## ANÁLISE CONTEXTUAL
Baseado nos dados mais recentes do DATASUS e informações de fontes confiáveis:

{news_context}

## INTERPRETAÇÃO DAS MÉTRICAS

### Taxa de Aumento de Casos
A variação no número de casos indica a tendência epidemiológica atual.

### Taxa de Mortalidade
Indicador crucial que reflete a gravidade dos casos e a eficácia do tratamento.

### Taxa de Ocupação de UTI
Métrica importante para avaliação da pressão sobre o sistema de saúde.

### Taxa de Vacinação
Fundamental para compreender a cobertura vacinal da população.

## RECOMENDAÇÕES
- Monitoramento contínuo dos indicadores
- Fortalecimento das medidas preventivas
- Otimização dos recursos de saúde

---
Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """

            return report

        except Exception as e:
            return f"Erro ao gerar relatório: {str(e)}"

    async def _arun(self, metrics: str, news_context: str, year: int = 2024) -> str:
        return self._run(metrics, news_context, year)
