from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """Modelo para requisições de chat"""
    msg: str


class ChatResponse(BaseModel):
    """Modelo para respostas de chat"""
    response: str


class HealthReportRequest(BaseModel):
    """Modelo para requisições de relatório de saúde"""
    year: int = 2024
    report_type: str = "complete"
    api_key: Optional[str] = None


class HealthMetricsResponse(BaseModel):
    """Modelo para resposta de métricas de saúde"""
    metrics: dict
    year: int
    generated_at: str


class HealthChatRequest(BaseModel):
    """Modelo para requisições de chat específico de saúde"""
    message: str
    api_key: str
    context: Optional[dict] = None


class HealthReport(BaseModel):
    """Modelo para relatório de saúde completo"""
    title: str
    generated_at: str
    year: int
    type: str
    metrics: dict
    analysis: dict
    charts: dict


class ApiStatusResponse(BaseModel):
    """Modelo para resposta de status da API"""
    status: str
    service: str
    version: str
    data_sources: list
    features: list
