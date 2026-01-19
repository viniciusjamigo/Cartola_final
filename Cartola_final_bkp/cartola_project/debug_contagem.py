# -*- coding: utf-8 -*-
"""Script para contar quantos jogadores estão sendo processados."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")

print("="*70)
print("DEBUG: Contagem de jogadores")
print("="*70)

# Carrega Cartola
df_cartola = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
df_cartola = df_cartola[df_cartola['ano'] == 2025].copy()
print(f"\n1. Total de registros do Cartola (2025): {len(df_cartola)}")

df_cartola['clube_id'] = pd.to_numeric(df_cartola['clube_id'], errors='coerce').fillna(0).astype(int)

from utils.analise_estatisticas import carregar_clubes_nome_fantasia
clubes_map_fantasia = carregar_clubes_nome_fantasia()
df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia).fillna('')

print(f"2. Jogadores únicos (antes de filtrar pontuacao > 0): {df_cartola['atleta_id'].nunique()}")

# Filtra apenas jogos onde jogou
df_cartola_jogou = df_cartola[df_cartola['pontuacao'] > 0].copy()
print(f"3. Registros com pontuacao > 0: {len(df_cartola_jogou)}")
print(f"   Jogadores únicos com pontuacao > 0: {df_cartola_jogou['atleta_id'].nunique()}")

# Remove duplicatas
df_cartola_jogou = df_cartola_jogou.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
print(f"4. Após remover duplicatas de rodada: {len(df_cartola_jogou)}")
print(f"   Jogadores únicos: {df_cartola_jogou['atleta_id'].nunique()}")

# Agrega
df_cartola_agg = df_cartola_jogou.groupby(['atleta_id', 'apelido', 'clube_id', 'clube_nome', 'posicao_id']).agg({
    'rodada': 'nunique',
    'pontuacao': 'mean',
    'G': 'sum',
    'A': 'sum',
}).reset_index()

print(f"5. Após agregação: {len(df_cartola_agg)} jogadores")
print(f"   Clubes únicos: {df_cartola_agg['clube_nome'].nunique()}")
print(f"   Clubes: {sorted([c for c in df_cartola_agg['clube_nome'].unique() if c])[:10]}...")

# Verifica quantos têm clube vazio
sem_clube = df_cartola_agg[df_cartola_agg['clube_nome'] == '']
print(f"6. Jogadores sem clube mapeado: {len(sem_clube)}")

print("\n" + "="*70)

