from fastapi import HTTPException
from models.request_models import ChatRequest, ChatResponse
from models.health_models import ChatContext, AgentRepository
from services.chat_service import ChatService


class ChatController:
    """Controller para operações de chat"""

    def __init__(self):
        self.chat_service = ChatService()
        self.agent_repository = AgentRepository()

    def process_chat(self, request: ChatRequest) -> ChatResponse:
        """Processa uma requisição de chat"""
        if not request.msg:
            raise HTTPException(status_code=400, detail='Campo msg obrigatório')

        try:
            # Criar contexto do chat
            _context = ChatContext(
                user_message=request.msg,
                persona_context=self.agent_repository.get_persona_context(),
                document_context="",
                history=[]
            )

            # Obter resposta do serviço
            answer = self.chat_service.get_response(request.msg)

            return ChatResponse(response=answer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
