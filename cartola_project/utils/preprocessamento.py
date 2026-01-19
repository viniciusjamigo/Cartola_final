import pandas as pd
import os
import json
import numpy as np
from utils.config import config, logger
from utils.validacao import validar_dados_rodada, validar_partidas

# --- DICIONÁRIO DE FORÇA (SIMULADO) ---
RANKING_FORCA = {
    "Palmeiras": {"def": 5, "of": 5},
    "Flamengo": {"def": 4, "of": 5},
    "Botafogo": {"def": 5, "of": 4},
    "Fortaleza": {"def": 4, "of": 4},
    "Internacional": {"def": 4, "of": 3},
    "São Paulo": {"def": 4, "of": 3},
    "Cruzeiro": {"def": 4, "of": 3},
    "Bahia": {"def": 3, "of": 4},
    "Atlético-MG": {"def": 3, "of": 4},
    "Vasco": {"def": 3, "of": 3},
    "Bragantino": {"def": 3, "of": 3},
    "Athletico-PR": {"def": 3, "of": 3},
    "Grêmio": {"def": 2, "of": 3},
    "Juventude": {"def": 2, "of": 2},
    "Criciúma": {"def": 2, "of": 2},
    "Fluminense": {"def": 2, "of": 2},
    "Vitória": {"def": 1, "of": 2},
    "Corinthians": {"def": 3, "of": 2},
    "Cuiabá": {"def": 2, "of": 1},
    "Atlético-GO": {"def": 1, "of": 2},
    "Santos": {"def": 3, "of": 3},
    "Sport": {"def": 2, "of": 2},
    "Ceará": {"def": 2, "of": 2},
    "Mirassol": {"def": 2, "of": 2}
}

def get_forca(nome_clube, tipo):
    return RANKING_FORCA.get(nome_clube, {"def": 3, "of": 3}).get(tipo, 3)

def calcular_volatilidade():
    """Calcula o desvio padrão das pontuações da temporada atual."""
    if not os.path.exists(config.HISTORICO_ATUAL_PATH):
        return {}
    
    try:
        df = pd.read_csv(config.HISTORICO_ATUAL_PATH)
        volatilidade = df.groupby('atleta_id')['pontuacao'].std().to_dict()
        return volatilidade
    except Exception as e:
        logger.error(f"Erro ao calcular volatilidade: {e}")
        return {}

def preprocessar_dados_rodada(alpha=0.2):
    try:
        logger.info("Iniciando pré-processamento dos dados da rodada.")
        # --- 1. Carregar dados ---
        if not os.path.exists(config.RAW_DATA_PATH):
            logger.error(f"Arquivo '{config.RAW_DATA_PATH}' não encontrado.")
            return None
            
        df_jogadores_raw = pd.read_csv(config.RAW_DATA_PATH)
        df_partidas = pd.read_csv(config.MATCHES_DATA_PATH)
        
        if not validar_dados_rodada(df_jogadores_raw) or not validar_partidas(df_partidas):
            logger.error("Dados de entrada inválidos para pré-processamento.")
            return None

        with open(config.CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes_map_str = json.load(f)
            clubes_map = {int(k): v for k, v in clubes_map_str.items()}

        df_jogadores = df_jogadores_raw[df_jogadores_raw['status'] == 'Provável'].copy()
        
        # Garante IDs numéricos
        df_jogadores['clube_id'] = pd.to_numeric(df_jogadores['clube_id'], errors='coerce').fillna(0).astype(int)
        
        # --- 2. Adversário e Casa (VETORIZADO) ---
        id_para_nome = {clube_id: detalhes['nome_fantasia'] for clube_id, detalhes in clubes_map.items()}
        df_jogadores['clube'] = df_jogadores['clube_id'].map(id_para_nome) 
        
        # Prepara mapeamento de partidas (Vetorizado)
        df_casa = df_partidas[['clube_casa_id', 'clube_visitante_id']].rename(columns={
            'clube_casa_id': 'clube_id',
            'clube_visitante_id': 'adversario_id'
        })
        df_casa['fator_casa'] = 1
        
        df_fora = df_partidas[['clube_visitante_id', 'clube_casa_id']].rename(columns={
            'clube_visitante_id': 'clube_id',
            'clube_casa_id': 'adversario_id'
        })
        df_fora['fator_casa'] = -1
        
        df_confrontos = pd.concat([df_casa, df_fora], ignore_index=True)
        df_jogadores = df_jogadores.merge(df_confrontos, on='clube_id', how='left')
        
        df_jogadores['adversario'] = df_jogadores['adversario_id'].map(id_para_nome).fillna('N/A')
        df_jogadores['fator_casa'] = df_jogadores['fator_casa'].fillna(0)
        
        # --- 3. Features Táticas ---
        df_jogadores['adversario_forca_def'] = df_jogadores['adversario'].apply(lambda x: get_forca(x, 'def'))
        df_jogadores['adversario_forca_of'] = df_jogadores['adversario'].apply(lambda x: get_forca(x, 'of'))
        
        # --- 4. Volatilidade ---
        mapa_volatilidade = calcular_volatilidade()
        df_jogadores['volatilidade'] = df_jogadores['atleta_id'].map(mapa_volatilidade).fillna(2.0)

        # --- 5. Juntar com Odds (Se existirem) ---
        if os.path.exists(config.ODDS_DATA_PATH):
            df_odds = pd.read_csv(config.ODDS_DATA_PATH)
            
            df_jogadores = df_jogadores.merge(
                df_odds, 
                left_on=['clube', 'adversario'], 
                right_on=['time_casa', 'time_visitante'], 
                how='left'
            )
            
            mask_na = df_jogadores['odd_casa'].isna()
            if mask_na.any():
                 df_odds_inv = df_odds.rename(columns={
                     'time_casa': 'time_visitante_inv',
                     'time_visitante': 'time_casa_inv',
                     'odd_casa': 'odd_casa_inv',
                     'odd_visitante': 'odd_visitante_inv',
                     'odd_empate': 'odd_empate_inv'
                 })
                 df_jogadores = df_jogadores.merge(
                     df_odds_inv,
                     left_on=['clube', 'adversario'],
                     right_on=['time_visitante_inv', 'time_casa_inv'],
                     how='left'
                 )
                 df_jogadores['odd_casa'] = df_jogadores['odd_casa'].fillna(df_jogadores['odd_casa_inv'])
                 df_jogadores['odd_visitante'] = df_jogadores['odd_visitante'].fillna(df_jogadores['odd_visitante_inv'])
                 df_jogadores['odd_empate'] = df_jogadores['odd_empate'].fillna(df_jogadores['odd_empate_inv'])
                 
                 cols_to_drop = ['time_visitante_inv', 'time_casa_inv', 'odd_casa_inv', 'odd_visitante_inv', 'odd_empate_inv']
                 df_jogadores.drop(columns=[c for c in cols_to_drop if c in df_jogadores.columns], inplace=True)

            df_jogadores['odd_vitoria'] = np.where(df_jogadores['fator_casa'] == 1, df_jogadores['odd_casa'], df_jogadores['odd_visitante'])
            df_jogadores['odd_derrota'] = np.where(df_jogadores['fator_casa'] == 1, df_jogadores['odd_visitante'], df_jogadores['odd_casa'])
            
            mask_odds = df_jogadores['odd_vitoria'].notna()
            if mask_odds.any():
                df_jogadores.loc[mask_odds, 'soma_inverso_odds'] = (1/df_jogadores['odd_vitoria']) + (1/df_jogadores['odd_empate']) + (1/df_jogadores['odd_derrota'])
                df_jogadores.loc[mask_odds, 'prob_vitoria'] = (1/df_jogadores['odd_vitoria']) / df_jogadores['soma_inverso_odds']
                df_jogadores['prob_vitoria'].fillna(0.33, inplace=True)
                
                bonus = alpha * (df_jogadores['prob_vitoria'] - 0.33)
                df_jogadores['pontuacao_prevista'] = df_jogadores['media_num'] * (1 + bonus)
            else:
                df_jogadores['pontuacao_prevista'] = df_jogadores['media_num']
        else:
            df_jogadores['pontuacao_prevista'] = df_jogadores['media_num']

        # --- 6. Finalização ---
        colunas_para_manter = [
            'atleta_id', 'nome', 'clube', 'clube_id', 'posicao', 'posicao_id', 
            'status', 'pontos_num', 'preco_num', 'variacao_num', 'media_num', 
            'jogos_num', 'adversario', 'adversario_id', 'fator_casa', 'pontuacao_prevista',
            'adversario_forca_def', 'adversario_forca_of', 'volatilidade', 'prob_vitoria'
        ]
        for col in colunas_para_manter:
            if col not in df_jogadores.columns:
                df_jogadores[col] = 0
                
        df_final = df_jogadores[colunas_para_manter].copy()
        
        # Força o uso de arrays numpy puros (.values) para evitar RecursionError
        previsoes = df_final['pontuacao_prevista'].values
        precos = df_final['preco_num'].values
        
        df_final['custo_beneficio'] = np.divide(
            previsoes,
            precos,
            out=np.zeros_like(previsoes, dtype=float),
            where=(precos != 0)
        )
        
        df_final.replace([np.inf, -np.inf], np.nan, inplace=True)
        df_final.fillna(0, inplace=True)
        
        df_final.to_csv(config.PROCESSED_DATA_PATH, index=False, encoding='utf-8-sig')
        logger.info(f"Pré-processamento concluído. Salvo em '{config.PROCESSED_DATA_PATH}'")
        return df_final

    except Exception as e:
        logger.error(f"Erro inesperado no pré-processamento: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    preprocessar_dados_rodada()
