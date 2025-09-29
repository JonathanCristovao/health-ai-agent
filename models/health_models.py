from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime


@dataclass
class HealthMetrics:
    """Modelo de dados para métricas de saúde"""
    casos_notificados: int
    obitos: int
    internacoes_uti: int
    vacinados: int
    taxa_aumento_casos: float
    taxa_mortalidade: float
    taxa_ocupacao_uti: float
    taxa_vacinacao: float


@dataclass
class EpidemiologicalData:
    """Modelo para dados epidemiológicos"""
    date: datetime
    region: str
    cases: int
    deaths: int
    recoveries: int
    active_cases: int


@dataclass
class HealthAnalysis:
    """Modelo para análise de saúde"""
    trend: str
    pressure_level: str
    vaccination_coverage: str
    recommendations: List[str]


@dataclass
class ChatContext:
    """Modelo para contexto de chat"""
    user_message: str
    persona_context: str
    document_context: str
    history: List[Dict[str, str]]


class HealthDataRepository:
    """Repository pattern para dados de saúde"""

    @staticmethod
    def get_metrics_by_year(year: int) -> HealthMetrics:
        """Obtém métricas por ano - simulação"""
        return HealthMetrics(
            casos_notificados=125000,
            obitos=2625,
            internacoes_uti=97500,
            vacinados=106250,
            taxa_aumento_casos=5.2,
            taxa_mortalidade=2.1,
            taxa_ocupacao_uti=78.0,
            taxa_vacinacao=85.4
        )

    @staticmethod
    def get_analysis_data(year: int) -> HealthAnalysis:
        """Obtém dados de análise por ano"""
        return HealthAnalysis(
            trend="Estabilização com leve melhoria",
            pressure_level="Moderada",
            vaccination_coverage="Adequada",
            recommendations=[
                "Manter vigilância epidemiológica ativa",
                "Otimizar recursos de UTI",
                "Continuar campanhas de vacinação"
            ]
        )


class AgentRepository:
    """Repository para agentes de IA"""

    def __init__(self):
        self.dr_datasus_persona = """
        Você é o Dr. DataSUS, um especialista em vigilância epidemiológica com 15 anos de experiência.

        CARACTERÍSTICAS:
        - Formação em Medicina com especialização em Epidemiologia
        - Expertise em análise de dados populacionais do DATASUS
        - Linguagem técnica mas acessível ao público
        - Foco em evidências científicas e dados confiáveis
        - Capacidade de interpretar métricas de saúde pública

        RESPONSABILIDADES:
        - Analisar dados do Sistema de Informação de Agravos de Notificação (SINAN)
        - Calcular e interpretar métricas epidemiológicas
        - Gerar relatórios de saúde pública
        - Responder perguntas sobre epidemiologia e vigilância
        - Fornecer recomendações baseadas em evidências
        """

    def get_persona_context(self) -> str:
        """Obtém contexto da persona do agente"""
        return self.dr_datasus_persona
