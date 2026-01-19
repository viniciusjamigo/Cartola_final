import pandas as pd
import os
import requests
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PARTIDAS_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")

# Base URL do repositório caRtola
BASE_URL = "https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/{ano}/{arquivo}"

def baixar_partidas(anos=[2022, 2023, 2024, 2025]):
    """Baixa histórico de partidas (quem x quem) do Github."""
    dfs = []
    
    for ano in anos:
        print(f"Baixando partidas de {ano}...")
        # O nome do arquivo varia as vezes. Tenta 'partidas.csv' ou 'matches.csv'
        for nome_arq in ['partidas.csv', 'matches.csv']:
            url = BASE_URL.format(ano=ano, arquivo=nome_arq)
            try:
                df = pd.read_csv(url)
                df['ano'] = ano
                
                # Padronização de colunas
                # Esperado: home_team, away_team, round, date, home_score, away_score
                # Às vezes vem como 'home_team_id', etc.
                
                rename_map = {
                    'home_team': 'mandante_id', 'home_team_id': 'mandante_id',
                    'away_team': 'visitante_id', 'away_team_id': 'visitante_id',
                    'round': 'rodada',
                    'home_score': 'placar_mandante',
                    'away_score': 'placar_visitante'
                }
                df.rename(columns=rename_map, inplace=True)
                
                # Seleciona colunas de interesse
                cols = ['ano', 'rodada', 'mandante_id', 'visitante_id', 'placar_mandante', 'placar_visitante']
                cols_existentes = [c for c in cols if c in df.columns]
                
                if 'mandante_id' in df.columns and 'visitante_id' in df.columns:
                    dfs.append(df[cols_existentes])
                    print(f" - Sucesso ({len(df)} jogos)")
                    break # Achou arquivo, pula pro proximo ano
            except:
                continue
                
    if dfs:
        df_final = pd.concat(dfs, ignore_index=True)
        # Garante tipos
        for col in ['mandante_id', 'visitante_id', 'rodada', 'ano']:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0).astype(int)
        
        # --- LÓGICA DE ATUALIZAÇÃO ---
        # 1. Carrega dados existentes, se houver
        if os.path.exists(PARTIDAS_PATH):
            print("Atualizando arquivo existente...")
            df_existente = pd.read_csv(PARTIDAS_PATH)
            # 2. Concatena o novo com o antigo
            df_consolidado = pd.concat([df_existente, df_final], ignore_index=True)
            # 3. Remove duplicatas, mantendo os dados antigos como prioridade
            df_consolidado.drop_duplicates(subset=['ano', 'rodada', 'mandante_id'], keep='first', inplace=True)
            # 4. Ordena para manter o arquivo organizado
            df_consolidado.sort_values(['ano', 'rodada'], inplace=True)
            df_final = df_consolidado
        
        df_final.to_csv(PARTIDAS_PATH, index=False)
        print(f"Arquivo salvo em {PARTIDAS_PATH}. Total de {len(df_final)} partidas.")
        return df_final
    else:
        print("Nenhum dado de partidas encontrado.")
        return None

if __name__ == "__main__":
    # Roda para os anos que o diagnóstico apontou como faltantes
    baixar_partidas(anos=[2018, 2019, 2020])

