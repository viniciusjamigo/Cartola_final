import pandas as pd
import os
import json
import streamlit as st
import numpy as np
from sklearn.metrics import mean_squared_error
from utils.otimizador import otimizar_escalacao
from utils.modelagem import prever_pontuacao
from utils.feature_engineering import preparar_features_historicas
from utils.config import config

# Caminhos baseados no config
HISTORICAL_DATA_PATH = config.HISTORICAL_DATA_PATH
USER_HISTORY_PATH = os.path.join(os.path.dirname(config.RAW_DATA_PATH), "historico_vini.csv")
CLUBS_DATA_PATH = config.CLUBS_DATA_PATH
TIME_IA_34_PATH = os.path.join(os.path.dirname(config.RAW_DATA_PATH), "time_ianova_rodada_34.csv")

# Força recarregamento
VERSION = "1.8_Corrected_Price_Leakage"

@st.cache_data
def carregar_dados_historicos():
    """Carrega e prepara os dados históricos para análise."""
    if not os.path.exists(HISTORICAL_DATA_PATH):
        return None
    
    try:
        df_hist = pd.read_csv(HISTORICAL_DATA_PATH, low_memory=False)
        
        # Tratamento de tipos e preenchimento básico
        df_hist['ano'] = pd.to_numeric(df_hist['ano'], errors='coerce')
        df_hist['rodada'] = pd.to_numeric(df_hist['rodada'], errors='coerce')
        df_hist['atleta_id'] = pd.to_numeric(df_hist['atleta_id'], errors='coerce')
        df_hist['pontuacao'] = pd.to_numeric(df_hist['pontuacao'], errors='coerce').fillna(0)
        df_hist['preco_num'] = pd.to_numeric(df_hist['preco_num'], errors='coerce').fillna(0)
        df_hist['variacao_num'] = pd.to_numeric(df_hist['variacao_num'], errors='coerce').fillna(0)
        
        # --- TRATAMENTO DA POSIÇÃO (CRÍTICO) ---
        df_hist['posicao_id'] = pd.to_numeric(df_hist['posicao_id'], errors='coerce')
        
        if df_hist['posicao_id'].isnull().any():
            map_str_to_id = {
                'gol': 1, 'lat': 2, 'zag': 3, 'mei': 4, 'ata': 5, 'tec': 6,
                'Goleiro': 1, 'Lateral': 2, 'Zagueiro': 3, 'Meia': 4, 'Atacante': 5, 'Técnico': 6
            }
            mask_nan = df_hist['posicao_id'].isnull()
            raw_pos = pd.read_csv(HISTORICAL_DATA_PATH, usecols=['posicao_id'])['posicao_id']
            mapped_values = raw_pos.map(map_str_to_id)
            df_hist.loc[mask_nan, 'posicao_id'] = mapped_values[mask_nan]
            
        df_hist['posicao_id'] = df_hist['posicao_id'].fillna(0).astype(int)
        
        posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}
        df_hist['posicao'] = df_hist['posicao_id'].map(posicao_map).fillna("Outros")
        
        # Mapeamento de Clubes
        df_hist['clube_id'] = pd.to_numeric(df_hist['clube_id'], errors='coerce').fillna(0).astype(int)
        
        if os.path.exists(CLUBS_DATA_PATH):
            with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                clubes_map = json.load(f)
                id_to_name = {int(k): v['nome_fantasia'] for k, v in clubes_map.items()}
                df_hist['clube'] = df_hist['clube_id'].map(id_to_name).fillna("Desconhecido")
        else:
            df_hist['clube'] = "Desconhecido"
            
        return df_hist
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return None

def calcular_pontuacao_maxima(df_rodada, orcamento=5000): 
    """Calcula a pontuação máxima possível na rodada (Time Ideal)."""
    # Filtra quem jogou (pontuação != 0)
    df_jogaram = df_rodada[(df_rodada['pontuacao'] != 0)].copy()
    
    if df_jogaram.empty: return 0
        
    # Para o otimizador, o 'score' é a própria pontuação real
    df_jogaram['score_alvo'] = df_jogaram['pontuacao'] 
    
    # O otimizador precisa de algumas colunas extras se não existirem
    if 'posicao' not in df_jogaram.columns and 'posicao_id' in df_jogaram.columns:
        posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}
        df_jogaram['posicao'] = df_jogaram['posicao_id'].map(posicao_map).fillna("Outros")
    
    # Força que técnicos sejam técnico (garantia extra)
    df_jogaram.loc[df_jogaram['posicao_id'] == 6, 'posicao'] = 'Técnico'

    try:
        # Time ideal sem restrição de custo
        time = otimizar_escalacao(
            df_jogaram,
            coluna_pontos='score_alvo',
            coluna_preco='preco_num',
            orcamento_total=orcamento,
            formacao_t_str="4-3-3",
            fator_risco=0.0
        )
        
        if time.empty: return 0
            
        pontos_base = time['pontuacao'].sum()
        
        # Capitão: Jogador de linha com maior pontuação
        jogadores_linha = time[time['posicao'] != 'Técnico']
        bonus_capitao = 0
        if not jogadores_linha.empty:
            bonus_capitao = jogadores_linha['pontuacao'].max() * 0.5
            
        return pontos_base + bonus_capitao
    except Exception as e:
        print(f"Erro ao calcular time ideal: {e}")
        return 0

def rodar_modelo_ia(df_rodada, coluna_previsao, orcamento=140, retornar_time=False):
    """Roda uma simulação de escalação baseada em uma coluna de previsão."""
    df_validos = df_rodada.dropna(subset=[coluna_previsao]).copy()
    if df_validos.empty: return (0, None) if retornar_time else 0
    
    try:
        time_ia = otimizar_escalacao(
            df_validos,
            coluna_pontos=coluna_previsao,
            coluna_preco='preco_num',
            orcamento_total=orcamento,
            formacao_t_str="4-3-3",
            fator_risco=0.0
        )
        
        if time_ia.empty: return (0, None) if retornar_time else 0
        
        pontos_time = time_ia['pontuacao'].sum()
        jogadores_linha = time_ia[time_ia['posicao'] != 'Técnico']
        if not jogadores_linha.empty:
            idx_cap = jogadores_linha[coluna_previsao].idxmax()
            pts_cap = time_ia.loc[idx_cap, 'pontuacao']
            pontos_time += pts_cap
            # Marca o capitão no dataframe
            time_ia['capitao'] = False
            time_ia.loc[idx_cap, 'capitao'] = True
            
        return (pontos_time, time_ia) if retornar_time else pontos_time
    except:
        return (0, None) if retornar_time else 0

def gerar_dados_comparativos(ano=None):
    """
    Gera o DataFrame consolidado para o gráfico comparativo com MÚLTIPLOS MODELOS.
    """
    if ano is None:
        ano = config.PREVIOUS_YEAR

    df_hist = carregar_dados_historicos()
    if df_hist is None:
        return None, "Arquivo de histórico não encontrado.", None, None

    df_hist = df_hist[df_hist['ano'] >= 2022].copy()

    if not os.path.exists(USER_HISTORY_PATH):
        return None, "Arquivo de histórico do usuário não encontrado.", None, None
        
    try:
        df_user = pd.read_csv(USER_HISTORY_PATH, sep=';')
        df_user['rodada'] = pd.to_numeric(df_user['rodada'], errors='coerce')
        df_user = df_user.dropna(subset=['rodada', 'pontuacao'])
        df_user['rodada'] = df_user['rodada'].astype(int)
        df_user = df_user[df_user['ano'] == ano]
        if df_user.empty: return None, f"Sem dados do usuário para {ano}.", None, None
    except Exception as e:
        return None, f"Erro ao ler histórico: {e}", None, None

    # --- FEATURE ENGINEERING (GERAL) ---
    df_hist = df_hist.sort_values(['ano', 'atleta_id', 'rodada'])
    
    # --- FIX CRÍTICO DE LEAKAGE DE PREÇO ---
    # Calcula o preço da rodada anterior (Preço Pré-Rodada) usando shift(1)
    # Isso é muito mais seguro do que 'Preco - Variacao', pois a Variação pode estar zerada/errada no CSV
    df_hist['preco_pre_rodada'] = df_hist.groupby(['ano', 'atleta_id'])['preco_num'].shift(1)
    
    # Fallback: Se for a primeira rodada ou valor nulo, tenta usar Preco - Variacao
    mask_nan_pre = df_hist['preco_pre_rodada'].isna() | (df_hist['preco_pre_rodada'] == 0)
    df_hist.loc[mask_nan_pre, 'preco_pre_rodada'] = df_hist.loc[mask_nan_pre, 'preco_num'] - df_hist.loc[mask_nan_pre, 'variacao_num']
    
    try:
        df_hist = preparar_features_historicas(df_hist)
        
        if 'fl_mandante' in df_hist.columns:
            df_hist['fator_casa'] = df_hist['fl_mandante'].map({1: 1, 0: -1})
        else:
            df_hist['fator_casa'] = 0
            
        if 'media_num' not in df_hist.columns:
            if 'media_temporada' in df_hist.columns:
                df_hist['media_num'] = df_hist['media_temporada']
            else:
                 df_hist['media_num'] = df_hist.groupby(['ano', 'atleta_id'])['pontuacao'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
    except Exception as e:
        print(f"Erro ao preparar features avançadas: {e}")
        df_hist['pontos_shift'] = df_hist.groupby(['ano', 'atleta_id'])['pontuacao'].shift(1)
        df_hist['media_num'] = df_hist.groupby(['ano', 'atleta_id'])['pontos_shift'].transform(lambda x: x.expanding().mean()).fillna(0)

    # --- SIMULAÇÃO ---
    dados_grafico = []
    
    # Pega todas as rodadas do historico
    rodadas_hist = sorted(df_hist[df_hist['ano'] == ano]['rodada'].unique())
    if not rodadas_hist:
        rodadas_hist = sorted(df_user['rodada'].unique())
        
    rodadas_validas = []
    for r in rodadas_hist:
        if df_hist[(df_hist['ano'] == ano) & (df_hist['rodada'] == r)]['pontuacao'].sum() > 0:
            rodadas_validas.append(r)
            
    rodadas_analise = sorted(list(set(rodadas_validas)))

    times_detalhados = {} 
    # Detalhamento para TODAS as rodadas (não apenas últimas 3)

    rmse_y_true = []
    rmse_y_pred_nova = []
    rmse_y_pred_legado = []
    
    progresso = st.progress(0, text="Iniciando Batalha de Modelos...")
    total = len(rodadas_analise)
    
    # MANUAL LOAD REMOVED AS REQUESTED
    # (O arquivo existe, mas não vamos usá-lo para o gráfico conforme pedido explícito)

    for i, rodada in enumerate(rodadas_analise):
        progresso.progress((i + 1) / total, text=f"Processando Rodada {rodada}/{rodadas_analise[-1]}...")
        
        user_row = df_user[df_user['rodada'] == rodada]
        if not user_row.empty:
            pts_user = user_row['pontuacao'].iloc[0]
        else:
            pts_user = None
        
        # --- DADOS HISTÓRICOS PARA OTIMIZAÇÃO (FONTE DA VERDADE) ---
        df_r = df_hist[(df_hist['ano'] == ano) & (df_hist['rodada'] == rodada)].copy()
        
        if df_r.empty: continue
        
        df_r['posicao_id'] = pd.to_numeric(df_r['posicao_id'], errors='coerce').fillna(0)
        df_r['variacao_num'] = pd.to_numeric(df_r['variacao_num'], errors='coerce').fillna(0)
        
        # 1. CÁLCULO DO MÁXIMO POSSÍVEL (PURE HISTORY)
        try:
            pts_max = calcular_pontuacao_maxima(df_r)
        except:
            pts_max = 0

        # 2. PREVISÕES E OTIMIZAÇÕES DA IA
        try:
            # IA Nova
            df_novo = df_r.copy()
            
            # --- CORREÇÃO DE LEAKAGE (PREÇO) ---
            # O preço no histórico é o preço PÓS-RODADA (com a valorização).
            # Para prever, precisamos do preço PRÉ-RODADA (sem a valorização).
            # Usa o preço pré-rodada calculado globalmente (via shift)
            if 'preco_pre_rodada' in df_novo.columns:
                 df_novo['preco_num'] = df_novo['preco_pre_rodada']
            else:
                 # Fallback (não deve acontecer)
                 df_novo['preco_num'] = df_novo['preco_num'] - df_novo['variacao_num']
            
            prever_pontuacao(df_novo, model_prefix='novo_', aplicar_bonus=True)
            df_r['ia_nova'] = df_novo['pontuacao_prevista']

            # IA Legado
            df_legado = df_r.copy()
            # Correção de preço também para legado
            if 'preco_pre_rodada' in df_legado.columns:
                 df_legado['preco_num'] = df_legado['preco_pre_rodada']
            else:
                 df_legado['preco_num'] = df_legado['preco_num'] - df_legado['variacao_num']
            
            prever_pontuacao(df_legado, model_prefix='legado_', aplicar_bonus=False)
            df_r['ia_legado'] = df_legado['pontuacao_prevista']
            
            # RMSE DEBUG
            mask_valid = df_r['pontuacao'] != 0
            if mask_valid.any():
                # Debug especifico para rodada 34
                if rodada == 34:
                    y_true_34 = df_r.loc[mask_valid, 'pontuacao']
                    y_pred_34 = df_r.loc[mask_valid, 'ia_nova']
                    mse_34 = mean_squared_error(y_true_34, y_pred_34)
                    print(f"DEBUG RMSE RODADA 34: MSE={mse_34:.2f} (RMSE={np.sqrt(mse_34):.2f})")
                
                rmse_y_true.extend(df_r.loc[mask_valid, 'pontuacao'].tolist())
                rmse_y_pred_nova.extend(df_r.loc[mask_valid, 'ia_nova'].tolist())
                rmse_y_pred_legado.extend(df_r.loc[mask_valid, 'ia_legado'].tolist())
                
        except Exception as e:
            print(f"Erro na previsão XGBoost rodada {rodada}: {e}")
            df_r['ia_nova'] = df_r['media_num']
            df_r['ia_legado'] = df_r['media_num']
        
        try:
            dict_pontos_reais = df_r.set_index('atleta_id')['pontuacao'].to_dict()
            
            def calcular_pontos_reais_do_time(time_df, pontuacao_map):
                if time_df is None or time_df.empty: return 0
                soma = 0
                for _, row in time_df.iterrows():
                    pontos_jogador = 0
                    if 'atleta_id' in row and pd.notna(row['atleta_id']):
                         pontos_jogador = pontuacao_map.get(int(row['atleta_id']), 0.0)
                    elif 'nome' in row:
                         match = df_r[df_r['apelido'] == row['nome']]
                         if not match.empty:
                             pontos_jogador = match.iloc[0]['pontuacao']
                    
                    is_cap = False
                    if 'capitao' in row: is_cap = row['capitao']
                    if 'C' in row: is_cap = (row['C'] == '©️')
                    
                    if is_cap:
                         soma += pontos_jogador * 0.5
                    soma += pontos_jogador
                return soma

            # Otimização Normal (SEM OVERRIDE MANUAL)
            # Nota: rodar_modelo_ia usa 'preco_num' para otimizar custo.
            # Aqui estamos usando df_r que ainda tem o preco_num ORIGINAL (Pos-Rodada).
            # Isso é OK? O otimizador deve usar o preço que o usuário paga.
            # Se o usuário paga o PREÇO PRÉ, devemos usar PREÇO PRÉ.
            # Então devemos ajustar df_r['preco_num'] também para a otimização de custo.
            
            df_otimizar = df_r.copy()
            # Usa o preço pré-rodada calculado globalmente (via shift)
            if 'preco_pre_rodada' in df_otimizar.columns:
                 df_otimizar['preco_num'] = df_otimizar['preco_pre_rodada']
            else:
                 df_otimizar['preco_num'] = df_otimizar['preco_num'] - df_otimizar['variacao_num']
            
            _, time_ia_nova = rodar_modelo_ia(df_otimizar, 'ia_nova', retornar_time=True)
            pts_ia_nova_real = calcular_pontos_reais_do_time(time_ia_nova, dict_pontos_reais)
            
            # Detalhamento para TODAS as rodadas
            if time_ia_nova is not None:
                # VALIDAÇÃO: Verifica duplicatas antes de processar
                if 'atleta_id' in time_ia_nova.columns:
                    duplicados = time_ia_nova.duplicated(subset=['atleta_id'], keep=False)
                    if duplicados.any():
                        print(f"⚠️ AVISO: {duplicados.sum()} duplicatas encontradas no time da IA Nova (rodada {rodada}). Removendo...")
                        # Remove duplicatas mantendo a primeira ocorrência
                        time_ia_nova = time_ia_nova.drop_duplicates(subset=['atleta_id'], keep='first')
                        print(f"✅ Time limpo: {len(time_ia_nova)} jogadores únicos.")
                
                time_ia_nova['rodada'] = rodada
                time_ia_nova['pontuacao'] = time_ia_nova['atleta_id'].map(dict_pontos_reais).fillna(0.0)
                
                # Inclui atleta_id como primeira coluna
                cols_uteis = ['rodada', 'atleta_id', 'apelido', 'clube', 'posicao', 'ia_nova', 'pontuacao', 'capitao']
                for c in cols_uteis:
                    if c not in time_ia_nova.columns: time_ia_nova[c] = 0
                    
                times_detalhados[rodada] = time_ia_nova[cols_uteis].copy()
                
                # Salva o arquivo time_ianova para a rodada 34 (se aplicável)
                if rodada == 34:
                    try:
                        df_salvar = time_ia_nova[cols_uteis].copy()
                        df_salvar['C'] = df_salvar['capitao'].apply(lambda x: '©️' if x else '')
                        # Renomeia colunas para salvar
                        df_salvar = df_salvar.rename(columns={
                            'ia_nova': 'pontuacao_prevista',
                            'pontuacao': 'Real'
                        })
                        # Reordena colunas para salvar (sem rodada e capitao)
                        cols_salvar = ['C', 'atleta_id', 'apelido', 'posicao', 'clube', 'pontuacao_prevista', 'Real']
                        cols_salvar = [c for c in cols_salvar if c in df_salvar.columns]
                        df_salvar[cols_salvar].to_csv(TIME_IA_34_PATH, index=False, encoding='utf-8-sig')
                        print(f"✅ Arquivo time_ianova_rodada_34.csv salvo com sucesso com {len(df_salvar)} jogadores!")
                    except Exception as e:
                        print(f"⚠️ Erro ao salvar arquivo time_ianova_rodada_34.csv: {e}")

            # IA Legado
            _, time_ia_legado = rodar_modelo_ia(df_otimizar, 'ia_legado', retornar_time=True)
            pts_ia_legado_real = calcular_pontos_reais_do_time(time_ia_legado, dict_pontos_reais)
            
            dados_grafico.append({
                'Rodada': rodada,
                'Vini (Você)': pts_user,
                'Máximo Possível': pts_max, 
                'IA Nova (Com Mando)': pts_ia_nova_real, 
                'IA Legado (Sem Mando)': pts_ia_legado_real
            })
        except Exception as e:
            print(f"Erro na otimização da rodada {rodada}: {e}")

    progresso.empty()
    
    rmse_scores = {}
    if rmse_y_true:
        try:
            rmse_nova = np.sqrt(mean_squared_error(rmse_y_true, rmse_y_pred_nova))
            rmse_legado = np.sqrt(mean_squared_error(rmse_y_true, rmse_y_pred_legado))
            rmse_scores = {"nova": rmse_nova, "legado": rmse_legado}
        except: pass

    if not dados_grafico:
        return None, "Falha na geração dos dados.", None, None
        
    return pd.DataFrame(dados_grafico), None, rmse_scores, times_detalhados
