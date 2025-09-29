import json
import os
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimpleRAGSystem:
    """Sistema RAG simplificado usando TF-IDF para similaridade"""

    def __init__(self, data_dir: str = "./data/simple_rag"):
        self.data_dir = data_dir
        self.documents = []
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.doc_vectors = None
        self.is_fitted = False

        # Criar diretório se não existir
        os.makedirs(data_dir, exist_ok=True)

        # Tentar carregar dados existentes
        self._load_existing_data()

    def _load_existing_data(self):
        """Carrega dados existentes se disponível"""
        try:
            docs_file = os.path.join(self.data_dir, "documents.json")
            vectors_file = os.path.join(self.data_dir, "vectors.pkl")

            if os.path.exists(docs_file):
                with open(docs_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)

                if os.path.exists(vectors_file) and self.documents:
                    with open(vectors_file, 'rb') as f:
                        data = pickle.load(f)
                        self.vectorizer = data['vectorizer']
                        self.doc_vectors = data['vectors']
                        self.is_fitted = True

                    print(f"Carregados {len(self.documents)} documentos do cache")

        except Exception as e:
            print(f"Erro ao carregar dados existentes: {e}")

    def _save_data(self):
        """Salva documentos e vetores"""
        try:
            docs_file = os.path.join(self.data_dir, "documents.json")
            vectors_file = os.path.join(self.data_dir, "vectors.pkl")

            with open(docs_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)

            if self.doc_vectors is not None:
                with open(vectors_file, 'wb') as f:
                    pickle.dump({
                        'vectorizer': self.vectorizer,
                        'vectors': self.doc_vectors
                    }, f)

        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    def add_document(self, content: str, metadata: Dict[str, Any]):
        """Adiciona um documento ao sistema"""
        doc = {
            "id": len(self.documents),
            "content": content,
            "metadata": metadata,
            "added_at": datetime.now().isoformat()
        }

        self.documents.append(doc)
        self._refit_vectorizer()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Adiciona múltiplos documentos"""
        for doc in documents:
            self.add_document(doc["content"], doc.get("metadata", {}))

    def _refit_vectorizer(self):
        """Reajusta o vectorizador com todos os documentos"""
        if not self.documents:
            return

        try:
            # Extrair conteúdo dos documentos
            contents = [doc["content"] for doc in self.documents]

            # Treinar vectorizador e transformar documentos
            self.doc_vectors = self.vectorizer.fit_transform(contents)
            self.is_fitted = True

            # Salvar dados
            self._save_data()

        except Exception as e:
            print(f"Erro ao ajustar vectorizador: {e}")

    def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Busca documentos similares à query"""
        if not self.is_fitted or not self.documents:
            return []

        try:
            # Transformar query em vetor
            query_vector = self.vectorizer.transform([query])

            # Calcular similaridade
            similarities = cosine_similarity(query_vector, self.doc_vectors).flatten()

            # Obter top k documentos
            top_indices = similarities.argsort()[-k:][::-1]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Threshold mínimo
                    doc = self.documents[idx].copy()
                    doc["similarity"] = float(similarities[idx])
                    results.append(doc)

            return results

        except Exception as e:
            print(f"Erro na busca: {e}")
            return []

    def query(self, question: str, k: int = 3) -> Dict[str, Any]:
        """Consulta o sistema e gera resposta baseada nos documentos similares"""
        similar_docs = self.search_similar(question, k)

        if not similar_docs:
            return {
                "answer": "Não foram encontrados documentos relevantes para responder à pergunta.",
                "sources": [],
                "confidence": 0.0
            }

        # Combinar conteúdo dos documentos mais similares
        context_parts = []
        sources = []

        for doc in similar_docs[:3]:
            context_parts.append(doc["content"][:500])  # Limitar tamanho
            sources.append({
                "id": doc["id"],
                "metadata": doc["metadata"],
                "similarity": doc["similarity"]
            })

        context = "\n\n".join(context_parts)

        # Gerar resposta baseada no contexto
        answer = self._generate_contextual_answer(question, context)

        confidence = np.mean([doc["similarity"] for doc in similar_docs[:3]])

        return {
            "answer": answer,
            "context": context,
            "sources": sources,
            "confidence": float(confidence)
        }

    def _generate_contextual_answer(self, question: str, context: str) -> str:
        """Gera resposta baseada no contexto (versão simplificada)"""
        # Versão simplificada - em produção seria com LLM

        # Extrair informações chave baseado na pergunta
        question_lower = question.lower()

        if "mortalidade" in question_lower:
            return f"Baseado nos dados disponíveis sobre mortalidade:\n\n{context[:300]}..."
        elif "uti" in question_lower:
            return f"Informações sobre UTI encontradas nos dados:\n\n{context[:300]}..."
        elif "vacinação" in question_lower or "vacina" in question_lower:
            return f"Dados sobre vacinação:\n\n{context[:300]}..."
        elif "casos" in question_lower:
            return f"Informações sobre casos encontradas:\n\n{context[:300]}..."
        else:
            return f"Com base nos documentos encontrados:\n\n{context[:400]}..."

    def initialize_with_datasus_data(self):
        """Inicializa com dados simulados do DATASUS"""
        try:
            sample_documents = [
                {
                    "content": """
                    Dados DATASUS 2024 - Estatísticas Gerais:
                    - Total de registros: 125,430
                    - Taxa de mortalidade: 2.1%
                    - Casos que necessitaram UTI: 78%
                    - Taxa de vacinação: 85.4%

                    Evolução dos casos:
                    - Cura: 97,835 casos (78%)
                    - Óbito: 2,634 casos (2.1%)
                    - Outros: 24,961 casos (19.9%)

                    Distribuição temporal:
                    - Pico em junho/2024: 15,230 casos
                    - Redução em agosto/2024: 8,450 casos
                    - Tendência atual: estabilização
                    """,
                    "metadata": {
                        "source": "DATASUS",
                        "year": 2024,
                        "type": "statistics",
                        "topic": "geral"
                    }
                },
                {
                    "content": """
                    Análise de Mortalidade DATASUS 2024:

                    Taxa de mortalidade por faixa etária:
                    - 0-19 anos: 0.3%
                    - 20-59 anos: 1.2%
                    - 60+ anos: 4.8%

                    Principais causas de óbito:
                    - Insuficiência respiratória: 45%
                    - Complicações cardiovasculares: 23%
                    - Sepse: 18%
                    - Outras: 14%

                    Comparação com 2023:
                    - Redução de 0.3% na taxa geral
                    - Melhoria no atendimento de emergência
                    - Maior eficácia dos tratamentos
                    """,
                    "metadata": {
                        "source": "DATASUS",
                        "year": 2024,
                        "type": "analysis",
                        "topic": "mortalidade"
                    }
                },
                {
                    "content": """
                    Ocupação de UTI - Dados DATASUS 2024:

                    Taxa de ocupação por região:
                    - Sudeste: 82%
                    - Sul: 76%
                    - Nordeste: 79%
                    - Norte: 74%
                    - Centro-Oeste: 71%

                    Tempo médio de permanência:
                    - UTI Geral: 8.5 dias
                    - UTI COVID: 12.3 dias
                    - UTI Cardiológica: 6.8 dias

                    Recursos disponíveis:
                    - Total de leitos UTI: 54,230
                    - Leitos ocupados: 42,299
                    - Taxa de rotatividade: 1.2 pacientes/leito/semana
                    """,
                    "metadata": {
                        "source": "DATASUS",
                        "year": 2024,
                        "type": "analysis",
                        "topic": "uti"
                    }
                },
                {
                    "content": """
                    Cobertura Vacinal - DATASUS 2024:

                    Vacinação por região:
                    - Sul: 91.2%
                    - Sudeste: 88.7%
                    - Centro-Oeste: 85.1%
                    - Nordeste: 82.4%
                    - Norte: 78.9%

                    Esquema vacinal completo:
                    - 1ª dose: 95.3%
                    - 2ª dose: 89.1%
                    - Dose de reforço: 67.8%

                    Grupos prioritários:
                    - Profissionais de saúde: 98.5%
                    - Idosos 60+: 94.2%
                    - Comorbidades: 87.6%
                    - População geral: 85.4%
                    """,
                    "metadata": {
                        "source": "DATASUS",
                        "year": 2024,
                        "type": "analysis",
                        "topic": "vacinacao"
                    }
                },
                {
                    "content": """
                    Manual de Vigilância Epidemiológica - SINAN:

                    O Sistema de Informação de Agravos de Notificação (SINAN)
                    é alimentado principalmente pela notificação e investigação
                    de casos de doenças e agravos que constam da lista nacional
                    de doenças de notificação compulsória.

                    Principais campos do sistema:
                    - DT_NOTIFIC: Data da notificação do caso
                    - EVOLUCAO: Evolução do caso (1=Cura, 2=Óbito, 3=Óbito por outras causas)
                    - UTI: Necessidade de UTI (1=Sim, 2=Não, 9=Ignorado)
                    - VACINA: Situação vacinal (1=Sim, 2=Não, 9=Ignorado)

                    Indicadores epidemiológicos:
                    - Taxa de incidência: casos novos/população em risco
                    - Taxa de mortalidade: óbitos/população total
                    - Taxa de letalidade: óbitos/casos totais
                    """,
                    "metadata": {
                        "source": "Manual SINAN",
                        "type": "reference",
                        "topic": "sinan_manual"
                    }
                }
            ]

            self.add_documents(sample_documents)
            print(f"Sistema RAG inicializado com {len(sample_documents)} documentos")

        except Exception as e:
            print(f"Erro ao inicializar dados: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do sistema"""
        return {
            "total_documents": len(self.documents),
            "is_fitted": self.is_fitted,
            "vectorizer_features": self.vectorizer.max_features if self.is_fitted else 0,
            "data_directory": self.data_dir,
            "last_update": datetime.now().isoformat()
        }
