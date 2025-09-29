from fastapi import APIRouter
from controllers.app_controller import AppController

# Criar router
app_router = APIRouter(tags=["app"])

# Instanciar controller
app_controller = AppController()


@app_router.get("/")
def home_endpoint():
    """Endpoint da página inicial"""
    return app_controller.get_home_status()


@app_router.get("/api/")
def api_home_endpoint():
    """Endpoint da home da API"""
    return app_controller.get_api_home_status()
