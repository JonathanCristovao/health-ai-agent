class AppController:
    """Controller para operações gerais da aplicação"""

    def get_home_status(self) -> dict:
        """Retorna status da página inicial"""
        return {"message": "DataSUS Health Assistant API is running"}

    def get_api_home_status(self) -> dict:
        """Retorna status da API"""
        return {"message": "Dr. DataSUS Health Analysis API is running"}
