import pandas as pd
import numpy as np
import os
import json
from utils.otimizador import otimizar_escalacao
from utils.modelagem import prever_pontuacao, preparar_features_historicas

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
HISTORICAL_ODDS_PATH = os.path.join(DATA_DIR, "historico_odds.csv")
CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")

def _preparar_historico():
    """Helper para carregar e preparar histórico de jogadores."""
    if not os.path.exists(HISTORICAL_DATA_PATH):
        return None

    df_hist = pd.read_csv(HISTORICAL_DATA_PATH)
    
    # 1. Calcula média acumulada
    df_hist = df_hist.sort_values(['ano', 'atleta_id', 'rodada'])
    df_hist['pontos_last'] = df_hist.groupby(['ano', 'atleta_id'])['pontuacao'].shift(1)
    df_hist['media_num'] = df_hist.groupby(['ano', 'atleta_id'])['pontos_last'].transform(lambda x: x.expanding().mean())
    df_hist['media_num'] = df_hist['media_num'].fillna(0)

    # 2. Mapeia Clubes
    try:
        with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes_map = json.load(f)
            id_to_name = {int(k): v['nome_fantasia'] for k, v in clubes_map.items()}
            df_hist['clube'] = df_hist['clube_id'].map(id_to_name)
            df_hist['clube'] = df_hist['clube'].fillna("Desconhecido")
    except Exception as e:
        print(f"Aviso: Erro clubes: {e}")
        df_hist['clube'] = "Desconhecido"
        
    return df_hist

def simular_melhor_risco(window=10):
    """
    Simula as últimas 'window' rodadas com diferentes fatores de risco.
    """
    df_hist = _preparar_historico()
    if df_hist is None: return None, "Arquivo histórico ausente."

    ano_max = df_hist['ano'].max()
    df_ano = df_hist[df_hist['ano'] == ano_max].copy()
    rodadas = sorted(df_ano['rodada'].unique())
    if len(rodadas) < window: return None, "Dados insuficientes."
    rodadas_teste = rodadas[-window:]
    
    riscos = [0.0, 0.5, 1.0, 1.5, 2.0]
    resultados = {r: 0 for r in riscos}
    volatilidade = df_ano.groupby('atleta_id')['pontuacao'].std().fillna(2.0)
    
    posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}

    for risco in riscos:
        total = 0
        for rodada in rodadas_teste:
            df_r = df_ano[df_ano['rodada'] == rodada].copy()
            if df_r['clube'].isnull().all() or (df_r['clube'] == 'Desconhecido').all(): continue
            
            df_r['posicao'] = df_r['posicao_id'].map(posicao_map)
            df_r['volatilidade'] = df_r['atleta_id'].map(volatilidade)
            df_r['pontuacao_prevista'] = df_r['media_num'] # Proxy
            
            try:
                time = otimizar_escalacao(df_r, 'pontuacao_prevista', 'preco_num', 140, "4-3-3", risco)
                total += time['pontuacao'].sum()
            except: pass
        resultados[risco] = total

    melhor = max(resultados, key=resultados.get)
    return resultados, melhor

import streamlit as st

def simular_desempenho_recente(window=3, orcamento=140, formacao="4-3-3", risco=0.0, modelo_tipo="IA", alpha=0.2):
    """
    Simula o desempenho nas últimas 'window' rodadas usando os parâmetros EXATOS da UI.
    Tenta usar histórico de odds se disponível.
    """
    df_hist = _preparar_historico()
    if df_hist is None: return None

    ano_max = df_hist['ano'].max()
    df_ano = df_hist[df_hist['ano'] == ano_max].copy()
    rodadas = sorted(df_ano['rodada'].unique())
    
    # Pega as últimas 'window' rodadas (ex: 3)
    rodadas_teste = rodadas[-window:] if len(rodadas) >= window else rodadas
    
    resultados_detalhados = {} # {rodada: pontuacao}
    
    volatilidade = df_ano.groupby('atleta_id')['pontuacao'].std().fillna(2.0)
    posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}
    
    # SE FOR USAR MODELO IA AVANÇADA:
    if modelo_tipo == "IA Avançada (XGBoost)":
        try:
            # Melhor recarregar o RAW para garantir compatibilidade total com a função de modelagem.
            df_raw = pd.read_csv(HISTORICAL_DATA_PATH)
            
            # --- CORREÇÃO CRÍTICA DE POSIÇÃO (ID Numérico) ---
            df_raw['posicao_id_temp'] = pd.to_numeric(df_raw['posicao_id'], errors='coerce')
            if df_raw['posicao_id_temp'].isna().any():
                 mapa_posicoes = {
                    'gol': 1, 'lat': 2, 'zag': 3, 'mei': 4, 'ata': 5, 'tec': 6,
                    'goleiro': 1, 'lateral': 2, 'zagueiro': 3, 'meia': 4, 'atacante': 5, 'técnico': 6
                }
                 df_raw['posicao_id'] = df_raw['posicao_id'].astype(str).str.lower().map(mapa_posicoes).fillna(df_raw['posicao_id_temp'])
            else:
                 df_raw['posicao_id'] = df_raw['posicao_id_temp']
            
            df_raw['posicao_id'] = df_raw['posicao_id'].fillna(0).astype(int)
            df_raw.drop(columns=['posicao_id_temp'], inplace=True, errors='ignore')
            
            df_full_enriched = preparar_features_historicas(df_raw)
            
            # Atualiza df_ano com as features enriquecidas
            df_ano = df_full_enriched[df_full_enriched['ano'] == ano_max].copy()
            
            # DIAGNÓSTICO DEBUG NA UI
            try:
                if 'st' in globals() or 'streamlit' in sys.modules:
                    import streamlit as st
                    st.toast(f"IA Ativa! Features: {len(df_ano.columns)}. Mando Médio: {df_ano['fl_mandante'].mean():.2f}")
            except: pass
            
            # Atualiza média_num que pode ter mudado nome ou lógica, mas mantemos compatibilidade
            if 'media_temporada' in df_ano.columns:
                df_ano['media_num'] = df_ano['media_temporada']
                
            # Re-aplica mapeamento de clubes para exibição se necessário
            if 'clube' not in df_ano.columns:
                 with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                    clubes_map = json.load(f)
                    id_to_name = {int(k): v['nome_fantasia'] for k, v in clubes_map.items()}
                    df_ano['clube'] = df_ano['clube_id'].map(id_to_name).fillna("Desconhecido")
                    
        except Exception as e:
            print(f"Erro ao preparar features avançadas para simulação: {e}")
            try:
                st.error(f"⚠️ Erro ao ativar IA na simulação: {e}. Usando média simples.")
            except:
                pass
            pass

    # Tenta carregar histórico de odds
    df_odds_hist = None
    if os.path.exists(HISTORICAL_ODDS_PATH):
        try:
            df_odds_hist = pd.read_csv(HISTORICAL_ODDS_PATH)
        except: pass

    for rodada in rodadas_teste:
        df_r = df_ano[df_ano['rodada'] == rodada].copy()
        
        # Skip se dados inválidos
        if df_r.empty or (df_r['clube'] == 'Desconhecido').all():
            resultados_detalhados[rodada] = 0
            continue
            
        df_r['posicao'] = df_r['posicao_id'].map(posicao_map)
        df_r['volatilidade'] = df_r['atleta_id'].map(volatilidade)
        
        # --- LÓGICA DE PREVISÃO ---
        df_r['pontuacao_prevista'] = df_r['media_num']
        
        # Se for IA Avançada, usa o Modelo XGBoost
        if modelo_tipo == "IA Avançada (XGBoost)":
            try:
                # Chama a predição real usando as features enriquecidas
                df_r = prever_pontuacao(df_r, model_prefix='novo_', aplicar_bonus=True)
            except Exception as e:
                print(f"Erro ao aplicar modelo XGBoost na rodada {rodada}: {e}")
                try: st.error(f"Erro IA Rodada {rodada}: {e}") 
                except: pass
        
        # Otimização
        try:
            time = otimizar_escalacao(
                df_r, 
                coluna_pontos='pontuacao_prevista', 
                coluna_preco='preco_num', 
                orcamento_total=orcamento, 
                formacao_t_str=formacao, 
                fator_risco=risco
            )
            pts = time['pontuacao'].sum()
            resultados_detalhados[rodada] = pts
        except Exception as e:
            print(f"Erro simulação recente rodada {rodada}: {e}")
            resultados_detalhados[rodada] = 0
            
    return resultados_detalhados

def gerar_comparativo_historico(orcamento=140, formacao="4-3-3", risco=0.0):
    """
    Gera um comparativo entre:
    1. Vini (Real) - Do arquivo historico_vini.csv
    2. IA (Simulada) - O que o modelo teria escalado
    3. Máximo Possível (God Mode) - A melhor escalação possível
    """
    caminho_vini = os.path.join(DATA_DIR, "historico_vini.csv")
    if not os.path.exists(caminho_vini):
        return None, "Arquivo 'historico_vini.csv' não encontrado."
        
    df_hist = _preparar_historico()
    if df_hist is None: return None, "Histórico geral não encontrado."
    
    # Carrega histórico do usuário
    try:
        df_vini = pd.read_csv(caminho_vini, sep=';')
        # Garante tipos
        df_vini['rodada'] = pd.to_numeric(df_vini['rodada'], errors='coerce')
        df_vini['pontuacao'] = pd.to_numeric(df_vini['pontuacao'], errors='coerce')
        df_vini = df_vini.dropna(subset=['rodada', 'pontuacao'])
    except Exception as e:
        return None, f"Erro ao ler historico_vini.csv: {e}"

    ano_max = df_hist['ano'].max()
    df_ano = df_hist[df_hist['ano'] == ano_max].copy()
    
    posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}
    volatilidade = df_ano.groupby('atleta_id')['pontuacao'].std().fillna(2.0)
    
    comparativo = []
    
    # Itera sobre as rodadas que o usuário jogou
    for _, row in df_vini.iterrows():
        rodada = int(row['rodada'])
        pontos_vini = row['pontuacao']
        
        # Dados da rodada
        df_r = df_ano[df_ano['rodada'] == rodada].copy()
        
        if df_r.empty or (df_r['clube'] == 'Desconhecido').all():
            continue
            
        df_r['posicao'] = df_r['posicao_id'].map(posicao_map)
        df_r['volatilidade'] = df_r['atleta_id'].map(volatilidade)
        df_r['pontuacao_prevista'] = df_r['media_num'] # Proxy IA
        
        # 1. Simulação IA
        pontos_ia = 0
        try:
            time_ia = otimizar_escalacao(
                df_r, 
                coluna_pontos='pontuacao_prevista',
                coluna_preco='preco_num',
                orcamento_total=orcamento,
                formacao_t_str=formacao,
                fator_risco=risco
            )
            pontos_ia = time_ia['pontuacao'].sum()
        except: pass
        
        # 2. Simulação Máxima (God Mode)
        pontos_max = 0
        try:
            time_max = otimizar_escalacao(
                df_r, 
                coluna_pontos='pontuacao', 
                coluna_preco='preco_num',
                orcamento_total=orcamento + 20, 
                formacao_t_str=formacao,
                fator_risco=0.0 
            )
            if not time_max.empty:
                jogadores_linha = time_max[time_max['posicao'] != 'Técnico']
                if not jogadores_linha.empty:
                    max_pts_jogador = jogadores_linha['pontuacao'].max()
                    pontos_max = time_max['pontuacao'].sum() + max_pts_jogador 
                else:
                    pontos_max = time_max['pontuacao'].sum()
        except: pass
        
        comparativo.append({
            "Rodada": rodada,
            "Você": pontos_vini,
            "IA Estimada": pontos_ia,
            "Máximo Possível": pontos_max
        })
        
    if not comparativo:
        return None, "Nenhuma rodada coincidente encontrada para comparação."
        
    return pd.DataFrame(comparativo), "Sucesso"
