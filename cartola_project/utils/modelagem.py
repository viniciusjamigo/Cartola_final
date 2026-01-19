import sys
import os
import pandas as pd
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np
import json

from utils.config import config, logger
from utils.feature_engineering import preparar_features_historicas, aplicar_bonus_tatico

# Mapeamento de modelos
MODELOS_CONFIG = {
    'gol': {'posicoes': [1], 'nome': 'modelo_gol.pkl'},
    'def': {'posicoes': [2, 3], 'nome': 'modelo_def.pkl'}, # Lat e Zag
    'mei': {'posicoes': [4], 'nome': 'modelo_mei.pkl'},
    'ata': {'posicoes': [5], 'nome': 'modelo_ata.pkl'},
    'tec': {'posicoes': [6], 'nome': 'modelo_tec.pkl'}
}

def treinar_modelo_especifico(df_treino, nome_modelo, posicoes_nome, model_prefix='novo_', use_new_features=True):
    """Treina um modelo XGBoost para um subset de dados."""
    if df_treino.empty:
        logger.warning(f"Aviso: Sem dados para treinar modelo {posicoes_nome}.")
        return None, 0.0

    # Features básicas
    features_base = ['preco_num', 'media_temporada', 'media_3_rodadas', 'posicao_id']
    if use_new_features:
        logger.info(f"  > [Treino {model_prefix}] Usando features avançadas (mando, adversário).")
        features_base.extend(['fl_mandante', 'adv_media_gols_feitos', 'adv_media_gols_sofridos'])

    # Feature selection inteligente por posição
    scouts_relevantes_map = {
        'gol': ['DE', 'GS', 'SG', 'DP', 'PS'],
        'def': ['SG', 'DS', 'FS', 'G', 'A', 'CA', 'CV', 'GC'],
        'mei': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'ata': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'tec': []
    }
    
    scouts_do_grupo = scouts_relevantes_map.get(posicoes_nome, [])
    features_scouts = []
    for col in df_treino.columns:
        if 'media_' in col and ('_last3' in col or '_season' in col) and col not in features_base:
            partes = col.split('_')
            if len(partes) >= 3:
                nome_scout = partes[1]
                if posicoes_nome != 'tec' and (not scouts_do_grupo or nome_scout in scouts_do_grupo):
                    features_scouts.append(col)

    features = features_base + features_scouts
    for col in features:
        if col not in df_treino.columns:
            df_treino[col] = 0

    logger.info(f"  > Treinando {posicoes_nome} com {len(features)} features.")
    
    X = df_treino[features]
    y = df_treino['pontuacao']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE)
    
    modelo = XGBRegressor(
        n_estimators=1000, 
        learning_rate=0.02, 
        max_depth=6, 
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=config.RANDOM_STATE,
        n_jobs=-1,
        objective='reg:squarederror'
    )
    
    modelo.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    rmse = np.sqrt(mean_squared_error(y_test, modelo.predict(X_test)))
    logger.info(f"  > [{posicoes_nome} - {model_prefix}] RMSE: {rmse:.4f}")
    
    caminho_modelo = os.path.join(config.MODEL_DIR, f"{model_prefix}{nome_modelo}")
    joblib.dump(modelo, caminho_modelo)
    
    return modelo, rmse

def treinar_modelo(ano_limite=None, rodada_limite=None):
    try:
        if not os.path.exists(config.HISTORICAL_DATA_PATH):
            logger.error(f"Arquivo '{config.HISTORICAL_DATA_PATH}' não encontrado.")
            return False

        df = pd.read_csv(config.HISTORICAL_DATA_PATH)
        
        if ano_limite and rodada_limite:
            mask_limite = (df['ano'] < ano_limite) | ((df['ano'] == ano_limite) & (df['rodada'] <= rodada_limite))
            df = df[mask_limite].copy()
        
        df = df[df['ano'] >= config.ANO_MINIMO_TREINO].copy()
        
        # Correção de posições e limpeza
        mapa_posicoes = {'gol': 1, 'lat': 2, 'zag': 3, 'mei': 4, 'ata': 5, 'tec': 6,
                         'goleiro': 1, 'lateral': 2, 'zagueiro': 3, 'meia': 4, 'atacante': 5, 'técnico': 6}
        
        df['posicao_id'] = pd.to_numeric(df['posicao_id'], errors='coerce')
        mask_nan = df['posicao_id'].isna()
        if mask_nan.any():
            df.loc[mask_nan, 'posicao_id'] = df.loc[mask_nan, 'posicao_id'].astype(str).str.lower().map(mapa_posicoes)
            
        df = df.dropna(subset=['posicao_id', 'pontuacao'])
        df = df[df['pontuacao'] != 0]
        
        # Correção de Data Leakage
        df = df.sort_values(['ano', 'atleta_id', 'rodada'])
        df['preco_num'] = df.groupby(['ano', 'atleta_id'])['preco_num'].shift(1)
        df['preco_num'] = df['preco_num'].fillna(df['preco_num'].mean())

        df_features = preparar_features_historicas(df)
        if df_features.empty:
            return False

        metricas = {}
        for nome_grupo, cfg in MODELOS_CONFIG.items():
            df_grupo = df_features[df_features['posicao_id'].isin(cfg['posicoes'])]
            
            _, rmse_n = treinar_modelo_especifico(df_grupo, cfg['nome'], nome_grupo, 'novo_', True)
            metricas[f"novo_{nome_grupo}"] = float(rmse_n)
            
            _, rmse_l = treinar_modelo_especifico(df_grupo, cfg['nome'], nome_grupo, 'legado_', False)
            metricas[f"legado_{nome_grupo}"] = float(rmse_l)
            
        with open(config.METRICS_PATH, 'w') as f:
            json.dump(metricas, f, indent=4)
            
        return True

    except Exception as e:
        logger.error(f"Erro fatal no treinamento: {e}", exc_info=True)
        return False

def prever_pontuacao(df_rodada_atual, model_prefix='novo_', aplicar_bonus=True):
    """Aplica o modelo especialista correto para cada jogador."""
    X_full = pd.DataFrame()
    X_full['preco_num'] = df_rodada_atual['preco_num']
    X_full['media_temporada'] = df_rodada_atual['media_num']
    X_full['media_3_rodadas'] = df_rodada_atual['media_num']
    X_full['posicao_id'] = df_rodada_atual['posicao_id']
    X_full['fl_mandante'] = (df_rodada_atual['fator_casa'] == 1).astype(int) if 'fator_casa' in df_rodada_atual.columns else 0
    
    # Estatísticas do adversário e Diferença de Aproveitamento
    if os.path.exists(config.ESTATISTICAS_TIMES_PATH) and 'adversario_id' in df_rodada_atual.columns:
        df_stats = pd.read_csv(config.ESTATISTICAS_TIMES_PATH).set_index('clube_id')
        
        # Dados do Time do Jogador
        df_rodada_atual['clube_aproveitamento'] = df_rodada_atual['clube_id'].map(df_stats['aproveitamento']).fillna(50.0)
        
        # Dados do Adversário
        df_rodada_atual['adv_media_gols_feitos'] = df_rodada_atual['adversario_id'].map(df_stats['media_gols_feitos']).fillna(1.0)
        df_rodada_atual['adv_media_gols_sofridos'] = df_rodada_atual['adversario_id'].map(df_stats['media_gols_sofridos']).fillna(1.0)
        df_rodada_atual['adv_aproveitamento'] = df_rodada_atual['adversario_id'].map(df_stats['aproveitamento']).fillna(50.0)
        
        # Cálculo da DIFERENÇA de Aproveitamento (Nova Feature)
        df_rodada_atual['diff_aproveitamento'] = df_rodada_atual['clube_aproveitamento'] - df_rodada_atual['adv_aproveitamento']
        
        X_full['adv_media_gols_feitos'] = df_rodada_atual['adv_media_gols_feitos']
        X_full['adv_media_gols_sofridos'] = df_rodada_atual['adv_media_gols_sofridos']
        X_full['diff_aproveitamento'] = df_rodada_atual['diff_aproveitamento']
    else:
        df_rodada_atual['adv_media_gols_feitos'] = 1.0
        df_rodada_atual['adv_media_gols_sofridos'] = 1.0
        df_rodada_atual['diff_aproveitamento'] = 0.0
        X_full['adv_media_gols_feitos'] = 1.0
        X_full['adv_media_gols_sofridos'] = 1.0
        X_full['diff_aproveitamento'] = 0.0

    # Scouts para inferência
    scouts_alvo = ['G', 'A', 'DS', 'SG', 'FS', 'FF', 'FD', 'FT', 'I', 'PE']
    
    # Garante a existência de jogos_num (pode faltar em simulações históricas)
    if 'jogos_num' in df_rodada_atual.columns:
        jogos = df_rodada_atual['jogos_num'].values
    else:
        # Se não houver jogos_num, tenta usar a rodada ou assume 1
        jogos = df_rodada_atual['rodada'].values if 'rodada' in df_rodada_atual.columns else np.ones(len(df_rodada_atual))
    
    for col in scouts_alvo:
        if f'media_{col}_season' in df_rodada_atual.columns:
            X_full[f'media_{col}_season'] = df_rodada_atual[f'media_{col}_season']
            X_full[f'media_{col}_last3'] = df_rodada_atual[f'media_{col}_last3']
        else:
            # Força o uso de arrays numpy puros (.values) para evitar RecursionError
            valores_scout = df_rodada_atual[col].values if col in df_rodada_atual.columns else np.zeros_like(jogos)
            media = np.divide(
                valores_scout, 
                jogos, 
                out=np.zeros_like(jogos, dtype=float), 
                where=jogos != 0
            )
            X_full[f'media_{col}_season'] = media
            X_full[f'media_{col}_last3'] = media
            
    df_rodada_atual['pontuacao_prevista_base'] = df_rodada_atual['media_num']
    
    for nome_grupo, cfg in MODELOS_CONFIG.items():
        caminho = os.path.join(config.MODEL_DIR, f"{model_prefix}{cfg['nome']}")
        if not os.path.exists(caminho): continue
            
        indices = df_rodada_atual[df_rodada_atual['posicao_id'].isin(cfg['posicoes'])].index
        if len(indices) > 0:
            modelo = joblib.load(caminho)
            features = modelo.feature_names_in_ if hasattr(modelo, 'feature_names_in_') else modelo.get_booster().feature_names
            X_grupo = X_full.loc[indices].reindex(columns=features, fill_value=0)
            df_rodada_atual.loc[indices, 'pontuacao_prevista_base'] = modelo.predict(X_grupo)

    df_rodada_atual['pontuacao_prevista'] = df_rodada_atual.apply(aplicar_bonus_tatico, axis=1) if aplicar_bonus else df_rodada_atual['pontuacao_prevista_base']
    df_rodada_atual.loc[df_rodada_atual['pontuacao_prevista'] < 0.5, 'pontuacao_prevista'] = 0.5
    
    return df_rodada_atual

def verificar_features_modelo():
    """Verifica se os modelos salvos possuem as novas features."""
    try:
        for _, cfg in MODELOS_CONFIG.items():
            caminho = os.path.join(config.MODEL_DIR, cfg['nome'])
            if os.path.exists(caminho):
                modelo = joblib.load(caminho)
                features = modelo.feature_names_in_ if hasattr(modelo, 'feature_names_in_') else modelo.get_booster().feature_names
                if 'fl_mandante' not in features: return False, "Modelos antigos detectados."
        return True, "Modelos atualizados."
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    treinar_modelo()
