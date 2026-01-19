import pandas as pd
import json
import os
from collections import Counter

# --- Caminhos (copiado de modelagem.py para consistência) ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
CLUBS_JSON_PATH = os.path.join(DATA_DIR, "clubes.json")

def diagnosticar_mapeamento_clubes():
    """
    Identifica quais abreviações de clubes no histórico de jogadores não
    estão sendo mapeadas para um ID numérico.
    """
    print("--- INICIANDO DIAGNÓSTICO DE MAPEAMENTO DE CLUBES ---")

    # 1. Carregar o histórico de jogadores
    if not os.path.exists(HISTORICAL_DATA_PATH):
        print(f"Erro: Arquivo de histórico não encontrado em {HISTORICAL_DATA_PATH}")
        return
    
    try:
        # Carrega apenas a coluna necessária para otimizar a memória
        df_hist = pd.read_csv(HISTORICAL_DATA_PATH, usecols=['clube_id'], low_memory=False)
        # Remove valores nulos e converte para string para garantir consistência
        df_hist.dropna(subset=['clube_id'], inplace=True)
        # Filtra entradas que já são puramente numéricas
        club_ids_texto = df_hist[df_hist['clube_id'].astype(str).str.isalpha()]['clube_id'].unique()
        print(f"Encontrados {len(club_ids_texto)} IDs de clubes em formato de texto (abreviações).")
    except Exception as e:
        print(f"Erro ao ler o arquivo histórico: {e}")
        return

    # 2. Construir o mapa de IDs (lógica de modelagem.py)
    mapa_abbr_id = {}
    if os.path.exists(CLUBS_JSON_PATH):
        with open(CLUBS_JSON_PATH, 'r', encoding='utf8') as f:
            clubes_json = json.load(f)
            
        for cid, dados in clubes_json.items():
            if 'abreviacao' in dados:
                mapa_abbr_id[dados['abreviacao']] = int(cid)
            if 'nome' in dados:
                mapa_abbr_id[dados['nome']] = int(cid)
    else:
        print(f"Aviso: Arquivo de clubes não encontrado em {CLUBS_JSON_PATH}")
    
    # Adicionar mapeamentos manuais
    manual_map = {
        'AME': 327, 'ATL': 282, 'ATM': 282, 'CAM': 282,
        'CAP': 293, 'PAR': 293, 'ATP': 293,
        'AVA': 314, 'CHA': 315, 'CSA': 373, 'CTB': 294, 'CFC': 294,
        'GOI': 290, 'ACG': 373, 'CUI': 1371,
        'RED': 280, 'RBB': 280, 'BRA': 280,
        'SPO': 292 # Adicionado mapeamento para o Sport
    }
    mapa_abbr_id.update(manual_map)
    print(f"Mapa de IDs construído com {len(mapa_abbr_id)} entradas.")

    # 3. Identificar clubes não mapeados
    nao_mapeados = []
    for abbr in club_ids_texto:
        if abbr not in mapa_abbr_id:
            nao_mapeados.append(abbr)
    
    if not nao_mapeados:
        print("\n--- RESULTADO ---")
        print("Sucesso! Todas as abreviacoes de clubes encontradas no historico foram mapeadas.")
        return

    print("\n--- RESULTADO: CLUBES NAO MAPEADOS ---")
    print(f"Encontradas {len(nao_mapeados)} abreviacoes de clubes que nao possuem um ID correspondente no mapa.")
    
    # 4. Contar a frequência
    # Recarrega a coluna para contar a frequência de ocorrência
    all_abbrs = df_hist[df_hist['clube_id'].astype(str).str.isalpha()]['clube_id']
    contagem = Counter(abbr for abbr in all_abbrs if abbr in nao_mapeados)
    
    print("\nFrequência das abreviações não mapeadas (ordem decrescente):")
    for abbr, count in contagem.most_common():
        print(f"- {abbr}: {count} ocorrências")

if __name__ == "__main__":
    diagnosticar_mapeamento_clubes()
