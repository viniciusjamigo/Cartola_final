import pandas as pd
import os
import json
import numpy as np

# --- CAMINHOS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual.csv")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual_processada.csv")
CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")
MATCHES_DATA_PATH = os.path.join(DATA_DIR, "partidas_rodada.csv")
ODDS_DATA_PATH = os.path.join(DATA_DIR, "odds_rodada.csv")
HISTORICO_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv") # Para calcular volatilidade

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
    """Calcula o desvio padrão das pontuações de 2025."""
    if not os.path.exists(HISTORICO_2025_PATH):
        return {}
    
    try:
        df = pd.read_csv(HISTORICO_2025_PATH)
        # Desvio padrão por atleta
        volatilidade = df.groupby('atleta_id')['pontuacao'].std().to_dict()
        return volatilidade
    except Exception:
        return {}

def preprocessar_dados_rodada(alpha=0.2):
    try:
        # --- 1. Carregar dados ---
        df_jogadores_raw = pd.read_csv(RAW_DATA_PATH)
        df_partidas = pd.read_csv(MATCHES_DATA_PATH)
        with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes_map_str = json.load(f)
            clubes_map = {int(k): v for k, v in clubes_map_str.items()}

        df_jogadores = df_jogadores_raw[df_jogadores_raw['status'] == 'Provável'].copy()
        
        # Garante IDs numéricos
        df_jogadores['clube_id'] = pd.to_numeric(df_jogadores['clube_id'], errors='coerce').fillna(0).astype(int)
        
        # --- 2. Adversário e Casa ---
        # Carregamos o mapa de IDs para Nomes (ex: 262 -> 'Flamengo')
        id_para_nome = {clube_id: detalhes['nome_fantasia'] for clube_id, detalhes in clubes_map.items()}
        
        # DEBUG: Verifica se o mapeamento está funcionando
        print("\n--- DEBUG PREPROCESSAMENTO ---")
        if not df_jogadores.empty:
            exemplo_id = df_jogadores['clube_id'].iloc[0]
            exemplo_nome = id_para_nome.get(exemplo_id, "NÃO ENCONTRADO")
            print(f"Teste de Mapeamento: ID {exemplo_id} -> {exemplo_nome}")
        
        df_jogadores['clube'] = df_jogadores['clube_id'].map(id_para_nome) 
        
        partidas_info = {}
        jogos_proc = 0
        
        # Importante: Precisamos garantir que 'clube_casa_id' e 'clube_visitante_id' sejam inteiros para bater com o mapa
        # E precisamos verificar se o nome do clube bate com o que está em 'df_jogadores['clube']'
        
        for _, row in df_partidas.iterrows():
            try:
                c_casa_id = int(row['clube_casa_id'])
                c_vis_id = int(row['clube_visitante_id'])
                
                # Usa o MESMO mapa que usamos para os jogadores
                clube_casa_nome = id_para_nome.get(c_casa_id)
                clube_visitante_nome = id_para_nome.get(c_vis_id)
                
                if clube_casa_nome and clube_visitante_nome:
                    # Mapeia pelo NOME DO CLUBE, pois é isso que está na coluna 'clube' de df_jogadores
                    partidas_info[clube_casa_nome] = {
                        'adversario': clube_visitante_nome, 
                        'adversario_id': c_vis_id,
                        'fator_casa': 1
                    }
                    partidas_info[clube_visitante_nome] = {
                        'adversario': clube_casa_nome, 
                        'adversario_id': c_casa_id,
                        'fator_casa': -1
                    }
                    jogos_proc += 1
            except Exception:
                continue
                
        print(f"  > Processamento de Partidas: {jogos_proc} jogos mapeados.")
        
        # Aplica o mapeamento usando o NOME do clube como chave
        df_jogadores['adversario'] = df_jogadores['clube'].map(lambda x: partidas_info.get(x, {}).get('adversario', 'N/A'))
        df_jogadores['adversario_id'] = df_jogadores['clube'].map(lambda x: partidas_info.get(x, {}).get('adversario_id', 0))
        df_jogadores['fator_casa'] = df_jogadores['clube'].map(lambda x: partidas_info.get(x, {}).get('fator_casa', 0))
        
        # DEBUG FINAL
        qtd_casa = (df_jogadores['fator_casa'] == 1).sum()
        qtd_fora = (df_jogadores['fator_casa'] == -1).sum()
        print(f"  > Jogadores em Casa: {qtd_casa} | Jogadores Fora: {qtd_fora}")
        print("------------------------------\n")

        # --- 3. Features Táticas ---
        df_jogadores['adversario_forca_def'] = df_jogadores['adversario'].apply(lambda x: get_forca(x, 'def'))
        df_jogadores['adversario_forca_of'] = df_jogadores['adversario'].apply(lambda x: get_forca(x, 'of'))
        
        # --- 4. Volatilidade (NOVO) ---
        mapa_volatilidade = calcular_volatilidade()
        # Se não tiver histórico (jogador novo), assume um desvio padrão médio (ex: 2.0)
        df_jogadores['volatilidade'] = df_jogadores['atleta_id'].map(mapa_volatilidade).fillna(2.0)

        # --- 5. Juntar com Odds (Se existirem) ---
        if os.path.exists(ODDS_DATA_PATH):
            df_odds = pd.read_csv(ODDS_DATA_PATH)
            
            df_merged = df_jogadores.merge(
                df_odds, 
                left_on=['clube', 'adversario'], 
                right_on=['time_casa', 'time_visitante'], 
                how='left'
            )
            
            df_merged_visitante = df_jogadores.merge(
                df_odds,
                left_on=['clube', 'adversario'],
                right_on=['time_visitante', 'time_casa'],
                how='left'
            )

            df_merged['odd_casa'].fillna(df_merged_visitante['odd_casa'], inplace=True)
            df_merged['odd_empate'].fillna(df_merged_visitante['odd_empate'], inplace=True)
            df_merged['odd_visitante'].fillna(df_merged_visitante['odd_visitante'], inplace=True)
            
            df_merged['odd_vitoria'] = np.where(df_merged['fator_casa'] == 1, df_merged['odd_casa'], df_merged['odd_visitante'])
            df_merged['odd_derrota'] = np.where(df_merged['fator_casa'] == 1, df_merged['odd_visitante'], df_merged['odd_casa'])
            
            df_jogadores = df_merged

            # Calcular Probabilidades para o Modo Clássico
            jogadores_com_odds = df_jogadores['odd_vitoria'].notna().sum()
            if jogadores_com_odds > 0:
                df_jogadores['soma_inverso_odds'] = (1/df_jogadores['odd_vitoria']) + (1/df_jogadores['odd_empate']) + (1/df_jogadores['odd_derrota'])
                df_jogadores['prob_vitoria'] = (1/df_jogadores['odd_vitoria']) / df_jogadores['soma_inverso_odds']
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
        
        # Custo benefício
        df_final['custo_beneficio'] = np.divide(
            df_final['pontuacao_prevista'],
            df_final['preco_num'],
            out=np.zeros_like(df_final['pontuacao_prevista'], dtype=float),
            where=(df_final['preco_num'] != 0)
        )
        
        df_final.replace([np.inf, -np.inf], np.nan, inplace=True)
        df_final.fillna(0, inplace=True)
        
        df_final.to_csv(PROCESSED_DATA_PATH, index=False, encoding='utf-8-sig')
        return df_final

    except FileNotFoundError as e:
        print(f"Erro: Arquivo de dados não encontrado: {e}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        return None

if __name__ == '__main__':
    preprocessar_dados_rodada()
