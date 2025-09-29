import chromadb
import pandas as pd
from typing import List, Dict, Any
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from datetime import datetime


class HealthRAGSystem:
    """Sistema RAG para análise de dados de saúde pública"""

    def __init__(self, api_key: str, persist_directory: str = "./data/chroma_db"):
        self.api_key = api_key
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        self.llm = ChatOpenAI(
            model="gpt-4",
            openai_api_key=api_key,
            temperature=0.1
        )

        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Collections para diferentes tipos de dados
        self.datasus_collection = None
        self.health_docs_collection = None
        self.news_collection = None

        # Vector store do LangChain
        self.vectorstore = None

        self._initialize_collections()

    def _initialize_collections(self):
        """Inicializa as collections do ChromaDB"""
        try:
            # Collection para dados do DATASUS
            self.datasus_collection = self.client.get_or_create_collection(
                name="datasus_data",
                metadata={"description": "Dados processados do DATASUS"}
            )

            # Collection para documentos de saúde pública
            self.health_docs_collection = self.client.get_or_create_collection(
                name="health_documents",
                metadata={"description": "Documentos e diretrizes de saúde pública"}
            )

            # Collection para notícias e contexto atual
            self.news_collection = self.client.get_or_create_collection(
                name="health_news",
                metadata={"description": "Notícias e atualizações sobre saúde pública"}
            )

            # Inicializar LangChain Chroma
            self.vectorstore = Chroma(
                client=self.client,
                collection_name="datasus_data",
                embedding_function=self.embeddings
            )

        except Exception as e:
            print(f"Erro ao inicializar collections: {e}")

    def process_and_store_datasus_data(self, year: int, sample_size: int = 5000):
        """Processa e armazena dados do DATASUS no banco vetorial"""
        from tools.health_tools import DatasusFetcher

        try:
            print(f"Processando dados do DATASUS para {year}...")

            # Buscar dados
            df = DatasusFetcher.fetch_data(year, sample_size)
            df_clean = DatasusFetcher.clean_and_process_data(df)

            # Gerar estatísticas e insights dos dados
            stats = self._generate_data_statistics(df_clean, year)

            # Criar documentos para o vector store
            documents = []

            # Estatísticas gerais
            general_stats = f"""
            Dados DATASUS {year} - Estatísticas Gerais:
            - Total de registros: {len(df_clean)}
            - Período: {year}
            - Fonte: Sistema de Informação de Agravos de Notificação (SINAN)

            Distribuição por evolução:
            {stats['evolucao_distribution']}

            Estatísticas de UTI:
            {stats['uti_stats']}

            Estatísticas de vacinação:
            {stats['vacina_stats']}

            Tendências temporais:
            {stats['temporal_trends']}
            """

            documents.append(Document(
                page_content=general_stats,
                metadata={
                    "source": "DATASUS",
                    "year": year,
                    "type": "statistics",
                    "processed_at": datetime.now().isoformat()
                }
            ))

            # Análises mensais
            if 'DT_NOTIFIC' in df_clean.columns:
                monthly_analysis = self._generate_monthly_analysis(df_clean, year)
                for month, analysis in monthly_analysis.items():
                    documents.append(Document(
                        page_content=analysis,
                        metadata={
                            "source": "DATASUS",
                            "year": year,
                            "month": month,
                            "type": "monthly_analysis",
                            "processed_at": datetime.now().isoformat()
                        }
                    ))

            # Adicionar documentos ao vector store
            if documents:
                self.vectorstore.add_documents(documents)
                print(f"Armazenados {len(documents)} documentos do DATASUS {year}")

        except Exception as e:
            print(f"Erro ao processar dados do DATASUS: {e}")

    def _generate_data_statistics(self, df: pd.DataFrame, year: int) -> Dict[str, Any]:
        """Gera estatísticas dos dados para armazenamento vetorial"""
        stats = {}

        # Distribuição por evolução
        if 'EVOLUCAO' in df.columns:
            evolucao_counts = df['EVOLUCAO'].value_counts()
            stats['evolucao_distribution'] = evolucao_counts.to_dict()

        # Estatísticas de UTI
        if 'UTI' in df.columns:
            uti_stats = df['UTI'].value_counts()
            stats['uti_stats'] = uti_stats.to_dict()

        # Estatísticas de vacinação
        if 'VACINA' in df.columns:
            vacina_stats = df['VACINA'].value_counts()
            stats['vacina_stats'] = vacina_stats.to_dict()

        # Tendências temporais
        if 'DT_NOTIFIC' in df.columns:
            df['mes'] = pd.to_datetime(df['DT_NOTIFIC'], errors='coerce').dt.to_period('M')
            temporal_trends = df.groupby('mes').size().to_dict()
            stats['temporal_trends'] = {str(k): v for k, v in temporal_trends.items()}

        return stats

    def _generate_monthly_analysis(self, df: pd.DataFrame, year: int) -> Dict[str, str]:
        """Gera análises mensais detalhadas"""
        monthly_analysis = {}

        if 'DT_NOTIFIC' in df.columns:
            df['mes'] = pd.to_datetime(df['DT_NOTIFIC'], errors='coerce').dt.month

            for month in df['mes'].dropna().unique():
                month_data = df[df['mes'] == month]

                analysis = f"""
                Análise DATASUS - {year}/{int(month):02d}:

                Total de notificações: {len(month_data)}

                Evolução dos casos:
                - Cura: {len(month_data[month_data['EVOLUCAO'] == 1]) if 'EVOLUCAO' in month_data.columns else 'N/A'}
                - Óbito: {len(month_data[month_data['EVOLUCAO'] == 2]) if 'EVOLUCAO' in month_data.columns else 'N/A'}

                UTI:
                - Necessitaram UTI: {len(month_data[month_data['UTI'] == 1]) if 'UTI' in month_data.columns else 'N/A'}
                - Não necessitaram UTI: {len(month_data[month_data['UTI'] == 2]) if 'UTI' in month_data.columns else 'N/A'}

                Vacinação:
                - Vacinados: {len(month_data[month_data['VACINA'] == 1]) if 'VACINA' in month_data.columns else 'N/A'}
                - Não vacinados: {len(month_data[month_data['VACINA'] == 2]) if 'VACINA' in month_data.columns else 'N/A'}
                """

                monthly_analysis[f"{year}-{int(month):02d}"] = analysis

        return monthly_analysis

    def add_health_documents(self, documents: List[Dict[str, Any]]):
        """Adiciona documentos de saúde pública ao vector store"""
        try:
            doc_objects = []

            for doc in documents:
                doc_objects.append(Document(
                    page_content=doc['content'],
                    metadata=doc.get('metadata', {})
                ))

            self.vectorstore.add_documents(doc_objects)
            print(f"Adicionados {len(doc_objects)} documentos de saúde pública")

        except Exception as e:
            print(f"Erro ao adicionar documentos: {e}")

    def search_similar_context(self, query: str, k: int = 5) -> List[Document]:
        """Busca contexto similar no banco vetorial"""
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
            return []

    def create_rag_chain(self):
        """Cria chain RAG para perguntas e respostas"""
        try:
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )

            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )

            return qa_chain
        except Exception as e:
            print(f"Erro ao criar RAG chain: {e}")
            return None

    def query_rag_system(self, question: str) -> Dict[str, Any]:
        """Consulta o sistema RAG com uma pergunta"""
        try:
            qa_chain = self.create_rag_chain()
            if not qa_chain:
                return {"error": "Não foi possível criar a chain RAG"}

            result = qa_chain({"query": question})

            return {
                "answer": result["result"],
                "sources": [doc.metadata for doc in result["source_documents"]],
                "source_content": [doc.page_content[:200] + "..." for doc in result["source_documents"]]
            }

        except Exception as e:
            return {"error": f"Erro na consulta RAG: {str(e)}"}

    def initialize_with_sample_data(self):
        """Inicializa o sistema com dados de amostra"""
        try:
            # Processar dados do DATASUS para anos recentes
            for year in [2023, 2024]:
                self.process_and_store_datasus_data(year, sample_size=1000)

            # Adicionar documentos de referência sobre saúde pública
            health_docs = [
                {
                    "content": """
                    Vigilância Epidemiológica é um conjunto de ações que proporcionam
                    o conhecimento, a detecção ou prevenção de qualquer mudança nos
                    fatores determinantes e condicionantes de saúde individual ou coletiva.

                    Principais indicadores:
                    - Taxa de incidência: número de casos novos por população em risco
                    - Taxa de mortalidade: número de óbitos por população total
                    - Taxa de letalidade: percentual de óbitos entre os casos
                    - Coeficiente de prevalência: casos existentes por população
                    """,
                    "metadata": {
                        "source": "Manual de Vigilância Epidemiológica",
                        "type": "reference_document",
                        "topic": "vigilancia_epidemiologica"
                    }
                },
                {
                    "content": """
                    Sistema de Informação de Agravos de Notificação (SINAN):

                    O SINAN é alimentado, principalmente, pela notificação e investigação
                    de casos de doenças e agravos que constam da lista nacional de
                    doenças de notificação compulsória.

                    Principais campos:
                    - DT_NOTIFIC: Data da notificação
                    - EVOLUCAO: Evolução do caso (1=Cura, 2=Óbito, 3=Óbito por outras causas)
                    - UTI: Necessidade de UTI (1=Sim, 2=Não)
                    - VACINA: Situação vacinal (1=Sim, 2=Não)
                    """,
                    "metadata": {
                        "source": "Manual SINAN",
                        "type": "reference_document",
                        "topic": "sinan_datasus"
                    }
                }
            ]

            self.add_health_documents(health_docs)
            print("Sistema RAG inicializado com dados de amostra")

        except Exception as e:
            print(f"Erro ao inicializar dados de amostra: {e}")

    def get_database_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o banco vetorial"""
        try:
            datasus_count = self.datasus_collection.count() if self.datasus_collection else 0
            health_docs_count = self.health_docs_collection.count() if self.health_docs_collection else 0

            return {
                "datasus_documents": datasus_count,
                "health_documents": health_docs_count,
                "total_documents": datasus_count + health_docs_count,
                "collections": ["datasus_data", "health_documents", "health_news"],
                "embedding_model": "text-embedding-ada-002",
                "vector_db": "ChromaDB"
            }
        except Exception as e:
            return {"error": f"Erro ao obter informações do banco: {e}"}
