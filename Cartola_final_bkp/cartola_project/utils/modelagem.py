import sys
import os

# Adiciona o diretório pai ao path para permitir importação correta quando rodado diretamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np
import json

# Tenta importar com caminho relativo ou absoluto dependendo do contexto
try:
    from utils.coleta_dados import HISTORICAL_MATCHES_PATH
except ImportError:
    from cartola_project.utils.coleta_dados import HISTORICAL_MATCHES_PATH

# --- CAMINHOS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "modelos")
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
METRICS_PATH = os.path.join(MODEL_DIR, "metricas.json")

# Mapeamento de modelos
MODELOS_CONFIG = {
    'gol': {'posicoes': [1], 'nome': 'modelo_gol.pkl'},
    'def': {'posicoes': [2, 3], 'nome': 'modelo_def.pkl'}, # Lat e Zag
    'mei': {'posicoes': [4], 'nome': 'modelo_mei.pkl'},
    'ata': {'posicoes': [5], 'nome': 'modelo_ata.pkl'},
    'tec': {'posicoes': [6], 'nome': 'modelo_tec.pkl'}
}

def preparar_features_historicas(df):
    """Cria features preditivas baseadas no passado."""
    print("Engenharia de Features em andamento...")
    df = df.sort_values(['ano', 'atleta_id', 'rodada'])
    
    # --- 1. Incorporar Histórico de Partidas (Mando de Campo e Adversário) ---
    if os.path.exists(HISTORICAL_MATCHES_PATH):
        try:
            df_partidas = pd.read_csv(HISTORICAL_MATCHES_PATH)
            # Garante tipos para merge
            df_partidas['ano'] = pd.to_numeric(df_partidas['ano'], errors='coerce').fillna(0).astype(int)
            df_partidas['rodada'] = pd.to_numeric(df_partidas['rodada'], errors='coerce').fillna(0).astype(int)
            
            # Assegura que o DF principal também tenha os tipos corretos para merge
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce').fillna(0).astype(int)
            df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce').fillna(0).astype(int)
            
            # --- CORREÇÃO: MAPEAMENTO DE IDs ---
            # O histórico de jogadores antigo usa ABREVIAÇÕES (FLA, CAM, etc.) em vez de IDs numéricos
            # Precisamos converter essas abreviações para IDs para cruzar com o histórico de partidas
            
            # Carrega mapa de clubes
            if os.path.exists(os.path.join(DATA_DIR, "clubes.json")):
                with open(os.path.join(DATA_DIR, "clubes.json"), 'r', encoding='utf8') as f:
                    clubes_json = json.load(f)
                    
                # Mapa: Abreviacao -> ID (ex: "FLA" -> 262)
                mapa_abbr_id = {}
                for cid, dados in clubes_json.items():
                    # Mapeia abreviação oficial
                    if 'abreviacao' in dados:
                        mapa_abbr_id[dados['abreviacao']] = int(cid)
                    # Mapeia nome (caso usem nome como ID)
                    if 'nome' in dados:
                        mapa_abbr_id[dados['nome']] = int(cid)
                
                # Mapeamentos manuais para dados legados
                manual_map = {
                    'AME': 327, 'ATL': 282, 'ATM': 282, 'CAM': 282,
                    'CAP': 293, 'PAR': 293, 'ATP': 293,
                    'AVA': 314, 'CHA': 315, 'CSA': 373, 'CTB': 294, 'CFC': 294,
                    'GOI': 290, 'ACG': 373, 'CUI': 1371,
                    'RED': 280, 'RBB': 280, 'BRA': 280,
                    'SPO': 292 # Adicionado mapeamento para o Sport
                }
                mapa_abbr_id.update(manual_map)
                
                # Aplica o mapeamento
                # Verifica se a coluna existe
                if 'clube_id' in df.columns:
                    # Força conversão para string para garantir o map, se houver misturas
                    df['clube_id_str'] = df['clube_id'].astype(str)
                    
                    # Tenta mapear
                    df['clube_id_mapped'] = df['clube_id_str'].map(mapa_abbr_id)
                    
                    # Onde falhou o mapeamento, tenta converter direto para int (pode já ser o ID numérico)
                    df['clube_id_numeric_direct'] = pd.to_numeric(df['clube_id'], errors='coerce')
                    
                    # Combina: Prioridade para o mapeado, senão o numérico direto
                    df['clube_id_num'] = df['clube_id_mapped'].fillna(df['clube_id_numeric_direct']).fillna(0).astype(int)
                    
                    # DEBUG CLUBES
                    nao_mapeados = df[df['clube_id_num'] == 0]['clube_id'].unique()
                    if len(nao_mapeados) > 0:
                        print(f"  ! Aviso: {len(nao_mapeados)} clubes não mapeados (ID=0). Exemplos: {nao_mapeados[:5]}")
                        # Tenta salvar o dia com um mapeamento de emergência se for muito crítico
                    
                    if not df.empty:
                        print(f"  > IDs processados. Exemplo: {df['clube_id_num'].iloc[0]} (Original: {df['clube_id'].iloc[0]})")
                else:
                    print("  ! Erro: Coluna 'clube_id' não encontrada no dataframe de jogadores.")
                    df['clube_id_num'] = 0
            else:
                print("  ! Aviso: clubes.json não encontrado. Assumindo clube_id numérico.")
                df['clube_id_num'] = pd.to_numeric(df['clube_id'], errors='coerce').fillna(0).astype(int)


            
            # Unificar Mandante e Adversário
            # Refatoração do Merge para evitar confusão de sufixos
            
            # Prepara cópia do DF de partidas para merge como MANDANTE
            # (Se jogador é do time X e X é mandante, então adversário é visitante_id)
            cols_home = {
                'mandante_id': 'mandante_id_match', # ID do clube no jogo (match)
                'visitante_id': 'visitante_id_match' # Adversário
            }
            df_partidas_home = df_partidas[['ano', 'rodada', 'mandante_id', 'visitante_id']].rename(columns=cols_home)
            
            # Garante tipos de chave de merge em ambos os lados
            df_partidas_home['ano'] = df_partidas_home['ano'].astype(int)
            df_partidas_home['rodada'] = df_partidas_home['rodada'].astype(int)
            df_partidas_home['mandante_id_match'] = df_partidas_home['mandante_id_match'].astype(int)
            
            df['clube_id_num'] = df['clube_id_num'].astype(int)
            
            # DEBUG MERGE
            print(f"  > Preparando Merge. Tipos: DF_JOG(ano={df['ano'].dtype}, rod={df['rodada'].dtype}, clube={df['clube_id_num'].dtype}) | DF_PART(ano={df_partidas_home['ano'].dtype}, rod={df_partidas_home['rodada'].dtype}, mand={df_partidas_home['mandante_id_match'].dtype})")

            df = df.merge(
                df_partidas_home,
                left_on=['ano', 'rodada', 'clube_id_num'],
                right_on=['ano', 'rodada', 'mandante_id_match'],
                how='left'
            )
            
            # Prepara cópia do DF de partidas para merge como VISITANTE
            # (Se jogador é do time X e X é visitante, então adversário é mandante_id)
            cols_away = {
                'visitante_id': 'visitante_id_match_v', # ID do clube no jogo
                'mandante_id': 'mandante_id_match_v' # Adversário
            }
            df_partidas_away = df_partidas[['ano', 'rodada', 'mandante_id', 'visitante_id']].rename(columns=cols_away)
            
            df_partidas_away['ano'] = df_partidas_away['ano'].astype(int)
            df_partidas_away['rodada'] = df_partidas_away['rodada'].astype(int)
            df_partidas_away['visitante_id_match_v'] = df_partidas_away['visitante_id_match_v'].astype(int)
            
            df = df.merge(
                df_partidas_away,
                left_on=['ano', 'rodada', 'clube_id_num'],
                right_on=['ano', 'rodada', 'visitante_id_match_v'],
                how='left'
            )
            
            # Consolidação
            # Se encontrou match no primeiro merge (mandante_id_match não é nulo), é mandante.
            df['fl_mandante'] = df['mandante_id_match'].notna().astype(int)
            
            # Adversário ID
            # Se é mandante -> adversário é visitante_id_match
            # Se não achou como mandante, tenta ver se achou como visitante (mandante_id_match_v)
            df['adversario_id'] = np.where(
                df['fl_mandante'] == 1,
                df['visitante_id_match'],
                df['mandante_id_match_v'] # Pode ser nulo se não achou o jogo
            )
            
            # Limpeza
            df.drop(columns=['mandante_id_match', 'visitante_id_match', 'visitante_id_match_v', 'mandante_id_match_v'], inplace=True, errors='ignore')
            
            jogos_com_match = df['adversario_id'].notna().sum()
            total_linhas = len(df)
            print(f"  > Histórico de Partidas cruzado: {jogos_com_match}/{total_linhas} registros encontraram sua partida correspondente.")
            if jogos_com_match == 0:
                print("  ! ALERTA CRÍTICO: Nenhum jogo foi cruzado com o histórico. Verifique o mapeamento de IDs de clubes.")
            
            print("  > Features 'fl_mandante' e 'adversario_id' processadas.")
            
            # --- MERGE COM ESTATÍSTICAS DE TIMES (Força do Adversário) ---
            estatisticas_path = os.path.join(DATA_DIR, "estatisticas_times.csv")
            if os.path.exists(estatisticas_path):
                df_stats = pd.read_csv(estatisticas_path)
                # Stats: clube_id, media_gols_sofridos, media_gols_feitos
                # Queremos saber a FORÇA DO ADVERSÁRIO.
                # Se sou Atacante, quero saber quanto o adversário SOFRE de gols.
                # Se sou Defensor, quero saber quanto o adversário FAZ de gols.
                
                df_stats_adv = df_stats[['clube_id', 'media_gols_feitos', 'media_gols_sofridos']].rename(columns={
                    'clube_id': 'adversario_id',
                    'media_gols_feitos': 'adv_media_gols_feitos',
                    'media_gols_sofridos': 'adv_media_gols_sofridos'
                })
                
                df = df.merge(df_stats_adv, on='adversario_id', how='left')
                
                # Preencher NAs com médias gerais (fallback)
                df['adv_media_gols_feitos'].fillna(1.0, inplace=True)
                df['adv_media_gols_sofridos'].fillna(1.0, inplace=True)
                print("  > Features de Força do Adversário adicionadas.")
            else:
                df['adv_media_gols_feitos'] = 1.0
                df['adv_media_gols_sofridos'] = 1.0
                
        except Exception as e:
            print(f"  ! Erro ao processar histórico de partidas: {e}")
            df['fl_mandante'] = 0
            df['adv_media_gols_feitos'] = 1.0
            df['adv_media_gols_sofridos'] = 1.0

    # Features temporais (Pontuação)
    df['pontos_last'] = df.groupby(['ano', 'atleta_id'])['pontuacao'].shift(1)
    
    # --- MELHORIA: Média Móvel Exponencial (EMA) ---
    # A EMA reage mais rápido a mudanças de fase do que a média simples
    df['media_3_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(lambda x: x.ewm(span=3, min_periods=1).mean())
    df['media_temporada'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(lambda x: x.expanding().mean())
    
    # --- NOVAS FEATURES: SCOUTS DETALHADOS (Média Móvel) ---
    # Lista de scouts relevantes para criar médias
    scouts_alvo = ['G', 'A', 'DS', 'SG', 'FS', 'FF', 'FD', 'FT', 'I', 'PE', 'DE', 'DP', 'GC', 'CV', 'CA', 'GS', 'PP', 'PS']
    
    # Verifica quais colunas existem no DF (compatibilidade com histórico antigo)
    cols_existentes = [col for col in scouts_alvo if col in df.columns]
    
    for col in cols_existentes:
        # Shift(1) porque queremos usar o dado do jogo ANTERIOR para prever o atual
        df[f'{col}_last'] = df.groupby(['ano', 'atleta_id'])[col].shift(1)
        
        # Média EMA dos últimos 3 jogos (Forma recente mais sensível)
        df[f'media_{col}_last3'] = df.groupby(['ano', 'atleta_id'])[f'{col}_last'].transform(lambda x: x.ewm(span=3, min_periods=1).mean())
        
        # Média da temporada (Consistência)
        df[f'media_{col}_season'] = df.groupby(['ano', 'atleta_id'])[f'{col}_last'].transform(lambda x: x.expanding().mean())
        
        # Preenche NaN com 0 (primeiros jogos)
        df[f'media_{col}_last3'] = df[f'media_{col}_last3'].fillna(0)
        df[f'media_{col}_season'] = df[f'media_{col}_season'].fillna(0)
    
    df = df.dropna(subset=['media_temporada']).copy()
    return df

def treinar_modelo_especifico(df_treino, nome_modelo, posicoes_nome, model_prefix='novo_', use_new_features=True):
    """Treina um modelo XGBoost para um subset de dados."""
    if df_treino.empty:
        print(f"Aviso: Sem dados para treinar modelo {posicoes_nome}.")
        return None, 0.0 # Retorno seguro para desempacotamento

    # Features básicas
    features_base = ['preco_num', 'media_temporada', 'media_3_rodadas', 'posicao_id']
    if use_new_features:
        print(f"  > [Treino {model_prefix}] Usando features avançadas (mando, adversário).")
        features_base.extend(['fl_mandante', 'adv_media_gols_feitos', 'adv_media_gols_sofridos'])
    else:
        print(f"  > [Treino {model_prefix}] Usando apenas features legadas.")

    # Identifica features de scouts criadas dinamicamente
    # features_scouts = [col for col in df_treino.columns if 'media_' in col and ('_last3' in col or '_season' in col) and col not in features_base]
    
    # --- FEATURE SELECTION INTELIGENTE POR POSIÇÃO ---
    # Define quais scouts fazem sentido para cada grupo para evitar ruído
    scouts_relevantes_map = {
        'gol': ['DE', 'GS', 'SG', 'DP', 'PS'],
        'def': ['SG', 'DS', 'FS', 'G', 'A', 'CA', 'CV', 'GC'], # Zagueiros/Laterais
        'mei': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'ata': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'tec': [] # Técnicos não têm scouts individuais
    }
    
    # Seleciona a lista de scouts alvo para esta posição
    scouts_do_grupo = scouts_relevantes_map.get(posicoes_nome, [])
    
    features_scouts = []
    for col in df_treino.columns:
        # Verifica se é uma coluna de média de scout
        if 'media_' in col and ('_last3' in col or '_season' in col) and col not in features_base:
            # Extrai o nome do scout da coluna (ex: media_DE_last3 -> DE)
            # Padrão esperado: media_NOME_last3 ou media_NOME_season
            partes = col.split('_')
            if len(partes) >= 3:
                nome_scout = partes[1]
                
                # Se for técnico, não adiciona nada. Se for outro, verifica a lista.
                # Se a lista estiver vazia (caso não mapeado), adiciona tudo por segurança.
                if posicoes_nome == 'tec':
                    continue 
                elif scouts_do_grupo and nome_scout in scouts_do_grupo:
                    features_scouts.append(col)
                elif not scouts_do_grupo:
                    features_scouts.append(col)

    features = features_base + features_scouts
    
    # Garante que todas as features existem no DF
    missing_cols = [col for col in features if col not in df_treino.columns]
    if missing_cols:
        print(f"  ! Aviso: Faltando colunas para treino: {missing_cols}")
        for col in missing_cols:
            df_treino[col] = 0

    print(f"  > Usando {len(features)} features para {posicoes_nome} (Incluindo scouts: {len(features_scouts)})")
    
    target = 'pontuacao'
    
    X = df_treino[features]
    y = df_treino[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Configuração para buscar a MÉDIA (reg:squarederror) e não a mediana (reg:absoluteerror)
    # Isso ajuda a aumentar as previsões em distribuições "skewed" como a do Cartola (muitos pontos baixos, poucos altos)
    modelo = XGBRegressor(
        n_estimators=1000, 
        learning_rate=0.02, 
        max_depth=6, 
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        objective='reg:squarederror' # MUDANÇA CRÍTICA: Foca na Média (valores maiores)
    )
    
    modelo.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    previsoes = modelo.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, previsoes))
    mae = mean_absolute_error(y_test, previsoes)
    
    print(f"  > [{posicoes_nome} - {model_prefix.strip('_')}] RMSE: {rmse:.4f} | MAE: {mae:.4f}")
    
    caminho_modelo = os.path.join(MODEL_DIR, f"{model_prefix}{nome_modelo}")
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    # Remove modelo antigo para garantir atualização
    if os.path.exists(caminho_modelo):
        try:
            os.remove(caminho_modelo)
        except OSError:
            pass

    joblib.dump(modelo, caminho_modelo)
    
    return modelo, rmse

def treinar_modelo(ano_limite=None, rodada_limite=None):
    try:
        if not os.path.exists(HISTORICAL_DATA_PATH):
            print(f"Arquivo '{HISTORICAL_DATA_PATH}' não encontrado.")
            return

        print("Carregando dados históricos...")
        df = pd.read_csv(HISTORICAL_DATA_PATH)
        
        # Filtra para usar apenas dados a partir de 2022
        print(f"Dados históricos totais: {len(df)}")
        
        # --- FILTRO DE ANO E RODADA (CONTROLE DO USUÁRIO) ---
        if ano_limite and rodada_limite:
            print(f"Aplicando limite de treino: Até Rodada {rodada_limite} de {ano_limite}")
            # Lógica: Pega tudo antes do ano limite, OU do ano limite mas até a rodada especificada
            mask_limite = (df['ano'] < ano_limite) | ((df['ano'] == ano_limite) & (df['rodada'] <= rodada_limite))
            df = df[mask_limite].copy()
        
        df = df[df['ano'] >= 2022].copy()
        print(f"Dados após filtro de ano (>= 2022) e corte ({ano_limite if ano_limite else 'N/A'}): {len(df)}")
        
        # Limpeza e Tipagem
        # Adiciona os scouts relevantes à lista de colunas essenciais
        scouts_alvo = ['G', 'A', 'DS', 'SG', 'FS', 'FF', 'FD', 'FT', 'I', 'PE']
        cols_essenciais = ['ano', 'atleta_id', 'rodada', 'pontuacao', 'preco_num', 'variacao_num', 'posicao_id', 'clube_id'] + scouts_alvo
        
        # Verifica colunas existentes
        cols_disponiveis = [c for c in cols_essenciais if c in df.columns]
        df = df[cols_disponiveis].copy()
        
        # --- CORREÇÃO DE POSIÇÕES (TEXTO -> ID) ---
        # Tenta converter para numérico primeiro (preserva 1, 2, 3...)
        df['posicao_id_num'] = pd.to_numeric(df['posicao_id'], errors='coerce')
        
        # Para os que falharam (NaN), tenta mapear do texto
        mask_nan_pos = df['posicao_id_num'].isna()
        if mask_nan_pos.any():
            # Normaliza para minúsculo para evitar problemas de Case Sensitivity
            mapa_posicoes = {
                'gol': 1, 'lat': 2, 'zag': 3, 'mei': 4, 'ata': 5, 'tec': 6,
                'goleiro': 1, 'lateral': 2, 'zagueiro': 3, 'meia': 4, 'atacante': 5, 'técnico': 6
            }
            
            # Converte apenas os problemáticos para string e mapeia
            col_texto = df.loc[mask_nan_pos, 'posicao_id'].astype(str).str.lower()
            df.loc[mask_nan_pos, 'posicao_id_num'] = col_texto.map(mapa_posicoes)
            
        df['posicao_id'] = df['posicao_id_num']
        df.drop(columns=['posicao_id_num'], inplace=True)
        
        print(f"  > Posições convertidas. Nulos finais: {df['posicao_id'].isna().sum()}")

        # DEBUG: Verificar dados antes do drop
        print(f"  > Dados antes da limpeza: {len(df)}")
        
        for col in ['pontuacao', 'preco_num', 'variacao_num', 'posicao_id']:
            if col in df.columns:
                 df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # RELAXAMENTO: Aceita preço zerado/nulo (preenche com média), mas exige pontuação válida
        media_preco = df[df['preco_num'] > 0]['preco_num'].mean()
        df['preco_num'].fillna(media_preco, inplace=True)
        df.loc[df['preco_num'] == 0, 'preco_num'] = media_preco
        
        # OBRIGATÓRIO: Ter pontuação diferente de zero (senão não serve para treino)
        # E ter posição definida
        df = df.dropna(subset=['posicao_id'])
        df = df.dropna(subset=['pontuacao'])
        
        print(f"  > Dados após dropna (posicao/pontuacao): {len(df)}")
        
        df = df[df['pontuacao'] != 0] # Remove zeros (jogadores que não jogaram)
        print(f"  > Dados válidos para treino (pontuacao != 0): {len(df)}")
        
        # --- CORREÇÃO DE DATA LEAKAGE: PREÇO ---
        # Usa shift(1) para pegar o preço da rodada anterior (Preço de Compra)
        print("  > Corrigindo DATA LEAKAGE: Calculando Preço Pré-Rodada via Shift(1)...")
        df = df.sort_values(['ano', 'atleta_id', 'rodada']) # Garante ordenação
        df['preco_pre'] = df.groupby(['ano', 'atleta_id'])['preco_num'].shift(1)
        
        # Fallback se shift for nulo (primeira rodada) ou zero
        mask_nan = df['preco_pre'].isna() | (df['preco_pre'] == 0)
        if 'variacao_num' in df.columns:
             df['variacao_num'] = df['variacao_num'].fillna(0)
             df.loc[mask_nan, 'preco_pre'] = df.loc[mask_nan, 'preco_num'] - df.loc[mask_nan, 'variacao_num']
        else:
             df.loc[mask_nan, 'preco_pre'] = df.loc[mask_nan, 'preco_num'] # Best effort
             
        df['preco_num'] = df['preco_pre']
        df.drop(columns=['preco_pre'], inplace=True)

        if df.empty:
            print("  ! ALERTA: Dados inválidos ou zerados. Iniciando download automático de histórico confiável...")
            # (Código de download de emergência mantido igual...)
            try:
                import sys
                sys.path.append(os.getcwd())
                from utils.coleta_historico_github import baixar_dados
                print("  > Baixando dados... (Aguarde)")
                baixar_dados()
                
                print("  > Recarregando...")
                if os.path.exists(HISTORICAL_DATA_PATH):
                    df = pd.read_csv(HISTORICAL_DATA_PATH)
                else:
                    # Caminho alternativo
                    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    df = pd.read_csv(os.path.join(base, "data", "historico_jogadores.csv"))

                if df['posicao_id'].dtype == 'O':
                   df['posicao_id'] = df['posicao_id'].astype(str).str.lower().map({'gol':1,'lat':2,'zag':3,'mei':4,'ata':5,'tec':6,'goleiro':1,'lateral':2,'zagueiro':3,'meia':4,'atacante':5,'técnico':6})

                for c in ['pontuacao','preco_num','variacao_num','posicao_id']: 
                    if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                
                df = df.dropna(subset=['pontuacao','posicao_id'])
                df = df[df['pontuacao']!=0]
                
                # REAPLICA CORREÇÃO NO FALLBACK
                if 'variacao_num' in df.columns:
                     df['variacao_num'] = df['variacao_num'].fillna(0)
                     df['preco_num'] = df['preco_num'] - df['variacao_num']

                print(f"  > Dados recuperados: {len(df)}")
                
                if df.empty: return False

            except Exception as e:
                print(f"Erro download emergência: {e}")
                return False

        # Engenharia de Features (Geral)
        df_features = preparar_features_historicas(df)
        
        if df_features.empty:
            return

        print("\n--- INICIANDO TREINAMENTO POR POSIÇÃO ---")
        
        metricas = {}

        # Loop para treinar cada especialista
        for nome_grupo, config in MODELOS_CONFIG.items():
            ids = config['posicoes']
            nome_arquivo = config['nome']
            
            # Filtra dados do grupo
            df_grupo = df_features[df_features['posicao_id'].isin(ids)]
            
            print(f"\n--- Treinando Especialista: {nome_grupo.upper()} ---")
            print(f"Registros encontrados: {len(df_grupo)}")

            # Treina Modelo Novo (com todas as features)
            modelo_novo, rmse_novo = treinar_modelo_especifico(
                df_grupo, nome_arquivo, nome_grupo, model_prefix='novo_', use_new_features=True
            )
            if modelo_novo:
                metricas[f"novo_{nome_grupo}"] = float(rmse_novo)

            # Treina Modelo Legado (sem as features de mando/adversário)
            modelo_legado, rmse_legado = treinar_modelo_especifico(
                df_grupo, nome_arquivo, nome_grupo, model_prefix='legado_', use_new_features=False
            )
            if modelo_legado:
                metricas[f"legado_{nome_grupo}"] = float(rmse_legado)
            
        # Salva métricas
        with open(METRICS_PATH, 'w') as f:
            json.dump(metricas, f, indent=4)
            
        print("\nTodos os modelos foram treinados e salvos.")
        return True # Sucesso

    except Exception as e:
        print(f"Erro fatal no treinamento: {e}")
        return False

def aplicar_bonus_tatico(row):
    """Aplica multiplicadores táticos pós-previsão."""
    previsao = row.get('pontuacao_prevista_base', 0)
    posicao = row['posicao_id']
    
    fator_casa = row.get('fator_casa', 0)
    if fator_casa == 0 and 'fl_mandante' in row:
        # Fallback para fl_mandante se fator_casa não existir (Backtest compatibility)
        fator_casa = 1 if row['fl_mandante'] == 1 else -1

    adv_def = row.get('adversario_forca_def', 3) # Escala 1-5
    adv_of = row.get('adversario_forca_of', 3) # Escala 1-5
    
    # NOVOS DADOS (Floats diretos de estatisticas) - Preferenciais se existirem
    media_gols_sofridos_adv = row.get('adv_media_gols_sofridos', None)
    media_gols_feitos_adv = row.get('adv_media_gols_feitos', None)
    
    prob_vitoria = row.get('prob_vitoria', 0.33) # Probabilidade de vitória baseada nas Odds
    
    multiplicador = 1.0
    
    # --- FATOR ODDS (Probabilidade Real) ---
    # Se probabilidade > 50%, ganha bônus proporcional (Mais agressivo)
    # Se probabilidade < 20%, perde pontos
    if prob_vitoria > 0.5:
        multiplicador += (prob_vitoria - 0.5) * 0.6 
    elif prob_vitoria < 0.2:
        multiplicador -= 0.10 # Azarão perde 10%
    
    # Mando de Campo (Já coberto parcialmente pelas Odds, mas reforçamos pelo fator psicológico/arbitragem)
    if fator_casa == 1: multiplicador += 0.08 
    elif fator_casa == -1: multiplicador -= 0.03 
        
    # Defesa (GOL/LAT/ZAG)
    if posicao in [1, 2, 3]: 
        # Usa média de gols feitos pelo adversário se disponível (mais preciso)
        if media_gols_feitos_adv is not None:
             if media_gols_feitos_adv <= 0.8: multiplicador += 0.20 # Adversário faz poucos gols
             elif media_gols_feitos_adv >= 1.5: multiplicador -= 0.15 # Adversário faz muitos gols
        else:
            # Fallback para escala 1-5
            if adv_of <= 2: multiplicador += 0.20
            elif adv_of >= 4: multiplicador -= 0.15
            
    # Ataque (MEI/ATA)
    if posicao in [4, 5]:
        # Usa média de gols sofridos pelo adversário se disponível (mais preciso)
        if media_gols_sofridos_adv is not None:
            if media_gols_sofridos_adv >= 1.5: multiplicador += 0.20 # Adversário toma muitos gols (Bom pra mim)
            elif media_gols_sofridos_adv <= 0.8: multiplicador -= 0.15 # Adversário toma poucos gols (Ruim pra mim)
        else:
            # Fallback para escala 1-5 (Lógica Invertida: 1=Defesa Fraca/Toma Gols? Não, geralmente 1=Forte)
            # Se 1=Forte Defesa -> Ruim para Ataque.
            # Se 5=Fraca Defesa -> Bom para Ataque.
            # O código original dizia: if adv_def <= 2: +0.20.
            # Isso implica que 1-2 é DEFESA FRACA no preprocessamento antigo. Assumindo consistência.
            if adv_def <= 2: multiplicador += 0.20 
            elif adv_def >= 4: multiplicador -= 0.15
            
    # Técnico
    if posicao == 6 and fator_casa == 1:
        # Simples bônus se jogar em casa e adversário não for pedreira
        eh_jogo_facil = False
        if media_gols_sofridos_adv is not None:
            if media_gols_sofridos_adv >= 1.2: eh_jogo_facil = True
        elif adv_def <= 2:
            eh_jogo_facil = True
            
        if eh_jogo_facil:
            multiplicador += 0.15

    return previsao * multiplicador

def prever_pontuacao(df_rodada_atual, model_prefix='novo_', aplicar_bonus=True):
    """
    Aplica o modelo especialista correto para cada jogador.
    """
    # --- LOG DE DIAGNÓSTICO ---
    # print(f"\n--- [LOG] Iniciando prever_pontuacao (prefixo='{model_prefix}', bonus={aplicar_bonus}) ---")
    
    # Features necessárias
    X_full = pd.DataFrame()
    X_full['preco_num'] = df_rodada_atual['preco_num']
    X_full['media_temporada'] = df_rodada_atual['media_num']
    X_full['media_3_rodadas'] = df_rodada_atual['media_num'] # Proxy na inferência
    X_full['posicao_id'] = df_rodada_atual['posicao_id']
    
    # --- NOVA FEATURE: MANDO DE CAMPO ---
    # O modelo espera 'fl_mandante' (0 ou 1)
    # O preprocessamento fornece 'fator_casa' (1, -1, 0)
    # A preparação histórica fornece 'fl_mandante' diretamente
    if 'fl_mandante' in df_rodada_atual.columns:
        X_full['fl_mandante'] = df_rodada_atual['fl_mandante'].astype(int)
    elif 'fator_casa' in df_rodada_atual.columns:
        X_full['fl_mandante'] = (df_rodada_atual['fator_casa'] == 1).astype(int)
    else:
        X_full['fl_mandante'] = 0
    
    # --- NOVA FEATURE: FORÇA DO ADVERSÁRIO ---
    estatisticas_path = os.path.join(DATA_DIR, "estatisticas_times.csv")
    X_full['adv_media_gols_feitos'] = 1.0
    X_full['adv_media_gols_sofridos'] = 1.0
    
    if os.path.exists(estatisticas_path) and 'adversario_id' in df_rodada_atual.columns:
        try:
            df_stats = pd.read_csv(estatisticas_path)
            stats_map_feitos = df_stats.set_index('clube_id')['media_gols_feitos'].to_dict()
            stats_map_sofridos = df_stats.set_index('clube_id')['media_gols_sofridos'].to_dict()
            
            X_full['adv_media_gols_feitos'] = df_rodada_atual['adversario_id'].map(stats_map_feitos).fillna(1.0)
            X_full['adv_media_gols_sofridos'] = df_rodada_atual['adversario_id'].map(stats_map_sofridos).fillna(1.0)
        except Exception as e:
            print(f"Erro ao carregar estatísticas do adversário na inferência: {e}")

    # --- CALCULAR FEATURES DE SCOUTS PARA INFERÊNCIA (LÓGICA CORRIGIDA) ---
    scouts_alvo = ['G', 'A', 'DS', 'SG', 'FS', 'FF', 'FD', 'FT', 'I', 'PE']
    
    for col in scouts_alvo:
        # Verifica se as features de scout já existem (cenário de análise histórica)
        # Se sim, usa-as diretamente.
        if f'media_{col}_season' in df_rodada_atual.columns and f'media_{col}_last3' in df_rodada_atual.columns:
            X_full[f'media_{col}_season'] = df_rodada_atual[f'media_{col}_season']
            X_full[f'media_{col}_last3'] = df_rodada_atual[f'media_{col}_last3']
        
        # Se não, calcula na hora usando 'jogos_num' (cenário de predição da rodada atual)
        elif 'jogos_num' in df_rodada_atual.columns:
            # Garante que a coluna base do scout exista, mesmo que seja com 0
            if col not in df_rodada_atual.columns:
                df_rodada_atual[col] = 0
            
            # Calcula a média por jogo
            media_season = np.divide(
                df_rodada_atual[col], 
                df_rodada_atual['jogos_num'], 
                out=np.zeros_like(df_rodada_atual[col], dtype=float), 
                where=df_rodada_atual['jogos_num'] != 0
            )
            
            # Usa a média da temporada como a melhor estimativa disponível para ambas as features
            X_full[f'media_{col}_season'] = media_season
            X_full[f'media_{col}_last3'] = media_season
        
        # Fallback final se nenhuma das condições for atendida
        else:
            X_full[f'media_{col}_season'] = 0
            X_full[f'media_{col}_last3'] = 0
            
    # DIAGNÓSTICO DE FEATURES NA PREVISÃO
    # print("\n--- DIAGNÓSTICO DE INFERÊNCIA ---")
    # print(f"Total de jogadores para prever: {len(X_full)}")
    if X_full['fl_mandante'].mean() == 0:
         pass # print(f"  ! AVISO: 'fl_mandante' está zerado para todos. Verifique histórico de partidas.")
    # print(f"Média de 'fl_mandante': {X_full['fl_mandante'].mean():.4f} (Esperado ~0.5)")
    # print(f"Média de 'adv_media_gols_feitos': {X_full['adv_media_gols_feitos'].mean():.4f} (Esperado != 1.0 se stats ok)")
    
    # Garante que todas as features esperadas pelo modelo estejam presentes (mesmo que zeradas)
    # Isso é crucial se o modelo foi treinado com uma feature que não conseguimos calcular agora
    # (O modelo vai ignorar colunas extras, mas falhar se faltar colunas)
    pass
    
    # Loop para prever por grupo
    for nome_grupo, config in MODELOS_CONFIG.items():
        ids = config['posicoes']
        nome_arquivo = config['nome']
        caminho_modelo = os.path.join(MODEL_DIR, f"{model_prefix}{nome_arquivo}")
        
        if not os.path.exists(caminho_modelo):
            print(f"Modelo {model_prefix}{nome_grupo} não encontrado. Pulando.")
            continue
            
        # Filtra índices dos jogadores dessa posição no DataFrame original
        indices_grupo = df_rodada_atual[df_rodada_atual['posicao_id'].isin(ids)].index
        
        if len(indices_grupo) > 0:
            try:
                modelo = joblib.load(caminho_modelo)
                
                # Seleciona features apenas desses jogadores
                X_grupo = X_full.loc[indices_grupo]
                
                # --- CORREÇÃO DE COMPATIBILIDADE ---
                # Verifica quais features o modelo espera receber
                if hasattr(modelo, 'feature_names_in_'):
                    features_esperadas = modelo.feature_names_in_
                else:
                    # Fallback para versões mais antigas do XGBoost/Scikit
                    try:
                        features_esperadas = modelo.get_booster().feature_names
                    except:
                        features_esperadas = None

                # Se conseguirmos ler as features do modelo, filtramos o input
                if features_esperadas is not None:
                    # Filtra apenas as colunas que o modelo conhece
                    cols_uteis = [col for col in features_esperadas if col in X_grupo.columns]
                    
                    # Se faltar alguma coluna que o modelo quer (mas não temos), preenchemos com 0
                    missing = [col for col in features_esperadas if col not in X_grupo.columns]
                    for col in missing:
                        X_grupo[col] = 0
                    
                    # Garante a ordem correta das colunas
                    X_grupo = X_grupo[features_esperadas]
                
                # Preve
                preds = modelo.predict(X_grupo)
                
                # Atribui de volta ao DataFrame principal
                df_rodada_atual.loc[indices_grupo, 'pontuacao_prevista_base'] = preds
                # print(f"  > Previsão feita para {nome_grupo}: {len(preds)} jogadores.")
            except Exception as e:
                print(f"Erro ao prever grupo {nome_grupo}: {e}")

    # --- LOG DE DIAGNÓSTICO ---
    # print(f"--- [LOG] Descrição da PREVISÃO BASE (antes do bônus) para '{model_prefix}':")
    # print(df_rodada_atual['pontuacao_prevista_base'].describe())

    # Se alguém ficou com 0 (modelo não encontrado ou posição estranha), usa média
    mask_zero = df_rodada_atual['pontuacao_prevista_base'] == 0
    df_rodada_atual.loc[mask_zero, 'pontuacao_prevista_base'] = df_rodada_atual.loc[mask_zero, 'media_num']
    
    # Aplica o bônus tático apenas se solicitado
    if aplicar_bonus:
        # print("Aplicando Bônus Tático...")
        df_rodada_atual['pontuacao_prevista'] = df_rodada_atual.apply(aplicar_bonus_tatico, axis=1)
    else:
        # print("Pulando Bônus Tático para o modelo Legado.")
        df_rodada_atual['pontuacao_prevista'] = df_rodada_atual['pontuacao_prevista_base']

    # --- LOG DE DIAGNÓSTICO ---
    # print(f"--- [LOG] Descrição da PREVISÃO FINAL para '{model_prefix}':")
    # print(df_rodada_atual['pontuacao_prevista'].describe())
    # print("--- [LOG] Fim de prever_pontuacao ---")

    # Ajuste final
    df_rodada_atual.loc[df_rodada_atual['pontuacao_prevista'] < 0.5, 'pontuacao_prevista'] = 0.5
    
    return df_rodada_atual

def verificar_features_modelo():
    """Verifica se os modelos salvos possuem as novas features."""
    try:
        for nome_grupo, config in MODELOS_CONFIG.items():
            caminho_modelo = os.path.join(MODEL_DIR, config['nome'])
            if os.path.exists(caminho_modelo):
                modelo = joblib.load(caminho_modelo)
                
                if hasattr(modelo, 'feature_names_in_'):
                    features = modelo.feature_names_in_
                else:
                    try:
                        features = modelo.get_booster().feature_names
                    except:
                        features = []
                
                # Verifica se features cruciais estão presentes
                tem_mando = 'fl_mandante' in features
                tem_adv = 'adv_media_gols_feitos' in features or 'adv_media_gols_sofridos' in features
                
                if not tem_mando or not tem_adv:
                    return False, f"Modelo '{nome_grupo}' antigo detectado."
                    
        return True, "Modelos atualizados."
    except Exception as e:
        return False, f"Erro ao verificar modelos: {e}"

if __name__ == "__main__":
    treinar_modelo()
