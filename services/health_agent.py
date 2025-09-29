from typing import TypedDict, List, Annotated
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import operator
from tools.health_tools import CalculateMetricsTool, GenerateChartsTool, GenerateReportTool, NewsSearchTool

try:
    from services.simple_rag import SimpleRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    SimpleRAGSystem = None
    RAG_AVAILABLE = False
    print("Sistema RAG não disponível - funcionando sem RAG")


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next_action: str
    metrics_data: str
    news_context: str
    final_report: str
    rag_context: str
    similar_documents: List[str]


class HealthAnalysisAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=api_key,
            temperature=0.1
        ) if api_key else None

        # Inicializar sistema RAG simplificado
        self.rag_system = None
        if RAG_AVAILABLE:
            try:
                self.rag_system = SimpleRAGSystem()
                self.rag_system.initialize_with_datasus_data()
                print("✅ Sistema RAG simplificado inicializado com sucesso")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar RAG: {e}")

        # Ferramentas disponíveis
        self.tools = [
            CalculateMetricsTool(),
            GenerateChartsTool(),
            NewsSearchTool(),
            GenerateReportTool()
        ]

        self.tool_executor = ToolExecutor(self.tools) if self.tools else None

        # Prompt do sistema
        self.system_prompt = """
        Você é um especialista em análise de dados de saúde pública e epidemiologia.
        Sua função é analisar dados do DATASUS, buscar contexto relevante e gerar
        relatórios completos sobre a situação epidemiológica atual.

        PERSONA: Dr. DataSUS - Especialista em Vigilância Epidemiológica
        - Formação em Medicina com especialização em Epidemiologia
        - 15 anos de experiência em saúde pública
        - Expertise em análise de dados populacionais
        - Linguagem técnica mas acessível
        - Foco em evidências científicas

        Você deve:
        1. Calcular métricas de saúde baseadas nos dados
        2. Buscar contexto atual sobre saúde pública
        3. Gerar relatórios detalhados com interpretações
        4. Responder perguntas sobre epidemiologia e saúde pública

        Use as ferramentas disponíveis para coletar dados e gerar insights.
        """

        # Criar o grafo
        self.workflow = self.create_workflow()

    def create_workflow(self):
        """Cria o workflow do agente usando LangGraph"""
        workflow = StateGraph(AgentState)

        # Nós do grafo
        workflow.add_node("analyzer", self.analyze_request)
        workflow.add_node("metrics_calculator", self.calculate_metrics)
        workflow.add_node("rag_retriever", self.retrieve_rag_context)
        workflow.add_node("news_searcher", self.search_news)
        workflow.add_node("report_generator", self.generate_report)
        workflow.add_node("responder", self.respond_to_user)

        # Arestas do grafo
        workflow.set_entry_point("analyzer")
        workflow.add_edge("analyzer", "rag_retriever")
        workflow.add_edge("rag_retriever", "metrics_calculator")
        workflow.add_edge("metrics_calculator", "news_searcher")
        workflow.add_edge("news_searcher", "report_generator")
        workflow.add_edge("report_generator", "responder")
        workflow.add_edge("responder", END)

        return workflow.compile()

    def analyze_request(self, state: AgentState) -> AgentState:
        """Analisa a requisição inicial"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""

        # Determina próxima ação
        if "relatório" in last_message.lower() or "métricas" in last_message.lower():
            state["next_action"] = "generate_full_report"
        else:
            state["next_action"] = "answer_question"

        return state

    def retrieve_rag_context(self, state: AgentState) -> AgentState:
        """Busca contexto relevante no sistema RAG"""
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""

        if self.rag_system:
            try:
                # Consultar sistema RAG simplificado
                rag_result = self.rag_system.query(last_message, k=3)

                if rag_result["confidence"] > 0.1:
                    state["rag_context"] = rag_result["answer"]
                    state["similar_documents"] = [doc["metadata"] for doc in rag_result["sources"]]
                else:
                    state["rag_context"] = "Contexto RAG com baixa confiança"
                    state["similar_documents"] = []

            except Exception as e:
                state["rag_context"] = f"Erro no RAG: {str(e)}"
                state["similar_documents"] = []
        else:
            state["rag_context"] = "Sistema RAG não inicializado"
            state["similar_documents"] = []

        return state

    def calculate_metrics(self, state: AgentState) -> AgentState:
        """Calcula métricas de saúde"""
        try:
            metrics_tool = CalculateMetricsTool()
            metrics_result = metrics_tool._run(year=2024)
            state["metrics_data"] = metrics_result
        except Exception as e:
            state["metrics_data"] = f"Erro ao calcular métricas: {str(e)}"

        return state

    def search_news(self, state: AgentState) -> AgentState:
        """Busca contexto de notícias"""
        try:
            news_tool = NewsSearchTool()
            news_result = news_tool._run("saúde pública brasil epidemiologia")
            state["news_context"] = news_result
        except Exception as e:
            state["news_context"] = f"Erro ao buscar notícias: {str(e)}"

        return state

    def generate_report(self, state: AgentState) -> AgentState:
        """Gera relatório final"""
        try:
            report_tool = GenerateReportTool()
            report_result = report_tool._run(
                metrics=state["metrics_data"],
                news_context=state["news_context"],
                year=2024
            )
            state["final_report"] = report_result
        except Exception as e:
            state["final_report"] = f"Erro ao gerar relatório: {str(e)}"

        return state

    def respond_to_user(self, state: AgentState) -> AgentState:
        """Responde ao usuário"""
        messages = state["messages"]

        if state["next_action"] == "generate_full_report":
            response_content = state["final_report"]
        else:
            # Para perguntas gerais, use o LLM com contexto RAG
            rag_info = ""
            if state.get("rag_context"):
                rag_info = f"\nContexto do RAG (baseado em dados do DATASUS): {state['rag_context']}"

            similar_docs_info = ""
            if state.get("similar_documents"):
                similar_docs_info = f"\nDocumentos relacionados encontrados: {len(state['similar_documents'])} documentos"

            prompt = f"""
            {self.system_prompt}

            Contexto atual:
            Métricas: {state.get('metrics_data', 'Não disponível')}
            Notícias: {state.get('news_context', 'Não disponível')}
            {rag_info}
            {similar_docs_info}

            Pergunta do usuário: {messages[-1].content if messages else ''}

            Responda como Dr. DataSUS, usando evidências e dados quando possível.
            Priorize informações do contexto RAG quando disponível, pois são baseadas em dados reais do DATASUS.
            """

            if self.llm:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                response_content = response.content
            else:
                response_content = "Erro: LLM não inicializado. Configure a API Key da OpenAI."

        # Adicionar resposta às mensagens
        state["messages"].append(AIMessage(content=response_content))

        return state

    def chat(self, message: str) -> str:
        """Interface principal para chat"""
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "next_action": "",
            "metrics_data": "",
            "news_context": "",
            "final_report": "",
            "rag_context": "",
            "similar_documents": []
        }

        if self.workflow:
            result = self.workflow.invoke(initial_state)
            return result["messages"][-1].content
        else:
            return "Erro: Workflow não inicializado. Verifique a configuração do agente."

    def get_rag_status(self) -> dict:
        """Retorna status do sistema RAG"""
        if not self.rag_system:
            return {
                "status": "disabled",
                "message": "Sistema RAG não inicializado",
                "documents": 0
            }

        try:
            status_info = self.rag_system.get_status()
            return {
                "status": "active",
                "message": "Sistema RAG simplificado funcionando",
                "documents": status_info.get("total_documents", 0),
                "is_fitted": status_info.get("is_fitted", False),
                "embedding_model": "TF-IDF (scikit-learn)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Erro no RAG: {e}",
                "documents": 0
            }

    def generate_full_report(self, year: int = 2024) -> str:
        """Gera relatório completo"""
        message = f"Gere um relatório completo de saúde pública para o ano {year}"
        return self.chat(message)
