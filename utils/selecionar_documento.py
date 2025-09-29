from utils.helpers import load_text
import os


class DocumentSelector:
    def __init__(self):
        self.docs = {}
        self._load_health_documents()

    def _load_health_documents(self):
        """Carrega documentos de saúde se existirem"""
        try:
            # Tenta carregar documentos relacionados à saúde
            data_dir = "data"
            if os.path.exists(os.path.join(data_dir, "dados_datasus.txt")):
                self.docs["datasus"] = load_text(os.path.join(data_dir, "dados_datasus.txt"))
            if os.path.exists(os.path.join(data_dir, "protocolos_saude.txt")):
                self.docs["protocolos"] = load_text(os.path.join(data_dir, "protocolos_saude.txt"))
            if os.path.exists(os.path.join(data_dir, "epidemiologia.txt")):
                self.docs["epidemiologia"] = load_text(os.path.join(data_dir, "epidemiologia.txt"))
        except Exception:
            # Se não existir, usar contexto padrão
            self.docs["default"] = "Sistema de análise de dados de saúde pública baseado no DATASUS"

    def select(self, text: str) -> str:
        """Seleciona documento baseado no contexto da consulta"""
        if not self.docs:
            return "Sistema de análise de dados de saúde pública baseado no DATASUS"

        low = text.lower()
        if "datasus" in low or "sinan" in low:
            return self.docs.get("datasus", "")
        if "protocolo" in low or "tratamento" in low:
            return self.docs.get("protocolos", "")
        if "epidemiologia" in low or "vigilância" in low:
            return self.docs.get("epidemiologia", "")

        # Retorna o primeiro documento disponível ou contexto padrão
        return next(iter(self.docs.values())
                    ) if self.docs else "Sistema de análise de dados de saúde pública baseado no DATASUS"
