"""
Configuração de rotas da aplicação seguindo arquitetura MVC

Structure:
- Models: Definem estrutura de dados (Pydantic models, dataclasses)
- Views: Definem endpoints/rotas da API (FastAPI routers)
- Controllers: Contém lógica de negócio e coordenam Models e Services
- Services: Implementam funcionalidades específicas (IA, dados, etc.)
"""

from fastapi import FastAPI
from views.app_views import app_router
from views.chat_views import chat_router
from views.health_views import health_router


def configure_routes(app: FastAPI) -> None:
    """Configura todas as rotas da aplicação"""

    app.include_router(app_router)
    app.include_router(chat_router)
    app.include_router(health_router)
