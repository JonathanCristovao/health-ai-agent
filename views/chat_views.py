from fastapi import APIRouter
from models.request_models import ChatRequest, ChatResponse
from controllers.chat_controller import ChatController

# Criar router
chat_router = APIRouter(prefix="/chat", tags=["chat"])

# Instanciar controller
chat_controller = ChatController()


@chat_router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Endpoint para chat geral"""
    return chat_controller.process_chat(request)
