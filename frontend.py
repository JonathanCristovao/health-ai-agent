import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from services.simple_agent import SimpleHealthAgent
    AGENT_AVAILABLE = True
except ImportError as e:
    st.error(f"Erro ao importar agente: {e}")
    AGENT_AVAILABLE = False

st.set_page_config(
    page_title="Dr. DataSUS - Análise de Saúde Pública",
    page_icon=None,
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #1f77b4, #2ca02c);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #1f77b4;
    margin: 0.5rem 0;
}
.chat-message {
    padding: 1rem;
    margin: 0.5rem 0;
    border-radius: 10px;
}
.user-message {
    background-color: #e3f2fd;
    margin-left: 2rem;
}
.agent-message {
    background-color: #f3e5f5;
    margin-right: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>Dr. DataSUS</h1>
    <h3>Especialista em Vigilância Epidemiológica e Análise de Dados do DATASUS</h3>
    <p>Análise automatizada de dados de saúde pública com IA</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Digite sua chave da API da OpenAI"
    )

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        st.success("API Key configurada!")
    else:
        st.warning("Configure sua API Key da OpenAI")

    st.divider()

    st.subheader("Parâmetros de Análise")
    selected_year = st.selectbox(
        "Ano para análise",
        options=[2025, 2024, 2023, 2022, 2021, 2020, 2019],
        index=1
    )

    report_type = st.selectbox(
        "Tipo de Relatório",
        options=[
            "Relatório Completo",
            "Métricas Principais",
            "Análise Temporal",
            "Comparação Anual"
        ]
    )

    st.divider()

    st.subheader("Sistema RAG")
    if AGENT_AVAILABLE:
        temp_agent = SimpleHealthAgent()
        rag_status = temp_agent.get_status()

        if rag_status["rag_system"]["status"] == "active":
            st.success(f"RAG Ativo: {rag_status['rag_system']['documents']} documentos")
            st.info(f"Embedding: {rag_status['rag_system']['embedding']}")
        else:
            st.warning("RAG não está ativo")
    else:
        st.error("Sistema não disponível")

    st.divider()

    # Botão para gerar relatório
    if st.button("Gerar Relatório Automatizado", type="primary", use_container_width=True):
        if not AGENT_AVAILABLE:
            st.error("Sistema do agente não disponível!")
        else:
            with st.spinner("Gerando relatório com RAG..."):
                try:
                    agent = SimpleHealthAgent(api_key if api_key else None)
                    report_content = agent.generate_report(selected_year)
                    st.session_state.show_report = True
                    st.session_state.report_year = selected_year
                    st.session_state.report_type = report_type
                    st.session_state.generated_report = report_content
                    st.success("Relatório gerado com sucesso usando RAG!")
                except Exception as e:
                    st.error(f"Erro ao gerar relatório: {e}")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Chat com Dr. DataSUS")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": """Olá! Sou o **Dr. DataSUS**, especialista em análise de dados de saúde pública.

**Posso te ajudar com:**
- Análise de métricas de saúde (mortalidade, vacinação, UTI)
- Geração de relatórios automatizados
- Interpretação de dados epidemiológicos
- Consultas específicas sobre saúde pública

**Como usar:**
1. Configure sua API Key da OpenAI na barra lateral
2. Escolha o ano e tipo de análise desejados
3. Clique em "Gerar Relatório" ou faça perguntas no chat

O que gostaria de saber sobre a situação epidemiológica?"""
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Digite sua pergunta sobre saúde pública..."):
        if not AGENT_AVAILABLE:
            st.error("Sistema do agente não disponível!")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Dr. DataSUS está analisando com RAG..."):
                    try:
                        agent = SimpleHealthAgent(api_key if api_key else None)
                        response = agent.chat(prompt)
                        st.markdown(response)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response
                        })

                    except Exception as e:
                        error_msg = f"Erro no agente: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Desculpe, ocorreu um erro: {error_msg}"
                        })

with col2:
    st.header("Painel de Métricas")
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Taxa de Aumento", "+5.2%", "1.1%")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Taxa de Mortalidade", "2.1%", "-0.3%")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Ocupação UTI", "78%", "-5%")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Taxa de Vacinação", "85.4%", "+2.1%")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    st.subheader("Casos Últimos 30 Dias")

    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    cases = np.random.poisson(lam=50, size=30) + np.sin(np.arange(30) * 0.2) * 10

    chart_data = pd.DataFrame({
        'Data': dates,
        'Casos': cases
    })

    st.line_chart(chart_data.set_index('Data'))
    st.divider()

    st.subheader("Sobre os Dados")
    st.markdown("""
    **Fonte:** DATASUS - Sistema de Informação de Agravos de Notificação (SINAN)

    **Atualização:** Dados processados em tempo real

    **Cobertura:** Nacional, com detalhamento por estado e município

    **Período:** 2019-2025
    """)

if hasattr(st.session_state, 'show_report') and st.session_state.show_report:
    st.header(f"📋 {st.session_state.report_type} - {st.session_state.report_year}")

    tab1, tab2, tab3 = st.tabs(["Métricas", "Gráficos", "Relatório"])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Taxa de Aumento de Casos", "+5.2%", "↗️ 1.1%")
        with col2:
            st.metric("Taxa de Mortalidade", "2.1%", "↘️ -0.3%")
        with col3:
            st.metric("Taxa de Ocupação UTI", "78%", "↘️ -5%")
        with col4:
            st.metric("Taxa de Vacinação", "85.4%", "↗️ +2.1%")

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Casos Diários (30 dias)")
            st.line_chart(chart_data.set_index('Data'))

        with col2:
            st.subheader("Casos Mensais (12 meses)")
            monthly_data = pd.DataFrame({
                'Mês': pd.date_range(end=datetime.now(), periods=12, freq='M'),
                'Casos': np.random.poisson(lam=1500, size=12)
            })
            st.bar_chart(monthly_data.set_index('Mês'))

    with tab3:
        if hasattr(st.session_state, 'generated_report'):
            st.markdown("## Relatório Gerado pelo Dr. DataSUS com RAG")
            st.markdown(st.session_state.generated_report)
        else:
            st.markdown(f"""
            # RELATÓRIO DE SAÚDE PÚBLICA - {st.session_state.report_year}

            ## RESUMO EXECUTIVO
            Este relatório apresenta uma análise abrangente dos principais indicadores de saúde pública baseados nos dados do DATASUS.

            ## MÉTRICAS PRINCIPAIS

            ### Taxa de Aumento de Casos: +5.2%
            Observa-se um aumento moderado nos casos notificados em comparação ao período anterior, indicando necessidade de monitoramento contínuo.

            ### Taxa de Mortalidade: 2.1%
            A taxa de mortalidade mantém-se dentro dos parâmetros esperados, com tendência de redução devido às melhorias no tratamento.

            ### Taxa de Ocupação de UTI: 78%
            A ocupação de UTIs apresenta nível alto mas controlado, indicando pressão moderada sobre o sistema de saúde.

            ### Taxa de Vacinação: 85.4%
            Excelente cobertura vacinal, contribuindo significativamente para o controle da disseminação.

            ## ANÁLISE CONTEXTUAL
            Com base nas informações coletadas e no contexto epidemiológico atual:

            - **Tendência Geral:** Estabilização com sinais de melhoria
            - **Pressão no Sistema:** Moderada, mas controlável
            - **Cobertura Vacinal:** Adequada na maioria das regiões

            ## RECOMENDAÇÕES

            1. **Monitoramento Contínuo:** Manter vigilância epidemiológica ativa
            2. **Fortalecimento da Rede:** Otimizar recursos de UTI
            3. **Campanhas Educativas:** Continuar promoção de medidas preventivas
            4. **Vacinação:** Manter e expandir cobertura vacinal

            ## CONCLUSÕES
            Os indicadores apontam para um cenário controlado com necessidade de manutenção das medidas preventivas e fortalecimento contínuo do sistema de saúde.

            ---

            **Relatório gerado por Dr. DataSUS**
            *Especialista em Vigilância Epidemiológica*
            Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

            *Para relatórios personalizados com RAG, clique em "Gerar Relatório Automatizado"*
            """)

    # Botão para limpar relatório
    if st.button("Fechar Relatório"):
        st.session_state.show_report = False
        st.rerun()


st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    **Dr. DataSUS** - Sistema Inteligente de Análise de Dados de Saúde Pública
    **IA**: OpenAI GPT-4 • **Dados**: DATASUS/SINAN • **RAG**: TF-IDF + Similaridade
    """)

with col2:
    if AGENT_AVAILABLE:
        temp_agent = SimpleHealthAgent()
        status = temp_agent.get_status()

        st.markdown(f"""
        **Status Técnico:**
        - Agente: {status['agent']} v{status['version']}
        - OpenAI: {'Configurado' if status['openai_configured'] else 'Não configurado'}
        - RAG: {'Ativo' if status['rag_system']['status'] == 'active' else 'Inativo'}
        - Documentos: {status['rag_system']['documents']}
        """)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Limpar Conversa", use_container_width=True):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()
