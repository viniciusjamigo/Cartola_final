# -*- coding: utf-8 -*-
"""Script para verificar quais colunas do FBref estão sendo usadas."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG: Verificação de colunas do FBref")
print("="*70)

df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)

print(f"\n1. Total de colunas: {len(df_fbref.columns)}")
print(f"2. Colunas relacionadas a XA/XG:")
for col in df_fbref.columns:
    if 'x' in col.lower() and ('a' in col.lower() or 'g' in col.lower()):
        print(f"   - {col}")

print(f"\n3. Verificando colunas específicas:")
print(f"   'xAG' existe? {'xAG' in df_fbref.columns}")
print(f"   'xAG.1' existe? {'xAG.1' in df_fbref.columns}")
print(f"   'xG' existe? {'xG' in df_fbref.columns}")
print(f"   'xG.1' existe? {'xG.1' in df_fbref.columns}")
print(f"   'MP' existe? {'MP' in df_fbref.columns}")

# Simula o código de seleção de colunas
colunas_necessarias = {
    'xAG_FBref': ['xAG', 'xAG.1'],
    'xG_FBref': ['xG', 'xG.1'],
}

colunas_selecionadas = []
colunas_renomeadas = {}

for nome_final, possiveis_nomes in colunas_necessarias.items():
    for nome_possivel in possiveis_nomes:
        if nome_possivel in df_fbref.columns:
            colunas_selecionadas.append(nome_possivel)
            colunas_renomeadas[nome_possivel] = nome_final
            print(f"\n4. {nome_final}: Encontrou '{nome_possivel}' -> renomeado para '{nome_final}'")
            break

# Testa com Arrascaeta
print(f"\n5. Testando com Arrascaeta:")
arrascaeta = df_fbref[df_fbref['Player'].str.contains('Arrascaeta', case=False, na=False)]
if not arrascaeta.empty:
    row = arrascaeta.iloc[0]
    print(f"   Player: {row['Player']}")
    print(f"   MP: {row.get('MP', 'N/A')}")
    if 'xAG' in df_fbref.columns:
        print(f"   xAG: {row.get('xAG', 'N/A')}")
    if 'xAG.1' in df_fbref.columns:
        print(f"   xAG.1: {row.get('xAG.1', 'N/A')}")
    if 'xG' in df_fbref.columns:
        print(f"   xG: {row.get('xG', 'N/A')}")
    if 'xG.1' in df_fbref.columns:
        print(f"   xG.1: {row.get('xG.1', 'N/A')}")

print("\n" + "="*70)




