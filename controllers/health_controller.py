from fastapi import HTTPException
from datetime import datetime
from models.request_models import (
    HealthReportRequest, HealthChatRequest, ChatResponse,
    HealthMetricsResponse, HealthReport, ApiStatusResponse
)
from models.health_models import HealthDataRepository, AgentRepository
from services.chat_service import ChatService


class HealthController:
    """Controller para operações relacionadas à saúde"""

    def __init__(self):
        self.health_repository = HealthDataRepository()
        self.agent_repository = AgentRepository()
        self.chat_service = ChatService()

    def health_chat(self, request: HealthChatRequest) -> ChatResponse:
        """Processa chat específico do agente de saúde"""
        try:
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API key da OpenAI é obrigatória")

            # Simulação de resposta do Dr. DataSUS
            response_content = f"""Como Dr. DataSUS, especialista em vigilância epidemiológica, posso informar sobre: {request.message}
                                **Análise baseada nos dados mais recentes:**
                                - Tendência epidemiológica atual: Estável
                                - Indicadores principais: Em monitoramento
                                - Recomendações: Manter vigilância ativa
                                Para uma análise mais detalhada, posso gerar um relatório completo com métricas específicas."""

            return ChatResponse(response=response_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def generate_health_report(self, request: HealthReportRequest) -> dict:
        """Gera relatório de saúde pública"""
        try:
            metrics = self.health_repository.get_metrics_by_year(request.year)
            analysis = self.health_repository.get_analysis_data(request.year)

            report = HealthReport(
                title=f"Relatório de Saúde Pública - {request.year}",
                generated_at=datetime.now().isoformat(),
                year=request.year,
                type=request.report_type,
                metrics={
                    "taxa_aumento_casos": f"+{metrics.taxa_aumento_casos}%",
                    "taxa_mortalidade": f"{metrics.taxa_mortalidade}%",
                    "taxa_ocupacao_uti": f"{metrics.taxa_ocupacao_uti}%",
                    "taxa_vacinacao": f"{metrics.taxa_vacinacao}%"
                },
                analysis={
                    "trend": analysis.trend,
                    "pressure_level": analysis.pressure_level,
                    "vaccination_coverage": analysis.vaccination_coverage,
                    "recommendations": analysis.recommendations
                },
                charts={
                    "daily_cases": "Dados dos últimos 30 dias",
                    "monthly_cases": "Dados dos últimos 12 meses"
                }
            )

            return report.dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_health_metrics(self, year: int) -> HealthMetricsResponse:
        """Obtém métricas específicas de um ano"""
        try:
            metrics = self.health_repository.get_metrics_by_year(year)

            return HealthMetricsResponse(
                metrics={
                    "casos_notificados": metrics.casos_notificados,
                    "obitos": metrics.obitos,
                    "internacoes_uti": metrics.internacoes_uti,
                    "vacinados": metrics.vacinados,
                    "taxa_aumento_casos": metrics.taxa_aumento_casos,
                    "taxa_mortalidade": metrics.taxa_mortalidade,
                    "taxa_ocupacao_uti": metrics.taxa_ocupacao_uti,
                    "taxa_vacinacao": metrics.taxa_vacinacao
                },
                year=year,
                generated_at=datetime.now().isoformat()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_api_status(self) -> ApiStatusResponse:
        """Obtém status da API de saúde"""
        return ApiStatusResponse(
            status="operational",
            service="Dr. DataSUS Health Analysis",
            version="1.0.0",
            data_sources=["DATASUS", "OpenAI"],
            features=[
                "Health metrics calculation",
                "Epidemiological analysis",
                "Automated reporting",
                "AI-powered chat"
            ]
        )
