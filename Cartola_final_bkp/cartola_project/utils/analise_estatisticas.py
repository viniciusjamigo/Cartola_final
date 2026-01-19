import pandas as pd
import numpy as np
import os
import json
import re
from difflib import SequenceMatcher

# --- CAMINHOS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_MATCHES_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_2025.csv")
TEAM_STATS_PATH = os.path.join(DATA_DIR, "estatisticas_times.csv")
ODDS_PATH = os.path.join(DATA_DIR, "historico_odds.csv")
CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")

def carregar_clubes():
    """Carrega o mapeamento de clubes."""
    if os.path.exists(CLUBS_DATA_PATH):
        with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes = json.load(f)
            return {int(k): v['nome'] for k, v in clubes.items()}
    return {}

def carregar_clubes_nome_fantasia():
    """Carrega o mapeamento de clubes usando nome_fantasia (para matching com odds)."""
    if os.path.exists(CLUBS_DATA_PATH):
        with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes = json.load(f)
            return {int(k): v.get('nome_fantasia', v.get('nome', '')) for k, v in clubes.items()}
    return {}

def analise_times(ano=2025, clubes_filtro=None):
    """
    Análise de times similar à BIA:
    - Probabilidade de Vitória
    - Probabilidade de SG (Clean Sheet)
    - Gols sofridos
    - SG's conquistados
    - Gols marcados pelo adversário
    - SG's cedidos pelo adversário
    """
    if not os.path.exists(HISTORICAL_MATCHES_PATH):
        return None, "Arquivo de histórico de partidas não encontrado."
    
    if not os.path.exists(TEAM_STATS_PATH):
        return None, "Arquivo de estatísticas de times não encontrado."
    
    try:
        # Carrega dados
        df_partidas = pd.read_csv(HISTORICAL_MATCHES_PATH)
        df_stats = pd.read_csv(TEAM_STATS_PATH)
        clubes_map = carregar_clubes()
        clubes_map_fantasia = carregar_clubes_nome_fantasia()  # Para matching com odds
        
        # Filtra por ano
        df_partidas = df_partidas[df_partidas['ano'] == ano].copy()
        
        if df_partidas.empty:
            return None, f"Nenhum dado encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            df_stats = df_stats[df_stats['clube_nome'].isin(clubes_filtro)].copy()
        
        # Calcula probabilidade de vitória via odds da rodada atual
        prob_vitoria_media = {}
        
        # Tenta primeiro odds_rodada.csv (rodada atual)
        odds_rodada_path = os.path.join(DATA_DIR, "odds_rodada.csv")
        df_odds = None
        
        if os.path.exists(odds_rodada_path):
            df_odds = pd.read_csv(odds_rodada_path)
            df_odds = df_odds[df_odds['ano'] == ano].copy()
        
        # Se não tiver ou estiver vazio, tenta historico_odds.csv
        if df_odds is None or df_odds.empty:
            if os.path.exists(ODDS_PATH):
                df_odds = pd.read_csv(ODDS_PATH)
                df_odds = df_odds[df_odds['ano'] == ano].copy()
                # Pega a rodada mais recente
                if not df_odds.empty and 'rodada_id' in df_odds.columns:
                    rodada_max = df_odds['rodada_id'].max()
                    df_odds = df_odds[df_odds['rodada_id'] == rodada_max].copy()
        
        # Calcula probabilidade de vitória para cada time na rodada atual
        if df_odds is not None and not df_odds.empty:
            for _, row in df_odds.iterrows():
                if pd.notna(row['odd_casa']) and pd.notna(row['odd_empate']) and pd.notna(row['odd_visitante']):
                    # Calcula probabilidade: 1/odd normalizado
                    soma_inverso = (1/row['odd_casa']) + (1/row['odd_empate']) + (1/row['odd_visitante'])
                    prob_casa = (1/row['odd_casa']) / soma_inverso
                    prob_visitante = (1/row['odd_visitante']) / soma_inverso
                    
                    # Mapeia nomes para IDs usando nome_fantasia
                    time_casa = row['time_casa']
                    time_visitante = row['time_visitante']
                    
                    # Encontra IDs dos times usando nome_fantasia
                    for clube_id, clube_nome_fantasia in clubes_map_fantasia.items():
                        if clube_nome_fantasia == time_casa:
                            prob_vitoria_media[clube_id] = prob_casa * 100
                        elif clube_nome_fantasia == time_visitante:
                            prob_vitoria_media[clube_id] = prob_visitante * 100
        
        # Calcula SG's conquistados e cedidos
        sg_conquistados = {}
        sg_cedidos_adv = {}
        gols_marcados_adv = {}
        gols_sofridos_adv = {}
        
        for _, row in df_partidas.iterrows():
            mandante_id = row['mandante_id']
            visitante_id = row['visitante_id']
            placar_m = row['placar_mandante']
            placar_v = row['placar_visitante']
            
            if pd.isna(placar_m) or pd.isna(placar_v):
                continue
            
            # SG conquistado (time não tomou gol)
            if placar_v == 0:
                if mandante_id not in sg_conquistados:
                    sg_conquistados[mandante_id] = 0
                sg_conquistados[mandante_id] += 1
            
            if placar_m == 0:
                if visitante_id not in sg_conquistados:
                    sg_conquistados[visitante_id] = 0
                sg_conquistados[visitante_id] += 1
            
            # SG cedido pelo adversário (adversário não marcou)
            if placar_v == 0:
                if visitante_id not in sg_cedidos_adv:
                    sg_cedidos_adv[visitante_id] = 0
                sg_cedidos_adv[visitante_id] += 1
            
            if placar_m == 0:
                if mandante_id not in sg_cedidos_adv:
                    sg_cedidos_adv[mandante_id] = 0
                sg_cedidos_adv[mandante_id] += 1
            
            # Gols marcados pelo adversário
            if visitante_id not in gols_marcados_adv:
                gols_marcados_adv[visitante_id] = []
            gols_marcados_adv[visitante_id].append(placar_m)
            
            if mandante_id not in gols_marcados_adv:
                gols_marcados_adv[mandante_id] = []
            gols_marcados_adv[mandante_id].append(placar_v)
        
        # Calcula médias
        gols_marcados_adv_media = {k: np.mean(v) for k, v in gols_marcados_adv.items()}
        
        # Conta jogos por time
        jogos_por_time = {}
        for _, row in df_partidas.iterrows():
            mandante_id = row['mandante_id']
            visitante_id = row['visitante_id']
            if pd.notna(row['placar_mandante']) and pd.notna(row['placar_visitante']):
                jogos_por_time[mandante_id] = jogos_por_time.get(mandante_id, 0) + 1
                jogos_por_time[visitante_id] = jogos_por_time.get(visitante_id, 0) + 1
        
        # Monta DataFrame final
        resultados = []
        for _, row in df_stats.iterrows():
            clube_id = row['clube_id']
            clube_nome = row.get('clube_nome', f'Clube {clube_id}')
            
            jogos = jogos_por_time.get(clube_id, row['jogos'])
            sg_conq = sg_conquistados.get(clube_id, 0)
            sg_ced = sg_cedidos_adv.get(clube_id, 0)
            
            resultados.append({
                'Clube': clube_nome,
                'Probabilidade de Vitória (%)': prob_vitoria_media.get(clube_id, 0),
                'Gols Sofridos (Média)': row['media_gols_sofridos'],
                "SG's Conquistados (%)": (sg_conq / jogos * 100) if jogos > 0 else 0,
                'Gols Marcados - Adversário (Média)': gols_marcados_adv_media.get(clube_id, 0),
                "SG's Cedidos - Adversário (%)": (sg_ced / jogos * 100) if jogos > 0 else 0,
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('Probabilidade de Vitória (%)', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de times: {str(e)}"


def analise_goleiros(ano=2025, clubes_filtro=None):
    """
    Análise de goleiros similar à BIA:
    - Jogos, Minutos (estimado), Minutos Titular (estimado)
    - Média, Média Básica
    - Probabilidade de SG
    - Probabilidade de Vitória
    """
    if not os.path.exists(HISTORICAL_PLAYERS_PATH):
        return None, "Arquivo de histórico de jogadores não encontrado."
    
    try:
        df_historico = pd.read_csv(HISTORICAL_PLAYERS_PATH)
        clubes_map = carregar_clubes()
        clubes_map_fantasia = carregar_clubes_nome_fantasia()  # Para matching com odds
        
        # Filtra por ano e posição (goleiro = 'gol' ou 1)
        # Aceita tanto string quanto número
        mask_posicao = (df_historico['posicao_id'] == 'gol') | (df_historico['posicao_id'] == 1)
        df_goleiros = df_historico[
            (df_historico['ano'] == ano) & mask_posicao
        ].copy()
        
        if df_goleiros.empty:
            return None, f"Nenhum dado de goleiros encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            # Converte nomes para IDs
            clubes_id_filtro = [k for k, v in clubes_map.items() if v in clubes_filtro]
            df_goleiros = df_goleiros[df_goleiros['clube_id'].isin(clubes_id_filtro)].copy()
        
        # Agrupa por atleta
        resultados = []
        
        for atleta_id in df_goleiros['atleta_id'].unique():
            df_atleta = df_goleiros[df_goleiros['atleta_id'] == atleta_id].copy()
            
            # Estima minutos: assume 90 min quando pontuacao > 0
            df_atleta['minutos_estimado'] = df_atleta['pontuacao'].apply(lambda x: 90 if x > 0 else 0)
            # Minutos titular: assume 90 min quando jogou e status é Provável
            df_atleta['minutos_titular_estimado'] = df_atleta.apply(
                lambda row: 90 if (row['pontuacao'] > 0 and 
                                   str(row.get('status_id', '')).lower() in ['provável', 'provavel']) else 0, 
                axis=1
            )
            
            jogos = len(df_atleta[df_atleta['pontuacao'] > 0])
            minutos_total = df_atleta['minutos_estimado'].sum()
            minutos_titular = df_atleta['minutos_titular_estimado'].sum()
            
            # Médias
            media = df_atleta['pontuacao'].mean()
            # Média básica (sem bônus de capitão, etc) - aproximação usando média quando jogou
            media_basica = df_atleta[df_atleta['pontuacao'] > 0]['pontuacao'].mean()
            
            # Probabilidade de SG (conta quantas vezes teve SG > 0, não soma os valores)
            if 'SG' in df_atleta.columns and pd.notna(df_atleta['SG']).any():
                sg_count = len(df_atleta[df_atleta['SG'] > 0])
            else:
                sg_count = 0
            prob_sg = (sg_count / jogos * 100) if jogos > 0 else 0
            
            # Probabilidade de vitória do time (usa odds da rodada atual)
            clube_id = df_atleta.iloc[0]['clube_id']
            clube_nome = clubes_map.get(clube_id, f'Clube {clube_id}')
            clube_nome_fantasia = clubes_map_fantasia.get(clube_id, '')
            
            # Busca probabilidade do time na rodada atual
            prob_vitoria = 50  # Default
            
            # Tenta primeiro odds_rodada.csv
            odds_rodada_path = os.path.join(DATA_DIR, "odds_rodada.csv")
            df_odds = None
            
            if os.path.exists(odds_rodada_path):
                df_odds = pd.read_csv(odds_rodada_path)
                df_odds = df_odds[df_odds['ano'] == ano].copy()
            
            # Se não tiver, tenta historico_odds.csv (rodada mais recente)
            if df_odds is None or df_odds.empty:
                if os.path.exists(ODDS_PATH):
                    df_odds = pd.read_csv(ODDS_PATH)
                    df_odds = df_odds[df_odds['ano'] == ano].copy()
                    if not df_odds.empty and 'rodada_id' in df_odds.columns:
                        rodada_max = df_odds['rodada_id'].max()
                        df_odds = df_odds[df_odds['rodada_id'] == rodada_max].copy()
            
            # Busca odds do clube usando nome_fantasia
            if df_odds is not None and not df_odds.empty:
                for _, row in df_odds.iterrows():
                    if row['time_casa'] == clube_nome_fantasia or row['time_visitante'] == clube_nome_fantasia:
                        if pd.notna(row['odd_casa']) and pd.notna(row['odd_empate']) and pd.notna(row['odd_visitante']):
                            soma_inverso = (1/row['odd_casa']) + (1/row['odd_empate']) + (1/row['odd_visitante'])
                            if row['time_casa'] == clube_nome_fantasia:
                                prob_vitoria = (1/row['odd_casa']) / soma_inverso * 100
                            else:
                                prob_vitoria = (1/row['odd_visitante']) / soma_inverso * 100
                            break
            
            nome = df_atleta.iloc[0]['apelido']
            
            resultados.append({
                'Clube': clube_nome,
                'Pos': 'GOL',
                'Nome': nome,
                'Jogos': jogos,
                'Minutos': minutos_total,
                'Minutos Titular': minutos_titular,
                'Média': round(media, 2),
                'M. Básica': round(media_basica, 2),
                'Prob. de SG (%)': round(prob_sg, 1),
                'Prob. Vitória (%)': round(prob_vitoria, 1)
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('Prob. Vitória (%)', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de goleiros: {str(e)}"


def analise_atacantes(ano=2025, clubes_filtro=None):
    """
    Análise de atacantes similar à BIA:
    - Jogos, Minutos (estimado), Minutos Titular (estimado)
    - Média, Média Básica
    - Probabilidade de Ataque
    - Probabilidade de Vitória
    """
    if not os.path.exists(HISTORICAL_PLAYERS_PATH):
        return None, "Arquivo de histórico de jogadores não encontrado."
    
    try:
        df_historico = pd.read_csv(HISTORICAL_PLAYERS_PATH)
        clubes_map = carregar_clubes()
        clubes_map_fantasia = carregar_clubes_nome_fantasia()  # Para matching com odds
        
        # Filtra por ano e posição (atacante = 'ata' ou 5)
        mask_posicao = (df_historico['posicao_id'] == 'ata') | (df_historico['posicao_id'] == 5)
        df_atacantes = df_historico[
            (df_historico['ano'] == ano) & mask_posicao
        ].copy()
        
        if df_atacantes.empty:
            return None, f"Nenhum dado de atacantes encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            clubes_id_filtro = [k for k, v in clubes_map.items() if v in clubes_filtro]
            df_atacantes = df_atacantes[df_atacantes['clube_id'].isin(clubes_id_filtro)].copy()
        
        resultados = []
        
        for atleta_id in df_atacantes['atleta_id'].unique():
            df_atleta = df_atacantes[df_atacantes['atleta_id'] == atleta_id].copy()
            
            # Estima minutos
            df_atleta['minutos_estimado'] = df_atleta['pontuacao'].apply(lambda x: 90 if x > 0 else 0)
            df_atleta['minutos_titular_estimado'] = df_atleta.apply(
                lambda row: 90 if (row['pontuacao'] > 0 and 
                                   str(row.get('status_id', '')).lower() in ['provável', 'provavel']) else 0, 
                axis=1
            )
            
            jogos = len(df_atleta[df_atleta['pontuacao'] > 0])
            minutos_total = df_atleta['minutos_estimado'].sum()
            minutos_titular = df_atleta['minutos_titular_estimado'].sum()
            
            # Médias
            media = df_atleta['pontuacao'].mean()
            media_basica = df_atleta[df_atleta['pontuacao'] > 0]['pontuacao'].mean()
            
            # Probabilidade de ataque (chance de marcar/assistir)
            g_col = df_atleta['G'] if 'G' in df_atleta.columns else pd.Series([0] * len(df_atleta))
            a_col = df_atleta['A'] if 'A' in df_atleta.columns else pd.Series([0] * len(df_atleta))
            jogos_com_gol_ou_assist = len(df_atleta[(g_col > 0) | (a_col > 0)])
            prob_ataque = (jogos_com_gol_ou_assist / jogos * 100) if jogos > 0 else 0
            
            # Probabilidade de vitória do time (usa odds da rodada atual)
            clube_id = df_atleta.iloc[0]['clube_id']
            clube_nome = clubes_map.get(clube_id, f'Clube {clube_id}')
            clube_nome_fantasia = clubes_map_fantasia.get(clube_id, '')
            prob_vitoria = 50  # Default
            
            # Tenta primeiro odds_rodada.csv
            odds_rodada_path = os.path.join(DATA_DIR, "odds_rodada.csv")
            df_odds = None
            
            if os.path.exists(odds_rodada_path):
                df_odds = pd.read_csv(odds_rodada_path)
                df_odds = df_odds[df_odds['ano'] == ano].copy()
            
            # Se não tiver, tenta historico_odds.csv (rodada mais recente)
            if df_odds is None or df_odds.empty:
                if os.path.exists(ODDS_PATH):
                    df_odds = pd.read_csv(ODDS_PATH)
                    df_odds = df_odds[df_odds['ano'] == ano].copy()
                    if not df_odds.empty and 'rodada_id' in df_odds.columns:
                        rodada_max = df_odds['rodada_id'].max()
                        df_odds = df_odds[df_odds['rodada_id'] == rodada_max].copy()
            
            # Busca odds do clube usando nome_fantasia
            if df_odds is not None and not df_odds.empty:
                for _, row in df_odds.iterrows():
                    if row['time_casa'] == clube_nome_fantasia or row['time_visitante'] == clube_nome_fantasia:
                        if pd.notna(row['odd_casa']) and pd.notna(row['odd_empate']) and pd.notna(row['odd_visitante']):
                            soma_inverso = (1/row['odd_casa']) + (1/row['odd_empate']) + (1/row['odd_visitante'])
                            if row['time_casa'] == clube_nome_fantasia:
                                prob_vitoria = (1/row['odd_casa']) / soma_inverso * 100
                            else:
                                prob_vitoria = (1/row['odd_visitante']) / soma_inverso * 100
                            break
            
            nome = df_atleta.iloc[0]['apelido']
            
            resultados.append({
                'Clube': clube_nome,
                'Pos': 'ATA',
                'Nome': nome,
                'Jogos': jogos,
                'Minutos': minutos_total,
                'Minutos Titular': minutos_titular,
                'Média': round(media, 2),
                'M. Básica': round(media_basica, 2),
                'Prob. Ataque (%)': round(prob_ataque, 1),
                'Prob. Vitória (%)': round(prob_vitoria, 1)
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('Prob. Vitória (%)', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de atacantes: {str(e)}"


def analise_recorrencia(ano=2025, clubes_filtro=None, posicao_filtro=None):
    """
    Análise de recorrência similar à BIA:
    - Média nos últimos 3 jogos
    - Média nos últimos 5 jogos
    - Máximo de jogos nos últimos 3/5
    - Percentual de jogos disputados
    """
    if not os.path.exists(HISTORICAL_PLAYERS_PATH):
        return None, "Arquivo de histórico de jogadores não encontrado."
    
    try:
        df_historico = pd.read_csv(HISTORICAL_PLAYERS_PATH)
        clubes_map = carregar_clubes()
        
        # Filtra por ano
        df_players = df_historico[df_historico['ano'] == ano].copy()
        
        if df_players.empty:
            return None, f"Nenhum dado encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            clubes_id_filtro = [k for k, v in clubes_map.items() if v in clubes_filtro]
            df_players = df_players[df_players['clube_id'].isin(clubes_id_filtro)].copy()
        
        # Filtra posição se especificado
        if posicao_filtro:
            # Mapeia número para string
            pos_map = {1: 'gol', 2: 'lat', 3: 'zag', 4: 'mei', 5: 'ata', 6: 'tec'}
            pos_string = pos_map.get(posicao_filtro, posicao_filtro)
            # Aceita tanto string quanto número
            mask_pos = (df_players['posicao_id'] == pos_string) | (df_players['posicao_id'] == posicao_filtro)
            df_players = df_players[mask_pos].copy()
        
        resultados = []
        
        for atleta_id in df_players['atleta_id'].unique():
            df_atleta = df_players[df_players['atleta_id'] == atleta_id].copy()
            
            # Ordena por rodada
            df_atleta = df_atleta.sort_values('rodada').copy()
            
            # Filtra apenas jogos onde jogou (pontuacao > 0)
            df_atleta_jogou = df_atleta[df_atleta['pontuacao'] > 0].copy()
            
            if len(df_atleta_jogou) == 0:
                continue
            
            # Últimos 3 e 5 jogos
            ultimos_3 = df_atleta_jogou.tail(3)
            ultimos_5 = df_atleta_jogou.tail(5)
            
            # Médias
            media_3 = ultimos_3['pontuacao'].mean() if len(ultimos_3) > 0 else 0
            media_5 = ultimos_5['pontuacao'].mean() if len(ultimos_5) > 0 else 0
            
            # Máximo de jogos
            max_3 = len(ultimos_3)
            max_5 = len(ultimos_5)
            
            # Percentual de jogos disputados
            total_rodadas = df_atleta['rodada'].nunique()
            jogos_disputados = len(df_atleta_jogou)
            perc_disputados = (jogos_disputados / total_rodadas * 100) if total_rodadas > 0 else 0
            
            # Últimos 3 jogos (%)
            ultimas_3_rodadas = df_atleta.tail(3)
            jogou_ultimas_3 = len(ultimas_3_rodadas[ultimas_3_rodadas['pontuacao'] > 0])
            perc_ultimas_3 = (jogou_ultimas_3 / 3 * 100) if len(ultimas_3_rodadas) > 0 else 0
            
            nome = df_atleta.iloc[0].get('apelido', 'N/A')
            clube_id = df_atleta.iloc[0].get('clube_id', 0)
            clube_nome = clubes_map.get(clube_id, f'Clube {clube_id}')
            posicao = df_atleta.iloc[0].get('posicao_id', 'N/A')
            status = str(df_atleta.iloc[-1].get('status_id', 'N/A'))  # Status mais recente
            
            # Mapeia posição
            pos_map = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
            pos_nome = pos_map.get(posicao, f'POS {posicao}')
            
            resultados.append({
                'Clube': clube_nome,
                'Jogador': f"{nome} {pos_nome}",
                'Status': status,
                '3 Jogos': round(media_3, 2),
                '5 Jogos': round(media_5, 2),
                'MAX 3': max_3,
                'MAX 5': max_5,
                'Últimos 3 Jogos (%)': round(perc_ultimas_3, 2),
                '% D': round(perc_disputados, 1)
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('3 Jogos', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de recorrência: {str(e)}"


def analise_participacoes_detalhada(ano=2025, clubes_filtro=None, posicao_filtro=None, status_filtro=None, min_jogos=0):
    """
    Análise de participações detalhada similar à BIA Score:
    - JOGOS: Jogos disputados
    - MÉDIA: Média de pontuação
    - M. BASICA: Média básica (sem bônus)
    - ESCANTEIOS/JOGO: Escanteios por jogo (aproximado via scouts disponíveis)
    - XA/JOGO: Expected Assists por jogo (aproximado)
    - XG/JOGO: Expected Goals por jogo (aproximado)
    - ASSISTENCIAS: Total de assistências
    - GOLS: Total de gols
    - G + A: Gols + Assistências
    """
    if not os.path.exists(HISTORICAL_PLAYERS_PATH):
        return None, "Arquivo de histórico de jogadores não encontrado."
    
    try:
        df_historico = pd.read_csv(HISTORICAL_PLAYERS_PATH)
        clubes_map = carregar_clubes()
        
        # Filtra por ano
        df_players = df_historico[df_historico['ano'] == ano].copy()
        
        if df_players.empty:
            return None, f"Nenhum dado encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            clubes_id_filtro = [k for k, v in clubes_map.items() if v in clubes_filtro]
            df_players = df_players[df_players['clube_id'].isin(clubes_id_filtro)].copy()
        
        # Filtra posição se especificado
        if posicao_filtro:
            pos_map = {1: 'gol', 2: 'lat', 3: 'zag', 4: 'mei', 5: 'ata', 6: 'tec'}
            pos_string = pos_map.get(posicao_filtro, posicao_filtro)
            mask_pos = (df_players['posicao_id'] == pos_string) | (df_players['posicao_id'] == posicao_filtro)
            df_players = df_players[mask_pos].copy()
        
        # Filtra status se especificado
        if status_filtro:
            df_players['status_normalizado'] = df_players['status_id'].astype(str).str.lower()
            status_filtro_lower = [s.lower() if isinstance(s, str) else str(s).lower() for s in status_filtro]
            df_players = df_players[df_players['status_normalizado'].isin(status_filtro_lower)].copy()
        
        resultados = []
        
        for atleta_id in df_players['atleta_id'].unique():
            df_atleta = df_players[df_players['atleta_id'] == atleta_id].copy()
            
            # Filtra apenas jogos disputados (pontuacao > 0)
            df_atleta_jogou = df_atleta[df_atleta['pontuacao'] > 0].copy()
            
            jogos = len(df_atleta_jogou)
            
            # Filtra por mínimo de jogos
            if jogos < min_jogos:
                continue
            
            if jogos == 0:
                continue
            
            # MÉDIA: Média geral (inclui jogos com 0 pontos)
            media = df_atleta['pontuacao'].mean()
            
            # M. BASICA: Média apenas dos jogos disputados (sem bônus de capitão, etc)
            media_basica = df_atleta_jogou['pontuacao'].mean()
            
            # ASSISTENCIAS: Total de assistências
            assistencias_total = df_atleta_jogou['A'].sum() if 'A' in df_atleta_jogou.columns and pd.notna(df_atleta_jogou['A']).any() else 0
            
            # GOLS: Total de gols
            gols_total = df_atleta_jogou['G'].sum() if 'G' in df_atleta_jogou.columns and pd.notna(df_atleta_jogou['G']).any() else 0
            
            # G + A: Gols + Assistências
            g_mais_a = gols_total + assistencias_total
            
            # XA/JOGO: Expected Assists por jogo (aproximado)
            # Aproximação: XA ≈ Assistências + (Finalizações Certas * 0.1)
            fs_total = df_atleta_jogou['FS'].sum() if 'FS' in df_atleta_jogou.columns and pd.notna(df_atleta_jogou['FS']).any() else 0
            xa_aproximado = assistencias_total + (fs_total * 0.1)
            xa_por_jogo = xa_aproximado / jogos if jogos > 0 else 0
            
            # XG/JOGO: Expected Goals por jogo (aproximado)
            # Aproximação: XG ≈ Gols + (Finalizações Certas * 0.15) + (Finalizações Fora * 0.05)
            ff_total = df_atleta_jogou['FF'].sum() if 'FF' in df_atleta_jogou.columns and pd.notna(df_atleta_jogou['FF']).any() else 0
            xg_aproximado = gols_total + (fs_total * 0.15) + (ff_total * 0.05)
            xg_por_jogo = xg_aproximado / jogos if jogos > 0 else 0
            
            # ESCANTEIOS/JOGO: Escanteios por jogo
            # Nota: O Cartola não tem scout de escanteios diretamente
            # Aproximação: Para meias/atacantes, podemos usar uma estimativa baseada em finalizações
            # ou deixar como 0.00 se não tivermos dados
            escanteios_por_jogo = 0.00  # Não temos dados de escanteios no Cartola
            
            # Dados do jogador
            nome = df_atleta.iloc[0].get('apelido', 'N/A')
            clube_id = df_atleta.iloc[0].get('clube_id', 0)
            clube_nome = clubes_map.get(clube_id, f'Clube {clube_id}')
            posicao = df_atleta.iloc[0].get('posicao_id', 'N/A')
            status_atual = str(df_atleta.iloc[-1].get('status_id', 'N/A'))
            
            # Mapeia posição
            pos_map_num = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
            pos_map_str = {'gol': 'GOL', 'lat': 'LAT', 'zag': 'ZAG', 'mei': 'MEI', 'ata': 'ATA', 'tec': 'TEC'}
            
            if isinstance(posicao, (int, float)) and not pd.isna(posicao):
                pos_nome = pos_map_num.get(int(posicao), f'POS {int(posicao)}')
            else:
                pos_str = str(posicao).lower()
                pos_nome = pos_map_str.get(pos_str, str(posicao).upper())
            
            resultados.append({
                'Clube': clube_nome,
                'Pos': pos_nome,
                'Nome': nome,
                'Status': status_atual,
                'Jogos': jogos,
                'Média': round(media, 2),
                'M. Básica': round(media_basica, 2),
                'Escanteios/Jogo': round(escanteios_por_jogo, 2),
                'XA/Jogo': round(xa_por_jogo, 2),
                'XG/Jogo': round(xg_por_jogo, 2),
                'Assistências': int(assistencias_total),
                'Gols': int(gols_total),
                'G + A': int(g_mais_a)
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('G + A', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de participações detalhada: {str(e)}"


def analise_participacoes(ano=2025, clubes_filtro=None, posicao_filtro=None, status_filtro=None):
    """
    Análise de participações similar à BIA:
    - Jogos disputados (participações)
    - Total de rodadas disponíveis
    - Percentual de participação
    - Status atual
    - Posição e clube
    """
    if not os.path.exists(HISTORICAL_PLAYERS_PATH):
        return None, "Arquivo de histórico de jogadores não encontrado."
    
    try:
        df_historico = pd.read_csv(HISTORICAL_PLAYERS_PATH)
        clubes_map = carregar_clubes()
        
        # Filtra por ano
        df_players = df_historico[df_historico['ano'] == ano].copy()
        
        if df_players.empty:
            return None, f"Nenhum dado encontrado para o ano {ano}."
        
        # Filtra clubes se especificado
        if clubes_filtro:
            clubes_id_filtro = [k for k, v in clubes_map.items() if v in clubes_filtro]
            df_players = df_players[df_players['clube_id'].isin(clubes_id_filtro)].copy()
        
        # Filtra posição se especificado
        if posicao_filtro:
            pos_map = {1: 'gol', 2: 'lat', 3: 'zag', 4: 'mei', 5: 'ata', 6: 'tec'}
            pos_string = pos_map.get(posicao_filtro, posicao_filtro)
            mask_pos = (df_players['posicao_id'] == pos_string) | (df_players['posicao_id'] == posicao_filtro)
            df_players = df_players[mask_pos].copy()
        
        # Filtra status se especificado
        if status_filtro:
            # Normaliza status para comparação
            df_players['status_normalizado'] = df_players['status_id'].astype(str).str.lower()
            status_filtro_lower = [s.lower() if isinstance(s, str) else str(s).lower() for s in status_filtro]
            df_players = df_players[df_players['status_normalizado'].isin(status_filtro_lower)].copy()
        
        # Conta total de rodadas disponíveis no ano
        total_rodadas_ano = df_players['rodada'].nunique()
        
        resultados = []
        
        for atleta_id in df_players['atleta_id'].unique():
            df_atleta = df_players[df_players['atleta_id'] == atleta_id].copy()
            
            # Ordena por rodada
            df_atleta = df_atleta.sort_values('rodada').copy()
            
            # Jogos disputados (participações) - quando pontuacao > 0
            jogos_disputados = len(df_atleta[df_atleta['pontuacao'] > 0])
            
            # Total de rodadas que o jogador apareceu no mercado
            rodadas_no_mercado = df_atleta['rodada'].nunique()
            
            # Percentual de participação (jogos disputados / rodadas no mercado)
            perc_participacao = (jogos_disputados / rodadas_no_mercado * 100) if rodadas_no_mercado > 0 else 0
            
            # Percentual de participação no ano (jogos disputados / total de rodadas do ano)
            perc_participacao_ano = (jogos_disputados / total_rodadas_ano * 100) if total_rodadas_ano > 0 else 0
            
            # Status mais recente
            status_atual = str(df_atleta.iloc[-1].get('status_id', 'N/A'))
            
            # Dados do jogador
            nome = df_atleta.iloc[0].get('apelido', 'N/A')
            clube_id = df_atleta.iloc[0].get('clube_id', 0)
            clube_nome = clubes_map.get(clube_id, f'Clube {clube_id}')
            posicao = df_atleta.iloc[0].get('posicao_id', 'N/A')
            
            # Mapeia posição (aceita número ou string)
            pos_map_num = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
            pos_map_str = {'gol': 'GOL', 'lat': 'LAT', 'zag': 'ZAG', 'mei': 'MEI', 'ata': 'ATA', 'tec': 'TEC'}
            
            if isinstance(posicao, (int, float)) and not pd.isna(posicao):
                pos_nome = pos_map_num.get(int(posicao), f'POS {int(posicao)}')
            else:
                pos_str = str(posicao).lower()
                pos_nome = pos_map_str.get(pos_str, str(posicao).upper())
            
            resultados.append({
                'Clube': clube_nome,
                'Pos': pos_nome,
                'Nome': nome,
                'Status': status_atual,
                'Jogos': jogos_disputados,
                'Rodadas no Mercado': rodadas_no_mercado,
                'Participação (%)': round(perc_participacao, 1),
                'Participação no Ano (%)': round(perc_participacao_ano, 1),
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('Participação (%)', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        return None, f"Erro ao gerar análise de participações: {str(e)}"


def normalizar_nome(nome):
    """Normaliza nome para comparação (remove acentos, espaços extras, etc.)"""
    if pd.isna(nome) or nome == '':
        return ''
    
    nome = str(nome).strip().lower()
    # Remove acentos
    nome = nome.replace('á', 'a').replace('à', 'a').replace('ã', 'a').replace('â', 'a')
    nome = nome.replace('é', 'e').replace('ê', 'e')
    nome = nome.replace('í', 'i').replace('î', 'i')
    nome = nome.replace('ó', 'o').replace('ô', 'o').replace('õ', 'o')
    nome = nome.replace('ú', 'u').replace('û', 'u')
    nome = nome.replace('ç', 'c')
    # Remove caracteres especiais
    nome = re.sub(r'[^a-z0-9\s]', '', nome)
    # Remove espaços extras
    nome = ' '.join(nome.split())
    return nome


def normalizar_clube(nome_clube):
    """Normaliza nome do clube para comparação"""
    if pd.isna(nome_clube) or nome_clube == '':
        return ''
    
    nome_clube = str(nome_clube).strip().lower()
    # Mapeamentos comuns
    mapeamentos = {
        'atletico mineiro': 'atletico-mg',
        'atlético mineiro': 'atletico-mg',
        'atletico-mineiro': 'atletico-mg',
        'botafogo (rj)': 'botafogo',
        'botafogo rj': 'botafogo',
        'rb bragantino': 'bragantino',
        'red bull bragantino': 'bragantino',
        'sao paulo': 'são paulo',
        'sport recife': 'sport',
    }
    
    for key, value in mapeamentos.items():
        if key in nome_clube:
            return value
    
    return nome_clube


def similaridade_nomes(nome1, nome2):
    """Calcula similaridade entre dois nomes (0-1)"""
    if not nome1 or not nome2:
        return 0.0
    return SequenceMatcher(None, nome1, nome2).ratio()


def safe_int(valor, default=0):
    """Converte valor para inteiro de forma segura, tratando NaN."""
    if pd.isna(valor):
        return default
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return default


def analise_combinada_cartola_fbref(ano=2025, clubes_filtro=None, posicao_filtro=None, status_filtro=None, min_jogos=0):
    """
    Combina dados do Cartola FC com dados do FBref para análise estatística completa.
    
    Retorna DataFrame com:
    - CLUBE, POS, NOME
    - JOGOS (do Cartola)
    - MÉDIA, M. BÁSICA (do Cartola)
    - ESCANTEIOS/JOGO, XA/JOGO, XG/JOGO (do FBref)
    - ASSISTÊNCIAS, GOLS, G + A (do FBref)
    """
    try:
        # Caminhos dos arquivos
        FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")
        
        # Verifica se arquivo do FBref existe
        if not os.path.exists(FBREF_JOGADORES_PATH):
            return None, "Arquivo de dados do FBref não encontrado. Execute o script de coleta primeiro."
        
        # Carrega dados do Cartola
        if not os.path.exists(HISTORICAL_PLAYERS_PATH):
            return None, "Arquivo de histórico de jogadores não encontrado."
        
        df_cartola = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
        # historico_2025.csv já está filtrado para 2025, mas mantém filtro para compatibilidade
        if 'ano' in df_cartola.columns:
            df_cartola = df_cartola[df_cartola['ano'] == ano].copy()
        
        if df_cartola.empty:
            return None, f"Nenhum dado do Cartola encontrado para o ano {ano}."
        
        # Converte clube_id para inteiro antes de qualquer processamento
        df_cartola['clube_id'] = pd.to_numeric(df_cartola['clube_id'], errors='coerce').fillna(0).astype(int)
        
        # Carrega dados do FBref (arquivo já está limpo, sem cabeçalhos duplicados)
        df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)
        
        # Remove linhas vazias ou inválidas
        if 'Player' in df_fbref.columns:
            df_fbref = df_fbref[df_fbref['Player'].notna()].copy()
            df_fbref = df_fbref[df_fbref['Player'] != 'Player'].copy()  # Remove cabeçalho se ainda existir
            df_fbref = df_fbref[df_fbref['Player'] != ''].copy()
        
        # Renomeia colunas do FBref para português
        # O arquivo limpo pode ter colunas com sufixos (.1) devido a duplicatas no HTML original
        # Estratégia: tenta coluna original primeiro, depois coluna com sufixo
        
        colunas_necessarias = {
            'Nome_FBref': ['Player'],
            'Clube_FBref': ['Clube'],
            'Jogos_FBref': ['MP'],  # Matches Played - número oficial de jogos
            'Starts_FBref': ['Starts'],  # Jogos como titular
            'Gols_FBref': ['Gls', 'Gls.1'],
            'Assistencias_FBref': ['Ast', 'Ast.1'],
            'G_mais_A_FBref': ['G+A', 'G+A.1'],
            'xG_FBref': ['xG.1', 'xG'],  # Prioriza xG.1 (por jogo) sobre xG (total)
            'xAG_FBref': ['xAG.1', 'xAG'],  # Prioriza xAG.1 (por jogo) sobre xAG (total)
            'Posicao_FBref': ['Pos'],
            'Minutos_90s_FBref': ['90s'],
        }
        
        colunas_selecionadas = []
        colunas_renomeadas = {}
        
        # Procura cada coluna necessária
        for nome_final, possiveis_nomes in colunas_necessarias.items():
            for nome_possivel in possiveis_nomes:
                if nome_possivel in df_fbref.columns:
                    colunas_selecionadas.append(nome_possivel)
                    colunas_renomeadas[nome_possivel] = nome_final
                    break
        
        # Adiciona coluna Clube (já foi criada pelo script de limpeza)
        if 'Clube' in df_fbref.columns and 'Clube' not in colunas_selecionadas:
            colunas_selecionadas.append('Clube')
            colunas_renomeadas['Clube'] = 'Clube_FBref'
        
        if 'URL_Clube' in df_fbref.columns:
            colunas_selecionadas.append('URL_Clube')
        
        if not colunas_selecionadas:
            return None, "Nenhuma coluna relevante encontrada no arquivo FBref."
        
        df_fbref_clean = df_fbref[colunas_selecionadas].copy()
        df_fbref_clean = df_fbref_clean.rename(columns=colunas_renomeadas)
        
        # DEBUG: Verifica se Jogos_FBref foi renomeada corretamente
        if 'Jogos_FBref' not in df_fbref_clean.columns:
            # Tenta encontrar a coluna original MP se não foi renomeada
            if 'MP' in df_fbref_clean.columns:
                df_fbref_clean['Jogos_FBref'] = df_fbref_clean['MP']
            else:
                return None, "Coluna 'Jogos_FBref' (MP) não encontrada após processamento."
        
        # Normaliza nomes e clubes para matching
        if 'Nome_FBref' in df_fbref_clean.columns:
            df_fbref_clean['Nome_Normalizado'] = df_fbref_clean['Nome_FBref'].apply(normalizar_nome)
        elif 'Player' in df_fbref_clean.columns:
            df_fbref_clean['Nome_FBref'] = df_fbref_clean['Player']
            df_fbref_clean['Nome_Normalizado'] = df_fbref_clean['Player'].apply(normalizar_nome)
        else:
            return None, "Coluna de nome do jogador não encontrada no arquivo FBref."
        
        if 'Clube_FBref' in df_fbref_clean.columns:
            df_fbref_clean['Clube_Normalizado'] = df_fbref_clean['Clube_FBref'].apply(normalizar_clube)
        elif 'Clube' in df_fbref_clean.columns:
            df_fbref_clean['Clube_FBref'] = df_fbref_clean['Clube']
            df_fbref_clean['Clube_Normalizado'] = df_fbref_clean['Clube'].apply(normalizar_clube)
        else:
            return None, "Coluna de clube não encontrada no arquivo FBref."
        
        # Agrega dados do Cartola por jogador
        clubes_map = carregar_clubes()
        clubes_map_fantasia = carregar_clubes_nome_fantasia()
        
        # Adiciona nome do clube ao DataFrame do Cartola (clube_id já foi convertido acima)
        df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia).fillna('')
        
        # Remove duplicatas de rodada por jogador (caso o jogador tenha mudado de clube na mesma rodada)
        # Mantém apenas a primeira ocorrência de cada rodada por jogador
        df_cartola = df_cartola.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
        
        # JOGOS: Conta TODAS as rodadas únicas onde o jogador aparece (mesmo com pontuacao = 0)
        # MÉDIA: Soma da pontuacao dividida pelo número total de rodadas onde apareceu
        # IMPORTANTE: Agrupa apenas por atleta_id e apelido para não separar jogadores que mudaram de clube
        # Depois pega o clube mais recente (última rodada) para exibição
        df_cartola_agg = df_cartola.groupby(['atleta_id', 'apelido']).agg({
            'rodada': 'nunique',  # Conta TODAS as rodadas únicas onde apareceu
            'pontuacao': ['sum', 'mean'],  # sum = soma total (inclui 0), mean = média (inclui 0)
            'G': 'sum',
            'A': 'sum',
            'FS': 'sum',
            'FF': 'sum',
            'posicao_id': 'first',  # Pega a primeira posição (geralmente não muda)
        }).reset_index()
        
        # Pega o clube mais recente (última rodada) de cada jogador
        df_cartola_ultimo_clube = df_cartola.sort_values('rodada').groupby(['atleta_id', 'apelido']).last()[['clube_id', 'clube_nome']].reset_index()
        
        df_cartola_agg.columns = ['atleta_id', 'Nome_Cartola', 
                                   'Jogos_Cartola', 'Pontuacao_Total', 'Media_Cartola', 
                                   'Gols_Cartola', 'Assistencias_Cartola', 'FS_Cartola', 'FF_Cartola', 'posicao_id']
        
        # Merge com o clube mais recente (usa apenas atleta_id, pois apelido foi renomeado para Nome_Cartola)
        df_cartola_agg = df_cartola_agg.merge(df_cartola_ultimo_clube[['atleta_id', 'clube_id', 'clube_nome']], 
                                               on='atleta_id', how='left')
        
        # Reordena colunas
        df_cartola_agg = df_cartola_agg[['atleta_id', 'Nome_Cartola', 'clube_id', 'clube_nome', 'posicao_id',
                                         'Jogos_Cartola', 'Pontuacao_Total', 'Media_Cartola', 
                                         'Gols_Cartola', 'Assistencias_Cartola', 'FS_Cartola', 'FF_Cartola']]
        
        # Renomeia clube_nome para Clube_Cartola para manter compatibilidade
        df_cartola_agg['Clube_Cartola'] = df_cartola_agg['clube_nome']
        
        # Recalcula MÉDIA corretamente: soma(pontuacao) / numero_total_rodadas_onde_apareceu
        # Isso inclui rodadas com pontuacao = 0
        df_cartola_agg['Media_Cartola'] = df_cartola_agg['Pontuacao_Total'] / df_cartola_agg['Jogos_Cartola']
        
        # Calcula média básica (sem bônus de gols e assistências)
        # Nova fórmula: ((SOMA da pontuação) - (soma de pontos por gols + soma de pontos por assistência)) / total de jogos
        # Onde: pontos por gols = G * 8, pontos por assistência = A * 5
        # Total de jogos = todas as rodadas onde apareceu (incluindo pontuacao = 0)
        
        # Garante que Gols e Assistencias não sejam NaN
        df_cartola_agg['Gols_Cartola'] = df_cartola_agg['Gols_Cartola'].fillna(0)
        df_cartola_agg['Assistencias_Cartola'] = df_cartola_agg['Assistencias_Cartola'].fillna(0)
        
        df_cartola_agg['Media_Basica_Cartola'] = (
            df_cartola_agg['Pontuacao_Total'] - 
            (df_cartola_agg['Gols_Cartola'] * 8 + df_cartola_agg['Assistencias_Cartola'] * 5)
        ) / df_cartola_agg['Jogos_Cartola']
        
        # Garante que não há valores negativos ou NaN
        df_cartola_agg['Media_Basica_Cartola'] = df_cartola_agg['Media_Basica_Cartola'].fillna(0)
        
        # Normaliza nomes e clubes do Cartola
        df_cartola_agg['Nome_Normalizado'] = df_cartola_agg['Nome_Cartola'].apply(normalizar_nome)
        df_cartola_agg['Clube_Normalizado'] = df_cartola_agg['Clube_Cartola'].apply(normalizar_clube)
        
        # Faz matching entre Cartola e FBref
        resultados = []
        erros_count = 0
        
        for idx, row_cartola in df_cartola_agg.iterrows():
            try:
                nome_cartola_norm = row_cartola['Nome_Normalizado']
                clube_cartola_norm = row_cartola['Clube_Normalizado']
                
                # Procura match no FBref (primeiro por clube, depois sem filtro de clube)
                df_match = df_fbref_clean[
                    (df_fbref_clean['Clube_Normalizado'] == clube_cartola_norm)
                ].copy()
                
                # Se não encontrou no mesmo clube, tenta sem filtro de clube
                if df_match.empty:
                    df_match = df_fbref_clean.copy()
                
                melhor_match = pd.DataFrame()  # Inicializa vazio
                
                # Só calcula similaridade se houver candidatos
                if not df_match.empty:
                    # Calcula similaridade de nomes
                    df_match['Similaridade'] = df_match['Nome_Normalizado'].apply(
                        lambda x: similaridade_nomes(nome_cartola_norm, x)
                    )
                    
                    # Pega o melhor match (similaridade > 0.7, mas se não encontrar, tenta o melhor disponível)
                    melhor_match = df_match[df_match['Similaridade'] > 0.7].nlargest(1, 'Similaridade')
                    
                    # Se não encontrou match com similaridade > 0.7, tenta o melhor disponível (similaridade > 0.5)
                    if melhor_match.empty:
                        melhor_match = df_match[df_match['Similaridade'] > 0.5].nlargest(1, 'Similaridade')
                
                # SEMPRE usa número de jogos do Cartola (rodadas onde pontuacao > 0)
                # NÃO substitui pelo valor do FBref, pois queremos consistência com MÉDIA e M. BÁSICA
                jogos_cartola = int(row_cartola.get('Jogos_Cartola', 0))
                
                # Inicializa variáveis do FBref
                xag_valor = 0
                xg_valor = 0
                assistencias_fbref = 0
                gols_fbref = 0
                g_mais_a_fbref = 0
                
                # Se encontrou match no FBref, usa dados do FBref (mas NÃO substitui jogos_cartola)
                jogos_fbref = 0  # Inicializa MP do FBref
                
                if not melhor_match.empty:
                    row_fbref = melhor_match.iloc[0]
                    
                    # Pega MP do FBref (Matches Played) para calcular XA/jogo e XG/jogo
                    try:
                        if 'Jogos_FBref' in row_fbref.index:
                            jogos_fbref = safe_int(row_fbref['Jogos_FBref'])
                        elif 'MP' in row_fbref.index:
                            jogos_fbref = safe_int(row_fbref['MP'])
                    except Exception:
                        jogos_fbref = 0
                    
                    # XA/Jogo e XG/Jogo do FBref (xAG.1 e xG.1 já são valores por jogo)
                    try:
                        xa_jogo = pd.to_numeric(row_fbref['xAG_FBref'], errors='coerce') or 0
                    except (KeyError, IndexError):
                        xa_jogo = 0
                    try:
                        xg_jogo = pd.to_numeric(row_fbref['xG_FBref'], errors='coerce') or 0
                    except (KeyError, IndexError):
                        xg_jogo = 0
                    
                    # Assistencias, Gols e G+A do FBref
                    assistencias_fbref = safe_int(row_fbref['Assistencias_FBref'] if 'Assistencias_FBref' in row_fbref.index else 0)
                    gols_fbref = safe_int(row_fbref['Gols_FBref'] if 'Gols_FBref' in row_fbref.index else 0)
                    g_mais_a_fbref = safe_int(row_fbref['G_mais_A_FBref'] if 'G_mais_A_FBref' in row_fbref.index else 0)
                else:
                    # Sem match no FBref, inicializa variáveis como 0
                    xa_jogo = 0
                    xg_jogo = 0
                    assistencias_fbref = 0
                    gols_fbref = 0
                    g_mais_a_fbref = 0
                
                # Escanteios/Jogo (aproximação usando FS e FF do Cartola)
                escanteios_jogo = 0.0  # Não temos dados diretos de escanteios do FBref
                
                # Mapeia posição (trata casos onde posicao_id pode ser NaN ou inválido)
                try:
                    posicao_id_int = int(row_cartola['posicao_id']) if pd.notna(row_cartola['posicao_id']) else 0
                except (ValueError, TypeError):
                    posicao_id_int = 0
                
                pos_map = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
                posicao = pos_map.get(posicao_id_int, 'OUT')
                
                # Adiciona resultado (inclui jogador mesmo sem match no FBref)
                resultados.append({
                    'CLUBE': row_cartola['Clube_Cartola'],
                    'POS': posicao,
                    'NOME': row_cartola['Nome_Cartola'],
                    'JOGOS': int(jogos_cartola),  # Total de rodadas únicas onde apareceu (inclui pontuacao = 0) no historico_2025.csv
                    'MÉDIA': round(row_cartola['Media_Cartola'], 2),  # Soma(pontuacao) / total_rodadas_onde_apareceu (inclui 0)
                    'M. BÁSICA': round(row_cartola['Media_Basica_Cartola'], 2),  # Média de (pontuacao - G*8 - A*5) apenas onde pontuacao > 0
                    'ESCANTEIOS/JOGO': round(escanteios_jogo, 2),
                    'XA/JOGO': round(xa_jogo, 3),
                    'XG/JOGO': round(xg_jogo, 3),
                    'ASSISTÊNCIAS': assistencias_fbref,
                    'GOLS': gols_fbref,
                    'G + A': g_mais_a_fbref,
                })
            except Exception as e:
                # Se houver erro ao processar um jogador, continua com os outros
                erros_count += 1
                continue
        
        if not resultados:
            return None, "Nenhum match encontrado entre dados do Cartola e FBref."
        
        df_resultado = pd.DataFrame(resultados)
        
        # Aplica filtros
        if clubes_filtro:
            df_resultado = df_resultado[df_resultado['CLUBE'].isin(clubes_filtro)].copy()
        
        if posicao_filtro:
            df_resultado = df_resultado[df_resultado['POS'] == posicao_filtro].copy()
        
        # Aplica filtro de mínimo de jogos (mas não remove jogadores com 0 jogos se min_jogos for 0)
        if min_jogos > 0:
            df_resultado = df_resultado[df_resultado['JOGOS'] >= min_jogos].copy()
        
        # Ordena por média
        df_resultado = df_resultado.sort_values('MÉDIA', ascending=False)
        
        return df_resultado, None
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"Erro ao combinar dados: {str(e)}"

