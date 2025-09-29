from openai import OpenAI
from typing import Optional
from config import settings
from utils.selecionar_documento import DocumentSelector
from services.base_service import AIService


class ChatService(AIService):
    """Serviço de chat que herda de AIService"""

    def __init__(self):
        super().__init__(settings.openai_api_key, settings.chat_model)
        self.client = OpenAI(api_key=self.api_key)
        self.doc_selector = DocumentSelector()

        # Persona específica para o Dr. DataSUS
        self.health_persona = """
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

    def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Implementação do método abstrato da classe pai"""
        return self.get_response(prompt)

    def get_response(self, prompt: str) -> str:
        """Obtém resposta do agente de chat"""
        doc_ctx = self.doc_selector.select(prompt) if hasattr(self, 'doc_selector') else ""

        messages = [
            {"role": "system", "content": self.health_persona},
            {"role": "system", "content": doc_ctx},
            {"role": "user", "content": prompt}
        ]

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
