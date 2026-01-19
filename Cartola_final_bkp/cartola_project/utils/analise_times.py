import pandas as pd
import os
import numpy as np

# --- CAMINHOS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_MATCHES_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")
TEAM_STATS_PATH = os.path.join(DATA_DIR, "estatisticas_times.csv")
CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")

def gerar_estatisticas_times():
    """
    Gera um arquivo com estatísticas agregadas dos times baseadas no histórico de partidas.
    """
    print("Gerando estatísticas consolidadas dos times...")
    
    if not os.path.exists(HISTORICAL_MATCHES_PATH):
        print(f"Erro: Arquivo {HISTORICAL_MATCHES_PATH} não encontrado.")
        return None

    try:
        df_partidas = pd.read_csv(HISTORICAL_MATCHES_PATH)
        
        # Filtra para usar os últimos 2 anos (ano atual e anterior) para estatísticas mais robustas
        ano_atual = df_partidas['ano'].max()
        anos_considerados = [ano_atual, ano_atual - 1]
        print(f"Calculando estatísticas com base nos anos: {anos_considerados}")
        df_partidas = df_partidas[df_partidas['ano'].isin(anos_considerados)].copy()
        
        if df_partidas.empty:
            print(f"Aviso: Nenhum dado de partida encontrado para os anos {anos_considerados}.")
            return None

        stats = {}

        def update_stats(team_id, gols_pro, gols_contra, is_home):
            if team_id not in stats:
                stats[team_id] = {
                    'jogos': 0, 'vitorias': 0, 'empates': 0, 'derrotas': 0,
                    'gols_pro': 0, 'gols_contra': 0,
                    'mandante_jogos': 0, 'mandante_vitorias': 0, 'mandante_derrotas': 0,
                    'visitante_jogos': 0, 'visitante_vitorias': 0, 'visitante_derrotas': 0
                }
            
            s = stats[team_id]
            s['jogos'] += 1
            s['gols_pro'] += gols_pro
            s['gols_contra'] += gols_contra
            
            resultado = 'E'
            if gols_pro > gols_contra: resultado = 'V'
            elif gols_pro < gols_contra: resultado = 'D'
            
            if resultado == 'V': s['vitorias'] += 1
            elif resultado == 'D': s['derrotas'] += 1
            else: s['empates'] += 1
            
            if is_home:
                s['mandante_jogos'] += 1
                if resultado == 'V': s['mandante_vitorias'] += 1
                elif resultado == 'D': s['mandante_derrotas'] += 1
            else:
                s['visitante_jogos'] += 1
                if resultado == 'V': s['visitante_vitorias'] += 1
                elif resultado == 'D': s['visitante_derrotas'] += 1

        for _, row in df_partidas.iterrows():
            mandante = row['mandante_id']
            visitante = row['visitante_id']
            placar_m = row['placar_mandante']
            placar_v = row['placar_visitante']
            
            if pd.isna(placar_m) or pd.isna(placar_v):
                continue
                
            update_stats(mandante, placar_m, placar_v, True)
            update_stats(visitante, placar_v, placar_m, False)
            
        # Converter para DataFrame
        dados_finais = []
        for team_id, s in stats.items():
            # Médias
            media_gp = s['gols_pro'] / s['jogos'] if s['jogos'] > 0 else 0
            media_gc = s['gols_contra'] / s['jogos'] if s['jogos'] > 0 else 0
            aproveitamento = (s['vitorias'] * 3 + s['empates']) / (s['jogos'] * 3) if s['jogos'] > 0 else 0
            
            row = {
                'clube_id': team_id,
                'jogos': s['jogos'],
                'aproveitamento': round(aproveitamento * 100, 2),
                'media_gols_feitos': round(media_gp, 2),
                'media_gols_sofridos': round(media_gc, 2),
                'total_gols_feitos': s['gols_pro'],
                'total_gols_sofridos': s['gols_contra'],
                'vitorias_mandante': s['mandante_vitorias'],
                'derrotas_mandante': s['mandante_derrotas'],
                'vitorias_visitante': s['visitante_vitorias'],
                'derrotas_visitante': s['visitante_derrotas']
            }
            dados_finais.append(row)
            
        df_stats = pd.DataFrame(dados_finais)
        
        # Adicionar nome do clube se disponível
        if os.path.exists(CLUBS_DATA_PATH):
            import json
            with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                clubes = json.load(f)
                # O json mapeia ID string -> dados. Converter keys para int.
                clubes_map = {int(k): v['nome'] for k, v in clubes.items()}
                df_stats['clube_nome'] = df_stats['clube_id'].map(clubes_map)
        
        df_stats.to_csv(TEAM_STATS_PATH, index=False)
        print(f"Estatísticas de times salvas em {TEAM_STATS_PATH}")
        return df_stats

    except Exception as e:
        print(f"Erro ao gerar estatísticas de times: {e}")
        return None

if __name__ == "__main__":
    gerar_estatisticas_times()

