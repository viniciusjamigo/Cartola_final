import pandas as pd
import numpy as np
import os
import json
from utils.config import config, logger

def preparar_features_historicas(df):
    """Cria features preditivas baseadas no passado."""
    logger.info("Engenharia de Features em andamento...")
    df = df.sort_values(['ano', 'atleta_id', 'rodada'])
    
    # --- 1. Incorporar Histórico de Partidas (Mando de Campo e Adversário) ---
    if os.path.exists(config.HISTORICAL_MATCHES_PATH):
        try:
            df_partidas = pd.read_csv(config.HISTORICAL_MATCHES_PATH)
            # Garante tipos para merge
            df_partidas['ano'] = pd.to_numeric(df_partidas['ano'], errors='coerce').fillna(0).astype(int)
            df_partidas['rodada'] = pd.to_numeric(df_partidas['rodada'], errors='coerce').fillna(0).astype(int)
            
            # Assegura que o DF principal também tenha os tipos corretos para merge
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce').fillna(0).astype(int)
            df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce').fillna(0).astype(int)
            
            # Carrega mapa de clubes
            if os.path.exists(config.CLUBS_DATA_PATH):
                with open(config.CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                    clubes_json = json.load(f)
                    
                mapa_abbr_id = {}
                for cid, dados in clubes_json.items():
                    if 'abreviacao' in dados:
                        mapa_abbr_id[dados['abreviacao']] = int(cid)
                    if 'nome' in dados:
                        mapa_abbr_id[dados['nome']] = int(cid)
                
                # Mapeamentos manuais para dados legados
                manual_map = {
                    'AME': 327, 'ATL': 282, 'ATM': 282, 'CAM': 282,
                    'CAP': 293, 'PAR': 293, 'ATP': 293,
                    'AVA': 314, 'CHA': 315, 'CSA': 373, 'CTB': 294, 'CFC': 294,
                    'GOI': 290, 'ACG': 373, 'CUI': 1371,
                    'RED': 280, 'RBB': 280, 'BRA': 280,
                    'SPO': 292
                }
                mapa_abbr_id.update(manual_map)
                
                if 'clube_id' in df.columns:
                    df['clube_id_str'] = df['clube_id'].astype(str)
                    df['clube_id_mapped'] = df['clube_id_str'].map(mapa_abbr_id)
                    df['clube_id_numeric_direct'] = pd.to_numeric(df['clube_id'], errors='coerce')
                    df['clube_id_num'] = df['clube_id_mapped'].fillna(df['clube_id_numeric_direct']).fillna(0).astype(int)
                else:
                    logger.error("Coluna 'clube_id' não encontrada no dataframe de jogadores.")
                    df['clube_id_num'] = 0
            else:
                logger.warning("clubes.json não encontrado. Assumindo clube_id numérico.")
                df['clube_id_num'] = pd.to_numeric(df['clube_id'], errors='coerce').fillna(0).astype(int)

            # Unificar Mandante e Adversário (VETORIZADO)
            df['clube_id_num'] = df['clube_id_num'].astype(int)
            
            # Merge para Mandante
            df = df.merge(
                df_partidas[['ano', 'rodada', 'mandante_id', 'visitante_id']].rename(columns={
                    'mandante_id': 'clube_id_num',
                    'visitante_id': 'adversario_id_match_h'
                }),
                on=['ano', 'rodada', 'clube_id_num'],
                how='left'
            )
            
            # Merge para Visitante
            df = df.merge(
                df_partidas[['ano', 'rodada', 'visitante_id', 'mandante_id']].rename(columns={
                    'visitante_id': 'clube_id_num',
                    'mandante_id': 'adversario_id_match_a'
                }),
                on=['ano', 'rodada', 'clube_id_num'],
                how='left'
            )
            
            df['fl_mandante'] = df['adversario_id_match_h'].notna().astype(int)
            df['adversario_id'] = df['adversario_id_match_h'].fillna(df['adversario_id_match_a'])
            df.drop(columns=['adversario_id_match_h', 'adversario_id_match_a'], inplace=True)
            
            # Merge com estatísticas de times (Força do Adversário)
            if os.path.exists(config.ESTATISTICAS_TIMES_PATH):
                df_stats = pd.read_csv(config.ESTATISTICAS_TIMES_PATH)
                df_stats_adv = df_stats[['clube_id', 'media_gols_feitos', 'media_gols_sofridos']].rename(columns={
                    'clube_id': 'adversario_id',
                    'media_gols_feitos': 'adv_media_gols_feitos',
                    'media_gols_sofridos': 'adv_media_gols_sofridos'
                })
                df = df.merge(df_stats_adv, on='adversario_id', how='left')
                df['adv_media_gols_feitos'].fillna(1.0, inplace=True)
                df['adv_media_gols_sofridos'].fillna(1.0, inplace=True)
            else:
                df['adv_media_gols_feitos'] = 1.0
                df['adv_media_gols_sofridos'] = 1.0
                
        except Exception as e:
            logger.error(f"Erro ao processar histórico de partidas: {e}", exc_info=True)
            df['fl_mandante'] = 0
            df['adv_media_gols_feitos'] = 1.0
            df['adv_media_gols_sofridos'] = 1.0

    # Features temporais (Pontuação)
    df['pontos_last'] = df.groupby(['ano', 'atleta_id'])['pontuacao'].shift(1)
    df['media_3_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(lambda x: x.ewm(span=3, min_periods=1).mean())
    df['media_temporada'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(lambda x: x.expanding().mean())
    
    # Scouts detalhados
    scouts_alvo = ['G', 'A', 'DS', 'SG', 'FS', 'FF', 'FD', 'FT', 'I', 'PE', 'DE', 'DP', 'GC', 'CV', 'CA', 'GS', 'PP', 'PS']
    cols_existentes = [col for col in scouts_alvo if col in df.columns]
    
    for col in cols_existentes:
        df[f'{col}_last'] = df.groupby(['ano', 'atleta_id'])[col].shift(1)
        df[f'media_{col}_last3'] = df.groupby(['ano', 'atleta_id'])[f'{col}_last'].transform(lambda x: x.ewm(span=3, min_periods=1).mean())
        df[f'media_{col}_season'] = df.groupby(['ano', 'atleta_id'])[f'{col}_last'].transform(lambda x: x.expanding().mean())
        df[f'media_{col}_last3'] = df[f'media_{col}_last3'].fillna(0)
        df[f'media_{col}_season'] = df[f'media_{col}_season'].fillna(0)
    
    df = df.dropna(subset=['media_temporada']).copy()
    return df

def aplicar_bonus_tatico(row):
    """Aplica multiplicadores táticos pós-previsão."""
    previsao = row.get('pontuacao_prevista_base', 0)
    posicao = row['posicao_id']
    
    fator_casa = row.get('fator_casa', 0)
    if fator_casa == 0 and 'fl_mandante' in row:
        fator_casa = 1 if row['fl_mandante'] == 1 else -1

    media_gols_sofridos_adv = row.get('adv_media_gols_sofridos', None)
    media_gols_feitos_adv = row.get('adv_media_gols_feitos', None)
    prob_vitoria = row.get('prob_vitoria', 0.33)
    diff_aproveitamento = row.get('diff_aproveitamento', 0.0)
    
    multiplicador = 1.0
    
    # Fator Odds
    if prob_vitoria > 0.5:
        multiplicador += (prob_vitoria - 0.5) * 0.6 
    elif prob_vitoria < 0.2:
        multiplicador -= 0.10
    
    # Fator Aproveitamento (Momento do Time)
    if diff_aproveitamento > 20: # Time 20% melhor que adversário
        multiplicador += 0.10
    elif diff_aproveitamento < -20: # Time 20% pior que adversário
        multiplicador -= 0.05
    
    # Mando de Campo
    if fator_casa == 1: multiplicador += 0.08 
    elif fator_casa == -1: multiplicador -= 0.03 
        
    # Defesa (GOL/LAT/ZAG)
    if posicao in [1, 2, 3]: 
        if media_gols_feitos_adv is not None:
             if media_gols_feitos_adv <= 0.8: multiplicador += 0.20
             elif media_gols_feitos_adv >= 1.5: multiplicador -= 0.15
            
    # Ataque (MEI/ATA)
    if posicao in [4, 5]:
        if media_gols_sofridos_adv is not None:
            if media_gols_sofridos_adv >= 1.5: multiplicador += 0.20
            elif media_gols_sofridos_adv <= 0.8: multiplicador -= 0.15
            
    # Técnico
    if posicao == 6 and fator_casa == 1:
        eh_jogo_facil = False
        if media_gols_sofridos_adv is not None and media_gols_sofridos_adv >= 1.2:
            eh_jogo_facil = True
        if eh_jogo_facil:
            multiplicador += 0.15

    return previsao * multiplicador

