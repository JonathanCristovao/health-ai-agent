from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseService(ABC):
    """Classe base para todos os serviços"""

    @abstractmethod
    def __init__(self):
        pass


class AIService(BaseService):
    """Serviço base para IA"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Gera resposta baseada em prompt e contexto"""
        pass


class DataService(BaseService):
    """Serviço base para manipulação de dados"""

    @abstractmethod
    def fetch_data(self, source: str, parameters: dict) -> Any:
        """Busca dados de uma fonte específica"""
        pass

    @abstractmethod
    def process_data(self, raw_data: Any) -> Any:
        """Processa dados brutos"""
        pass
