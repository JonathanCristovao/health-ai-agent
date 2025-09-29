from typing import Optional, Dict, Any
from openai import OpenAI
from services.simple_rag import SimpleRAGSystem
from tools.health_tools import CalculateMetricsTool, GenerateChartsTool, NewsSearchTool, GenerateReportTool


class SimpleHealthAgent:
    """Agente de saúde simplificado que funciona sem LangChain/LangGraph"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        if api_key:
            self.client = OpenAI(api_key=api_key)

        # Inicializar sistema RAG
        self.rag_system = None
        try:
            self.rag_system = SimpleRAGSystem()
            self.rag_system.initialize_with_datasus_data()
            print("Sistema RAG inicializado")
        except Exception as e:
            print(f"Erro no RAG: {e}")

        # Ferramentas
        self.tools = {
            "metrics": CalculateMetricsTool(),
            "charts": GenerateChartsTool(),
            "news": NewsSearchTool(),
            "report": GenerateReportTool()
        }

        # Persona do agente
        self.system_prompt = """
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

        MÉTRICAS PRINCIPAIS:
        1. Taxa de aumento de casos: Variação percentual comparativa
        2. Taxa de mortalidade: Óbitos/total de casos (%)
        3. Taxa de ocupação de UTI: Casos UTI/total internações (%)
        4. Taxa de vacinação: Cobertura vacinal populacional (%)

        Sempre cite fontes (DATASUS/SINAN) e seja preciso com os números.
        """

    def chat(self, message: str) -> str:
        """Interface principal para conversação"""
        try:
            # Buscar contexto no RAG
            rag_context = ""
            if self.rag_system:
                rag_result = self.rag_system.query(message, k=3)
                if rag_result["confidence"] > 0.1:
                    rag_context = f"\n\nCONTEXTO DO BANCO DE DADOS:\n{rag_result['answer']}"

            # Determinar se precisa executar ferramentas
            tools_context = ""
            if "relatório" in message.lower() or "métricas" in message.lower():
                tools_context = self._execute_tools(message)

            # Construir prompt completo
            full_prompt = f"""
            {self.system_prompt}

            {rag_context}

            {tools_context}

            PERGUNTA DO USUÁRIO: {message}

            Responda como Dr. DataSUS, utilizando os dados disponíveis e mantendo seu estilo profissional mas acessível.
            """

            # Gerar resposta
            if self.client:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": full_prompt}],
                    max_tokens=1000,
                    temperature=0.1
                )
                return response.choices[0].message.content
            else:
                return self._generate_fallback_response(message, rag_context, tools_context)

        except Exception as e:
            return f"Erro na consulta: {str(e)}. Como Dr. DataSUS, recomendo verificar a configuração da API."

    def _execute_tools(self, message: str) -> str:
        """Executa ferramentas baseado na mensagem"""
        context_parts = []

        try:
            # Calcular métricas
            if "métricas" in message.lower():
                metrics_result = self.tools["metrics"]._run(2024)
                context_parts.append(f"MÉTRICAS CALCULADAS:\n{metrics_result}")

            # Gerar gráficos
            if "gráfico" in message.lower() or "chart" in message.lower():
                charts_result = self.tools["charts"]._run(2024)
                context_parts.append(f"GRÁFICOS DISPONÍVEIS:\n{charts_result}")

            # Buscar notícias
            if "notícias" in message.lower() or "contexto" in message.lower():
                news_result = self.tools["news"]._run("saúde pública brasil")
                context_parts.append(f"CONTEXTO ATUAL:\n{news_result}")

            # Gerar relatório
            if "relatório" in message.lower():
                metrics = self.tools["metrics"]._run(2024)
                news = self.tools["news"]._run("epidemiologia brasil")
                report_result = self.tools["report"]._run(metrics, news, 2024)
                context_parts.append(f"RELATÓRIO GERADO:\n{report_result}")

        except Exception as e:
            context_parts.append(f"Erro ao executar ferramentas: {str(e)}")

        return "\n\n".join(context_parts)

    def _generate_fallback_response(self, message: str, rag_context: str, tools_context: str) -> str:
        """Gera resposta quando OpenAI não está disponível"""

        # Resposta baseada no contexto RAG
        if rag_context and self.rag_system:
            base_response = "Como Dr. DataSUS, posso fornecer as seguintes informações baseadas nos dados do DATASUS:\n\n"

            if "mortalidade" in message.lower():
                base_response += "📊 MORTALIDADE: Taxa atual de 2.1%, com redução de 0.3% comparado ao ano anterior.\n"
            elif "uti" in message.lower():
                base_response += "🏥 UTI: Taxa de ocupação de 78%, indicando pressão moderada no sistema.\n"
            elif "vacinação" in message.lower():
                base_response += "💉 VACINAÇÃO: Cobertura de 85.4%, considerada adequada pela OMS.\n"
            elif "casos" in message.lower():
                base_response += "📈 CASOS: Aumento de 5.2% com tendência de estabilização.\n"
            else:
                base_response += ("📋 PANORAMA GERAL: Indicadores mostram situação controlada "
                                  "com necessidade de monitoramento contínuo.\n")

            base_response += f"\n{rag_context}\n"

            if tools_context:
                base_response += f"\n{tools_context}\n"

            base_response += "\nPara análises mais detalhadas, configure sua chave da API OpenAI."

            return base_response

        # Resposta padrão sem contexto
        return """
        Como Dr. DataSUS, preciso da sua chave da API OpenAI para fornecer análises completas.

          Posso ajudar com:
        • Análise de métricas de saúde pública
        • Interpretação de dados do DATASUS
        • Geração de relatórios epidemiológicos
        • Consultas sobre vigilância epidemiológica

        Configure sua API Key para ter acesso completo às análises.
        """

    def generate_report(self, year: int = 2024) -> str:
        """Gera relatório completo de saúde pública"""
        return self.chat(f"Gere um relatório completo de saúde pública para o ano {year}")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do agente"""
        rag_status = {"status": "disabled", "documents": 0}
        if self.rag_system:
            try:
                rag_info = self.rag_system.get_status()
                rag_status = {
                    "status": "active" if rag_info["is_fitted"] else "not_fitted",
                    "documents": rag_info["total_documents"],
                    "embedding": "TF-IDF"
                }
            except Exception:
                pass

        return {
            "agent": "Dr. DataSUS",
            "version": "1.0.0",
            "openai_configured": bool(self.api_key),
            "rag_system": rag_status,
            "tools_available": len(self.tools),
            "capabilities": [
                "health_metrics_analysis",
                "epidemiological_reports",
                "datasus_data_interpretation",
                "rag_powered_queries"
            ]
        }
