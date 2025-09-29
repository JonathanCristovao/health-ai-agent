import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from typing import Dict, Optional
import base64
import io

warnings.filterwarnings('ignore')


class DataSUSVisualizer:
    """Classe para visualizações dos dados DATASUS processados"""

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.fig_size = (12, 8)

        # Configurar estilo
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    def plot_temporal_trends(self, save_path: Optional[str] = None) -> str:
        """Gráfico de tendências temporais"""
        if 'DT_NOTIFIC' not in self.data.columns:
            return "Dados de data não disponíveis"

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Análise Temporal - DATASUS', fontsize=16, fontweight='bold')

        # Casos por mês
        if 'MES_NOTIFIC' in self.data.columns:
            monthly_cases = self.data.groupby('MES_NOTIFIC').size()
            axes[0, 0].bar(monthly_cases.index, monthly_cases.values, color='skyblue')
            axes[0, 0].set_title('Casos por Mês')
            axes[0, 0].set_xlabel('Mês')
            axes[0, 0].set_ylabel('Número de Casos')

        # Evolução temporal
        daily_cases = self.data.groupby(self.data['DT_NOTIFIC'].dt.date).size()
        axes[0, 1].plot(daily_cases.index, daily_cases.values, color='red', alpha=0.7)
        axes[0, 1].set_title('Evolução Diária')
        axes[0, 1].set_xlabel('Data')
        axes[0, 1].set_ylabel('Casos por Dia')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # Casos por semana epidemiológica
        if 'SEMANA_NOTIFIC' in self.data.columns:
            weekly_cases = self.data.groupby('SEMANA_NOTIFIC').size()
            axes[1, 0].bar(weekly_cases.index, weekly_cases.values, color='green', alpha=0.7)
            axes[1, 0].set_title('Casos por Semana Epidemiológica')
            axes[1, 0].set_xlabel('Semana')
            axes[1, 0].set_ylabel('Número de Casos')

        # Média móvel de 7 dias
        daily_cases_smooth = daily_cases.rolling(window=7).mean()
        axes[1, 1].plot(daily_cases_smooth.index, daily_cases_smooth.values, color='purple', linewidth=2)
        axes[1, 1].set_title('Média Móvel 7 dias')
        axes[1, 1].set_xlabel('Data')
        axes[1, 1].set_ylabel('Casos (Média 7 dias)')
        axes[1, 1].tick_params(axis='x', rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        # Converter para base64 para embedding
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close()

        return f"data:image/png;base64,{img_base64}"

    def plot_geographic_distribution(self) -> str:
        """Mapa de distribuição geográfica"""
        if 'SG_UF' not in self.data.columns:
            return "Dados geográficos não disponíveis"

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Distribuição Geográfica - DATASUS', fontsize=16, fontweight='bold')

        # Top 10 estados
        uf_counts = self.data['SG_UF'].value_counts().head(10)
        axes[0].bar(uf_counts.index, uf_counts.values, color='lightcoral')
        axes[0].set_title('Top 10 Estados - Número de Casos')
        axes[0].set_xlabel('Estado')
        axes[0].set_ylabel('Número de Casos')
        axes[0].tick_params(axis='x', rotation=45)

        # Análise de vacinação por estado (se disponível)
        if 'VACINA' in self.data.columns:
            vacina_uf = self.data.groupby('SG_UF')['VACINA'].apply(
                lambda x: (x == 1).mean() * 100
            ).sort_values()

            # Mostrar apenas os 15 primeiros para legibilidade
            vacina_uf_plot = vacina_uf.head(15)
            colors = ['red' if x < 70 else 'orange' if x < 80 else 'green' for x in vacina_uf_plot.values]

            axes[1].barh(vacina_uf_plot.index, vacina_uf_plot.values, color=colors)
            axes[1].set_title('Cobertura Vacinal por Estado (%)')
            axes[1].set_xlabel('Cobertura Vacinal (%)')
            axes[1].set_ylabel('Estado')

            # Linha de referência
            axes[1].axvline(x=75, color='blue', linestyle='--', alpha=0.7, label='Meta 75%')
            axes[1].legend()

        plt.tight_layout()

        # Converter para base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close()

        return f"data:image/png;base64,{img_base64}"

    def plot_demographic_analysis(self) -> str:
        """Análise demográfica"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Análise Demográfica - DATASUS', fontsize=16, fontweight='bold')

        # Distribuição por sexo
        if 'CS_SEXO_DESC' in self.data.columns:
            sexo_counts = self.data['CS_SEXO_DESC'].value_counts()
            axes[0, 0].pie(sexo_counts.values, labels=sexo_counts.index, autopct='%1.1f%%', startangle=90)
            axes[0, 0].set_title('Distribuição por Sexo')

        # Faixa etária
        if 'FAIXA_ETARIA' in self.data.columns:
            faixa_counts = self.data['FAIXA_ETARIA'].value_counts().sort_index()
            axes[0, 1].bar(range(len(faixa_counts)), faixa_counts.values, color='lightblue')
            axes[0, 1].set_title('Distribuição por Faixa Etária')
            axes[0, 1].set_xticks(range(len(faixa_counts)))
            axes[0, 1].set_xticklabels(faixa_counts.index, rotation=45)
            axes[0, 1].set_ylabel('Número de Casos')

        # Evolução dos casos
        if 'EVOLUCAO_DESC' in self.data.columns:
            evolucao_counts = self.data['EVOLUCAO_DESC'].value_counts()
            colors = ['green', 'red', 'orange', 'gray'][:len(evolucao_counts)]
            axes[1, 0].pie(evolucao_counts.values, labels=evolucao_counts.index,
                           autopct='%1.1f%%', colors=colors, startangle=90)
            axes[1, 0].set_title('Evolução dos Casos')

        # Comorbidades
        if 'NUM_COMORBIDADES' in self.data.columns:
            comorbidades = self.data['NUM_COMORBIDADES'].value_counts().sort_index()
            axes[1, 1].bar(comorbidades.index, comorbidades.values, color='salmon')
            axes[1, 1].set_title('Distribuição de Comorbidades')
            axes[1, 1].set_xlabel('Número de Comorbidades')
            axes[1, 1].set_ylabel('Número de Casos')

        plt.tight_layout()

        # Converter para base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close()

        return f"data:image/png;base64,{img_base64}"

    def plot_clinical_analysis(self) -> str:
        """Análise clínica"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Análise Clínica - DATASUS', fontsize=16, fontweight='bold')

        # Taxa de letalidade por faixa etária
        if 'FAIXA_ETARIA' in self.data.columns and 'EVOLUCAO' in self.data.columns:
            letalidade = self.data.groupby('FAIXA_ETARIA')['EVOLUCAO'].apply(
                lambda x: (x == 2).mean() * 100
            ).sort_index()

            axes[0, 0].bar(range(len(letalidade)), letalidade.values, color='darkred', alpha=0.7)
            axes[0, 0].set_title('Taxa de Letalidade por Faixa Etária (%)')
            axes[0, 0].set_xticks(range(len(letalidade)))
            axes[0, 0].set_xticklabels(letalidade.index, rotation=45)
            axes[0, 0].set_ylabel('Taxa de Letalidade (%)')

        # Utilização de UTI
        if 'UTI_DESC' in self.data.columns:
            uti_counts = self.data['UTI_DESC'].value_counts()
            axes[0, 1].pie(uti_counts.values, labels=uti_counts.index, autopct='%1.1f%%')
            axes[0, 1].set_title('Utilização de UTI')

        # Tempo de internação
        if 'DIAS_INTERNACAO' in self.data.columns:
            dias_internacao = self.data['DIAS_INTERNACAO'].dropna()
            dias_internacao = dias_internacao[(dias_internacao >= 0) & (dias_internacao <= 60)]  # Filtrar outliers

            axes[1, 0].hist(dias_internacao, bins=20, color='lightgreen', alpha=0.7, edgecolor='black')
            axes[1, 0].set_title('Distribuição do Tempo de Internação')
            axes[1, 0].set_xlabel('Dias de Internação')
            axes[1, 0].set_ylabel('Frequência')

        # Classificação final
        if 'CLASSI_FIN' in self.data.columns:
            classi_counts = self.data['CLASSI_FIN'].value_counts()
            axes[1, 1].bar(classi_counts.index, classi_counts.values, color='purple', alpha=0.7)
            axes[1, 1].set_title('Classificação Final dos Casos')
            axes[1, 1].set_xlabel('Classificação')
            axes[1, 1].set_ylabel('Número de Casos')

        plt.tight_layout()

        # Converter para base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close()

        return f"data:image/png;base64,{img_base64}"

    def create_vaccination_dashboard(self) -> Dict[str, str]:
        """Dashboard específico de vacinação"""
        if 'VACINA' not in self.data.columns:
            return {"error": "Dados de vacinação não disponíveis"}

        # Gráfico 1: Cobertura geral
        fig1, ax1 = plt.subplots(figsize=(10, 6))

        vacina_counts = self.data['VACINA_DESC'].value_counts() if 'VACINA_DESC' in self.data.columns else self.data['VACINA'].map({
            1: 'Sim', 2: 'Não', 9: 'Ignorado'}).value_counts()
        colors = ['green', 'red', 'gray']
        ax1.pie(vacina_counts.values, labels=vacina_counts.index, autopct='%1.1f%%',
                colors=colors, startangle=90)
        ax1.set_title('Cobertura Vacinal Geral', fontsize=14, fontweight='bold')

        img_buffer1 = io.BytesIO()
        plt.savefig(img_buffer1, format='png', dpi=150, bbox_inches='tight')
        img_buffer1.seek(0)
        img1_base64 = base64.b64encode(img_buffer1.read()).decode()
        plt.close()

        # Gráfico 2: Cobertura por estado
        if 'SG_UF' in self.data.columns:
            fig2, ax2 = plt.subplots(figsize=(12, 8))

            vacina_uf = self.data.groupby('SG_UF')['VACINA'].apply(
                lambda x: (x == 1).mean() * 100
            ).sort_values()

            colors = ['red' if x < 70 else 'orange' if x < 80 else 'green' for x in vacina_uf.values]
            ax2.barh(vacina_uf.index, vacina_uf.values, color=colors)
            ax2.set_title('Cobertura Vacinal por Estado (%)', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Cobertura Vacinal (%)')
            ax2.axvline(x=75, color='blue', linestyle='--', alpha=0.7, label='Meta 75%')
            ax2.legend()

            # Destacar estados com menor cobertura
            for i, (estado, valor) in enumerate(vacina_uf.head(5).items()):
                ax2.text(valor + 1, i, f'{valor:.1f}%', va='center', fontweight='bold')

            img_buffer2 = io.BytesIO()
            plt.savefig(img_buffer2, format='png', dpi=150, bbox_inches='tight')
            img_buffer2.seek(0)
            img2_base64 = base64.b64encode(img_buffer2.read()).decode()
            plt.close()
        else:
            img2_base64 = ""

        return {
            "cobertura_geral": f"data:image/png;base64,{img1_base64}",
            "cobertura_estados": f"data:image/png;base64,{img2_base64}" if img2_base64 else ""
        }
