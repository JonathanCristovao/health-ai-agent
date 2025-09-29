"""
Agente de Saúde Simplificado - Versão sem dependências complexas
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage

# Importar sistema RAG simplificado
try:
    from services.simple_rag import SimpleRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    SimpleRAGSystem = None
    RAG_AVAILABLE = False
    print("Sistema RAG não disponível - funcionando sem RAG")


class SimpleHealthAgent:
    """Agente de Saúde Simplificado com sistema RAG"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.1
        ) if api_key else None

        # Inicializar sistema RAG simplificado
        self.rag_system = None
        if RAG_AVAILABLE and api_key:
            try:
                self.rag_system = SimpleRAGSystem()
                print("✅ Sistema RAG simplificado inicializado com sucesso")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar RAG: {e}")
                self.rag_system = None
        else:
            print("⚠️ Sistema RAG não disponível - API key ausente ou módulo não encontrado")

        # Template para respostas
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Você é um assistente especializado em análise de dados de saúde pública do Brasil.
            Use o contexto fornecido para responder perguntas sobre:
            - Dados do DATASUS
            - Indicadores de saúde pública
            - Vacinação e epidemiologia
            - Sistema Único de Saúde (SUS)

            Contexto relevante:
            {context}

            Seja preciso, informativo e cite dados quando disponível."""),
            ("human", "{question}")
        ])

    def query(self, question: str) -> Dict[str, Any]:
        """
        Processa uma pergunta usando RAG + LLM
        """
        result = {
            "question": question,
            "answer": "",
            "context_used": [],
            "rag_available": self.rag_system is not None,
            "llm_available": self.llm is not None
        }

        try:
            # Buscar contexto no RAG se disponível
            context = ""
            if self.rag_system:
                rag_result = self.rag_system.query(question, k=3)
                context = rag_result.get("context", "")
                result["context_used"] = rag_result.get("sources", [])

            # Gerar resposta com LLM se disponível
            if self.llm and context:
                messages = self.prompt_template.format_messages(
                    context=context,
                    question=question
                )
                response = self.llm.invoke(messages)
                result["answer"] = response.content

            elif self.llm:
                # Resposta sem contexto RAG
                simple_prompt = f"""Como assistente de saúde pública do Brasil, responda:

                Pergunta: {question}

                Forneça informações gerais sobre o tema relacionado ao sistema de saúde brasileiro."""

                response = self.llm.invoke([HumanMessage(content=simple_prompt)])
                result["answer"] = response.content

            elif context:
                # Apenas contexto RAG, sem LLM
                result["answer"] = f"Contexto encontrado nos dados: {context[:500]}..."

            else:
                result["answer"] = "Sistema não disponível. Verifique configurações da API e do RAG."

        except Exception as e:
            result["answer"] = f"Erro ao processar pergunta: {str(e)}"
            print(f"Erro no agente: {e}")

        return result

    def get_status(self) -> Dict[str, Any]:
        """Retorna status dos componentes do agente"""
        return {
            "rag_available": self.rag_system is not None,
            "llm_available": self.llm is not None,
            "rag_documents": len(self.rag_system.documents) if self.rag_system else 0,
            "model": "gpt-4o-mini" if self.llm else None
        }

    def analyze_health_data(self, query: str) -> Dict[str, Any]:
        """
        Análise especializada de dados de saúde
        """
        health_queries = [
            f"Dados epidemiológicos sobre: {query}",
            f"Indicadores de saúde relacionados a: {query}",
            f"Informações do DATASUS sobre: {query}"
        ]

        results = []
        for hq in health_queries:
            if self.rag_system:
                rag_results = self.rag_system.search_similar(hq, k=2)
                results.extend(rag_results)

        # Combinar resultados e gerar resposta
        if results and self.llm:
            context = "\n\n".join([doc.get("content", "")[:200] for doc in results[:3]])

            analysis_prompt = f"""Analise os seguintes dados de saúde pública do Brasil:
                                {context}
                                Pergunta específica: {query}
                                Forneça uma análise detalhada incluindo:
                                1. Principais indicadores encontrados
                                2. Tendências observadas
                                3. Implicações para a saúde pública
                                4. Recomendações baseadas nos dados"""

            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])

            return {
                "query": query,
                "analysis": response.content,
                "data_sources": len(results),
                "context_documents": results[:3]
            }

        return {
            "query": query,
            "analysis": "Análise não disponível - verifique configurações do sistema",
            "data_sources": 0,
            "context_documents": []
        }
