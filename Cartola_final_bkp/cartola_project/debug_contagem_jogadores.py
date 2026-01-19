# -*- coding: utf-8 -*-
"""Script para debugar contagem de jogadores na análise combinada."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv")

print("="*70)
print("DEBUG: Contagem de jogadores na análise combinada")
print("="*70)

# Carrega dados do Cartola
df_cartola = pd.read_csv(HISTORICAL_2025_PATH, low_memory=False)
print(f"\n1. Total de registros no historico_2025.csv: {len(df_cartola)}")

# Remove duplicatas
df_cartola = df_cartola.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
print(f"2. Após remover duplicatas: {len(df_cartola)}")

# Filtra apenas onde pontuacao > 0
df_cartola_jogou = df_cartola[df_cartola['pontuacao'] > 0].copy()
print(f"3. Onde pontuacao > 0: {len(df_cartola_jogou)}")

# Agrega por jogador
from utils.analise_estatisticas import carregar_clubes_nome_fantasia
clubes_map_fantasia = carregar_clubes_nome_fantasia()
df_cartola_jogou['clube_id'] = pd.to_numeric(df_cartola_jogou['clube_id'], errors='coerce').fillna(0).astype(int)
df_cartola_jogou['clube_nome'] = df_cartola_jogou['clube_id'].map(clubes_map_fantasia).fillna('')

df_cartola_agg = df_cartola_jogou.groupby(['atleta_id', 'apelido', 'clube_id', 'clube_nome', 'posicao_id']).agg({
    'rodada': 'nunique',
    'pontuacao': ['sum', 'mean'],
    'G': 'sum',
    'A': 'sum',
}).reset_index()

print(f"4. Jogadores únicos com pontuacao > 0: {len(df_cartola_agg)}")

# Verifica quantos têm match no FBref
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")
if os.path.exists(FBREF_JOGADORES_PATH):
    df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)
    print(f"\n5. Total de jogadores no FBref: {len(df_fbref)}")
    
    # Simula matching básico (apenas verifica se há nomes similares)
    from utils.analise_estatisticas import normalizar_nome, normalizar_clube, similaridade_nomes
    
    df_cartola_agg['Nome_Normalizado'] = df_cartola_agg['apelido'].apply(normalizar_nome)
    df_cartola_agg['Clube_Normalizado'] = df_cartola_agg['clube_nome'].apply(normalizar_clube)
    
    if 'Player' in df_fbref.columns:
        df_fbref['Nome_Normalizado'] = df_fbref['Player'].apply(normalizar_nome)
    if 'Clube' in df_fbref.columns:
        df_fbref['Clube_Normalizado'] = df_fbref['Clube'].apply(normalizar_clube)
    
    # Conta quantos jogadores do Cartola têm nomes similares no FBref
    # (aproximação simples, sem fazer matching completo)
    print(f"6. Verificando matches...")
    print(f"   (Matching completo seria muito lento, mas há {len(df_cartola_agg)} jogadores no Cartola)")
    print(f"   Se apenas 103 aparecem na tela, pode ser:")
    print(f"   - Filtro de mínimo de jogos")
    print(f"   - Apenas jogadores com match no FBref estão sendo mostrados")
    print(f"   - Algum outro filtro na interface")
else:
    print("\n5. Arquivo FBref não encontrado")

print("\n" + "="*70)
print("RESUMO:")
print(f"Total de jogadores únicos no Cartola (pontuacao > 0): {len(df_cartola_agg)}")
print("="*70)

