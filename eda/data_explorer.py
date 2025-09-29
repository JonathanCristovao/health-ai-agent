import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from typing import Dict
from datetime import datetime

# Configurações
warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class DataSUSExplorer:
    """Classe para análise exploratória de dados do DATASUS"""

    def __init__(self):
        self._raw_data = None
        self.processed_data = None
        self.metadata = {}

        # URLs do DATASUS atualizadas
        self.DATASUS_URLS = {
            2019: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2019/INFLUD19-26-06-2025.csv",
            2020: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2020/INFLUD20-26-06-2025.csv",
            2021: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2021/INFLUD21-26-06-2025.csv",
            2022: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2022/INFLUD22-26-06-2025.csv",
            2023: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2023/INFLUD23-26-06-2025.csv",
            2024: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2024/INFLUD24-26-06-2025.csv",
            2025: "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-22-09-2025.csv"
        }

        # Dicionário de colunas relevantes e seus significados
        self.RELEVANT_COLUMNS = {
            # Identificação
            'NU_NOTIFIC': 'Número da notificação',
            'DT_NOTIFIC': 'Data da notificação',
            'SG_UF_NOT': 'UF de notificação',
            'CO_MUN_NOT': 'Código município notificação',

            # Demografia
            'CS_SEXO': 'Sexo (M/F)',
            'DT_NASC': 'Data de nascimento',
            'NU_IDADE_N': 'Idade',
            'CS_RACA': 'Raça/cor',
            'CS_ESCOL_N': 'Escolaridade',

            # Residência
            'SG_UF': 'UF de residência',
            'CO_MUN_RES': 'Código município residência',

            # Sintomas e sinais
            'DT_SIN_PRI': 'Data dos primeiros sintomas',
            'FEBRE': 'Febre',
            'TOSSE': 'Tosse',
            'GARGANTA': 'Dor de garganta',
            'DISPNEIA': 'Dispneia',
            'SATURACAO': 'Saturação < 95%',
            'DIARREIA': 'Diarreia',
            'VOMITO': 'Vômito',

            # Fatores de risco
            'CARDIOPATI': 'Cardiopatia',
            'DIABETES': 'Diabetes',
            'OBESIDADE': 'Obesidade',
            'ASMA': 'Asma',
            'IMUNODEPRE': 'Imunodeficiência',

            # Vacinação
            'VACINA': 'Vacinação influenza',
            'DT_UT_DOSE': 'Data última dose',
            'VACINA_COV': 'Vacinação COVID-19',
            'DOSE_1_COV': 'Data 1ª dose COVID',
            'DOSE_2_COV': 'Data 2ª dose COVID',

            # Hospitalização
            'HOSPITAL': 'Hospitalização',
            'DT_INTERNA': 'Data internação',
            'UTI': 'UTI',
            'DT_ENTUTI': 'Data entrada UTI',
            'DT_SAIDUTI': 'Data saída UTI',
            'SUPORT_VEN': 'Suporte ventilatório',

            # Exames
            'PCR_RESUL': 'Resultado PCR',
            'CLASSI_FIN': 'Classificação final',

            # Evolução
            'EVOLUCAO': 'Evolução do caso',
            'DT_EVOLUCA': 'Data da evolução',
        }

        # Códigos de valores
        self.VALUE_CODES = {
            'CS_SEXO': {1: 'Masculino', 2: 'Feminino', 9: 'Ignorado'},
            'EVOLUCAO': {1: 'Cura', 2: 'Óbito', 3: 'Óbito por outras causas', 9: 'Ignorado'},
            'UTI': {1: 'Sim', 2: 'Não', 9: 'Ignorado'},
            'VACINA': {1: 'Sim', 2: 'Não', 9: 'Ignorado'},
            'HOSPITAL': {1: 'Sim', 2: 'Não', 9: 'Ignorado'},
            'CLASSI_FIN': {1: 'SRAG por Influenza', 2: 'SRAG por COVID-19', 3: 'SRAG por outros vírus', 4: 'SRAG não especificada', 5: 'Outros'}
        }

    def load_data(self, year: int, sample_size: int = 50000, full_eda: bool = True) -> pd.DataFrame:
        """Carrega dados do DATASUS com análise exploratória inicial"""
        print(f"Carregando dados do DATASUS para {year}...")

        if year not in self.DATASUS_URLS:
            print(f"Ano {year} não disponível. Gerando dados simulados...")
            return self._generate_sample_data(year, sample_size)

        url = self.DATASUS_URLS[year]

        # Estratégias de carregamento
        strategies = [
            {'encoding': 'latin1', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'utf-8', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'cp1252', 'sep': ';', 'on_bad_lines': 'skip'},
            {'encoding': 'iso-8859-1', 'sep': ',', 'on_bad_lines': 'skip'}
        ]

        for i, strategy in enumerate(strategies):
            try:
                print(f"Tentativa {i+1}: {strategy}")
                self._raw_data = pd.read_csv(
                    url,
                    nrows=sample_size,
                    low_memory=False,
                    **strategy
                )
                print(f"Sucesso! Carregados {len(self.raw_data)} registros com {len(self.raw_data.columns)} colunas")
                break
            except Exception as e:
                print(f"Falhou: {e}")
                continue

        if self.raw_data is None:
            print("Todas as estratégias falharam. Usando dados simulados...")
            self._raw_data = self._generate_sample_data(year, sample_size)

        # Fazer EDA inicial se solicitado
        if full_eda:
            self._initial_eda()

        return self.raw_data

    def _initial_eda(self):
        """Análise exploratória inicial dos dados brutos"""
        print("\n" + "=" * 50)
        print("ANÁLISE EXPLORATÓRIA INICIAL")
        print("=" * 50)

        if self.raw_data is None:
            print("Nenhum dado carregado")
            return

        # Informações básicas
        print(f"Shape dos dados: {self.raw_data.shape}")
        print(
            f"Período: {self.raw_data.get('DT_NOTIFIC', pd.Series()).min()} a {self.raw_data.get('DT_NOTIFIC', pd.Series()).max()}")

        # Colunas disponíveis vs relevantes
        available_cols = set(self.raw_data.columns)
        relevant_cols = set(self.RELEVANT_COLUMNS.keys())
        missing_cols = relevant_cols - available_cols
        _extra_cols = available_cols - relevant_cols

        print(f"Colunas relevantes encontradas: {len(relevant_cols & available_cols)}/{len(relevant_cols)}")
        if missing_cols:
            print(f"Colunas relevantes ausentes: {list(missing_cols)[:5]}{'...' if len(missing_cols) > 5 else ''}")

        # Análise de dados faltantes
        print("\\n🔍 ANÁLISE DE DADOS FALTANTES:")
        missing_data = self.raw_data.isnull().sum()
        missing_relevant = missing_data[missing_data.index.isin(self.RELEVANT_COLUMNS.keys())]
        if not missing_relevant.empty:
            print(missing_relevant.sort_values(ascending=False).head(10))

        # Tipos de dados
        print("\\n📝 TIPOS DE DADOS:")
        dtype_counts = self.raw_data.dtypes.value_counts()
        print(dtype_counts)

        # Salvar metadados
        self.metadata = {
            'shape': self.raw_data.shape,
            'columns_total': len(self.raw_data.columns),
            'columns_relevant': len(relevant_cols & available_cols),
            'missing_columns': list(missing_cols),
            'data_types': dtype_counts.to_dict(),
            'missing_data_pct': (self.raw_data.isnull().sum() / len(self.raw_data) * 100).to_dict(),
            'load_timestamp': datetime.now().isoformat()
        }

    def preprocess_data(self) -> pd.DataFrame:
        """Preprocessamento completo dos dados"""
        print("\\n" + "=" * 50)
        print("PREPROCESSAMENTO DE DADOS")
        print("=" * 50)

        if self.raw_data is None:
            print("Nenhum dado carregado para processar")
            return None

        df = self.raw_data.copy()

        # 1. Selecionar apenas colunas relevantes disponíveis
        available_relevant = [col for col in self.RELEVANT_COLUMNS.keys() if col in df.columns]
        df_clean = df[available_relevant].copy()
        print(f"Selecionadas {len(available_relevant)} colunas relevantes de {len(df.columns)} totais")

        # 2. Conversão de tipos de dados
        print("Convertendo tipos de dados...")

        # Datas
        date_columns = ['DT_NOTIFIC', 'DT_SIN_PRI', 'DT_INTERNA', 'DT_EVOLUCA', 'DT_NASC',
                        'DT_UT_DOSE', 'DT_ENTUTI', 'DT_SAIDUTI', 'DOSE_1_COV', 'DOSE_2_COV']

        for col in date_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce', format='%d/%m/%Y')
                print(f"{col}: {df_clean[col].notna().sum()} datas válidas")

        # Categóricas com códigos conhecidos
        for col, codes in self.VALUE_CODES.items():
            if col in df_clean.columns:
                df_clean[f'{col}_DESC'] = df_clean[col].map(codes)
                print(f"{col}: mapeamento criado")

        # Numéricas
        numeric_columns = ['NU_IDADE_N', 'CO_MUN_NOT', 'CO_MUN_RES']
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        # 3. Limpeza e validação
        print("🧹 Limpeza e validação...")

        # Remover registros com datas inválidas críticas
        initial_count = len(df_clean)
        if 'DT_NOTIFIC' in df_clean.columns:
            df_clean = df_clean.dropna(subset=['DT_NOTIFIC'])
            print(f"Removidos {initial_count - len(df_clean)} registros sem data de notificação")

        # Filtrar datas válidas (não muito antigas ou futuras)
        current_year = datetime.now().year
        if 'DT_NOTIFIC' in df_clean.columns:
            valid_dates = (df_clean['DT_NOTIFIC'].dt.year >= 2009) & (df_clean['DT_NOTIFIC'].dt.year <= current_year)
            df_clean = df_clean[valid_dates]
            print(f"Mantidos registros com datas entre 2009-{current_year}")

        # 4. Criação de variáveis derivadas
        print("Criando variáveis derivadas...")

        # Idade em faixas etárias
        if 'NU_IDADE_N' in df_clean.columns:
            df_clean['FAIXA_ETARIA'] = pd.cut(
                df_clean['NU_IDADE_N'],
                bins=[0, 2, 12, 18, 30, 45, 60, 75, 100],
                labels=['0-2', '3-12', '13-18', '19-30', '31-45', '46-60', '61-75', '75+']
            )

        # Ano e mês da notificação
        if 'DT_NOTIFIC' in df_clean.columns:
            df_clean['ANO_NOTIFIC'] = df_clean['DT_NOTIFIC'].dt.year
            df_clean['MES_NOTIFIC'] = df_clean['DT_NOTIFIC'].dt.month
            df_clean['SEMANA_NOTIFIC'] = df_clean['DT_NOTIFIC'].dt.isocalendar().week

        # Tempo entre sintomas e notificação
        if 'DT_NOTIFIC' in df_clean.columns and 'DT_SIN_PRI' in df_clean.columns:
            df_clean['DIAS_SINTOMAS_NOTIFIC'] = (df_clean['DT_NOTIFIC'] - df_clean['DT_SIN_PRI']).dt.days

        # Tempo de internação
        if 'DT_INTERNA' in df_clean.columns and 'DT_EVOLUCA' in df_clean.columns:
            df_clean['DIAS_INTERNACAO'] = (df_clean['DT_EVOLUCA'] - df_clean['DT_INTERNA']).dt.days

        # Indicadores de comorbidades
        comorbidade_cols = ['CARDIOPATI', 'DIABETES', 'OBESIDADE', 'ASMA', 'IMUNODEPRE']
        available_comorbidades = [col for col in comorbidade_cols if col in df_clean.columns]
        if available_comorbidades:
            df_clean['TEM_COMORBIDADE'] = (df_clean[available_comorbidades] == 1).any(axis=1)
            df_clean['NUM_COMORBIDADES'] = (df_clean[available_comorbidades] == 1).sum(axis=1)

        # 5. Relatório final
        self.processed_data = df_clean
        print("\\n PREPROCESSAMENTO CONCLUÍDO")
        print(f" Dados finais: {len(df_clean)} registros, {len(df_clean.columns)} colunas")
        print(f" Período: {df_clean.get('DT_NOTIFIC', pd.Series()).min()} a {df_clean.get('DT_NOTIFIC', pd.Series()).max()}")

        return df_clean

    def generate_eda_report(self) -> Dict:
        """Gera relatório completo de EDA"""
        if self.processed_data is None:
            print(" Execute preprocess_data() primeiro")
            return {}

        df = self.processed_data
        report = {}

        print("\\n" + "=" * 50)
        print("GERANDO RELATÓRIO DE EDA")
        print("=" * 50)

        # Análise temporal
        if 'DT_NOTIFIC' in df.columns:
            report['temporal'] = {
                'casos_por_mes': df.groupby('MES_NOTIFIC').size().to_dict() if 'MES_NOTIFIC' in df.columns else {},
                'casos_por_ano': df.groupby('ANO_NOTIFIC').size().to_dict() if 'ANO_NOTIFIC' in df.columns else {},
                'tendencia_mensal': df.groupby(df['DT_NOTIFIC'].dt.to_period('M')).size().to_dict()
            }

        # Análise geográfica
        if 'SG_UF' in df.columns:
            report['geografica'] = {
                'casos_por_uf': df.groupby('SG_UF').size().sort_values(ascending=False).to_dict(),
                'top_5_estados': df.groupby('SG_UF').size().nlargest(5).to_dict()
            }

        # Análise demográfica
        if 'CS_SEXO_DESC' in df.columns:
            report['demografica'] = {
                'distribuicao_sexo': df['CS_SEXO_DESC'].value_counts().to_dict(),
                'faixa_etaria': df['FAIXA_ETARIA'].value_counts().to_dict() if 'FAIXA_ETARIA' in df.columns else {}
            }

        # Análise clínica
        if 'EVOLUCAO_DESC' in df.columns:
            report['clinica'] = {
                'evolucao_casos': df['EVOLUCAO_DESC'].value_counts().to_dict(),
                'taxa_letalidade': (df['EVOLUCAO'] == 2).mean() * 100 if 'EVOLUCAO' in df.columns else 0,
                'internacao_uti': df['UTI_DESC'].value_counts().to_dict() if 'UTI_DESC' in df.columns else {}
            }

        # Análise de vacinação
        if 'VACINA' in df.columns:
            report['vacinacao'] = {
                'cobertura_geral': (
                    df['VACINA'] == 1).mean() *
                100,
                'cobertura_por_uf': df.groupby('SG_UF')['VACINA'].apply(
                    lambda x: (
                        x == 1).mean() *
                    100).sort_values().to_dict() if 'SG_UF' in df.columns else {}}

        print(" Relatório EDA gerado com sucesso!")
        return report

    def _generate_sample_data(self, year: int, sample_size: int) -> pd.DataFrame:
        """Gera dados simulados realistas quando dados reais não disponíveis"""
        print(f" Gerando {sample_size} registros simulados para {year}...")

        np.random.seed(year)

        # Datas do ano
        start_date = pd.Timestamp(f'{year}-01-01')
        end_date = pd.Timestamp(f'{year}-12-31')
        dates = pd.date_range(start_date, end_date, periods=sample_size)

        # Estados brasileiros com pesos populacionais
        estados = ['SP', 'RJ', 'MG', 'BA', 'PR', 'RS', 'PE', 'CE', 'PA', 'SC', 'GO', 'MA', 'ES',
                   'PB', 'AL', 'MT', 'MS', 'DF', 'PI', 'RN', 'RO', 'AM', 'TO', 'AC', 'SE', 'AP', 'RR']
        pesos_estados = [0.22, 0.08, 0.10, 0.07, 0.06, 0.06, 0.05, 0.04, 0.04, 0.04, 0.03, 0.03, 0.02,
                         0.02, 0.02, 0.02, 0.01, 0.01, 0.02, 0.02, 0.01, 0.02, 0.01, 0.004, 0.01, 0.004, 0.003]

        df = pd.DataFrame({
            'NU_NOTIFIC': range(1, sample_size + 1),
            'DT_NOTIFIC': np.random.choice(dates, size=sample_size),
            'SG_UF': np.random.choice(estados, size=sample_size, p=pesos_estados),
            'CS_SEXO': np.random.choice([1, 2], size=sample_size, p=[0.52, 0.48]),
            'NU_IDADE_N': np.random.gamma(shape=2, scale=25, size=sample_size).astype(int),
            'EVOLUCAO': np.random.choice([1, 2, 3, 9], size=sample_size, p=[0.85, 0.08, 0.02, 0.05]),
            'UTI': np.random.choice([1, 2, 9], size=sample_size, p=[0.15, 0.80, 0.05]),
            'VACINA': np.random.choice([1, 2, 9], size=sample_size, p=[0.75, 0.20, 0.05]),
            'HOSPITAL': np.random.choice([1, 2, 9], size=sample_size, p=[0.30, 0.65, 0.05]),
            'CLASSI_FIN': np.random.choice([1, 2, 3, 4, 5], size=sample_size, p=[0.25, 0.45, 0.15, 0.10, 0.05]),
            'CARDIOPATI': np.random.choice([1, 2, 9], size=sample_size, p=[0.12, 0.85, 0.03]),
            'DIABETES': np.random.choice([1, 2, 9], size=sample_size, p=[0.18, 0.79, 0.03]),
            'OBESIDADE': np.random.choice([1, 2, 9], size=sample_size, p=[0.22, 0.75, 0.03])
        })

        # Adicionar datas correlacionadas
        df['DT_SIN_PRI'] = df['DT_NOTIFIC'] - pd.to_timedelta(np.random.randint(0, 15, sample_size), unit='D')
        df['DT_INTERNA'] = df['DT_NOTIFIC'] + pd.to_timedelta(np.random.randint(0, 7, sample_size), unit='D')
        df['DT_EVOLUCA'] = df['DT_INTERNA'] + pd.to_timedelta(np.random.randint(1, 30, sample_size), unit='D')

        print(f" Dados simulados gerados: {len(df)} registros")
        return df

    def quick_vaccination_analysis(self) -> Dict:
        """Análise rápida de vacinação por estado"""
        if self.processed_data is None:
            print(" Execute preprocess_data() primeiro")
            return {}

        df = self.processed_data

        if 'VACINA' not in df.columns or 'SG_UF' not in df.columns:
            print(" Colunas necessárias não disponíveis")
            return {}

        # Calcular cobertura vacinal por estado
        vacina_uf = df.groupby('SG_UF')['VACINA'].agg([
            lambda x: (x == 1).sum(),  # Vacinados
            'count'  # Total
        ]).rename(columns={'<lambda>': 'vacinados', 'count': 'total'})

        vacina_uf['cobertura_pct'] = (vacina_uf['vacinados'] / vacina_uf['total'] * 100).round(2)
        vacina_uf = vacina_uf.sort_values('cobertura_pct')

        result = {
            'menor_cobertura': vacina_uf.head().to_dict('index'),
            'maior_cobertura': vacina_uf.tail().to_dict('index'),
            'media_nacional': vacina_uf['cobertura_pct'].mean(),
            'total_analisado': len(df)
        }

        return result
