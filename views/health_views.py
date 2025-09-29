from fastapi import APIRouter
from models.request_models import (
    HealthReportRequest, HealthChatRequest, ChatResponse,
    HealthMetricsResponse, ApiStatusResponse
)
from controllers.health_controller import HealthController

# Criar router
health_router = APIRouter(prefix="/health", tags=["health"])

# Instanciar controller
health_controller = HealthController()


@health_router.post("/chat", response_model=ChatResponse)
def health_chat_endpoint(request: HealthChatRequest):
    """Endpoint para chat com o agente de saúde"""
    return health_controller.health_chat(request)


@health_router.post("/report", response_model=dict)
def generate_health_report_endpoint(request: HealthReportRequest):
    """Endpoint para gerar relatório de saúde"""
    return health_controller.generate_health_report(request)


@health_router.get("/metrics/{year}", response_model=HealthMetricsResponse)
def get_health_metrics_endpoint(year: int):
    """Endpoint para obter métricas específicas de um ano"""
    return health_controller.get_health_metrics(year)


@health_router.get("/status", response_model=ApiStatusResponse)
def health_api_status_endpoint():
    """Status da API de saúde"""
    return health_controller.get_api_status()
