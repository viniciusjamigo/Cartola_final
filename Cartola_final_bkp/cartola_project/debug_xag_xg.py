# -*- coding: utf-8 -*-
"""Script para testar se xAG.1 e xG.1 estão sendo usados corretamente."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG: Verificação de xAG.1 e xG.1")
print("="*70)

df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)

# Simula o código de seleção de colunas
colunas_necessarias = {
    'xAG_FBref': ['xAG.1', 'xAG'],  # Prioriza xAG.1 (por jogo) sobre xAG (total)
    'xG_FBref': ['xG.1', 'xG'],  # Prioriza xG.1 (por jogo) sobre xG (total)
}

colunas_selecionadas = []
colunas_renomeadas = {}

for nome_final, possiveis_nomes in colunas_necessarias.items():
    for nome_possivel in possiveis_nomes:
        if nome_possivel in df_fbref.columns:
            colunas_selecionadas.append(nome_possivel)
            colunas_renomeadas[nome_possivel] = nome_final
            print(f"{nome_final}: Encontrou '{nome_possivel}' -> renomeado para '{nome_final}'")
            break

# Testa com Arrascaeta
print(f"\nTestando com Arrascaeta:")
arrascaeta = df_fbref[df_fbref['Player'].str.contains('Arrascaeta', case=False, na=False)]
if not arrascaeta.empty:
    row = arrascaeta.iloc[0]
    print(f"Player: {row['Player']}")
    
    # Simula o que o código faz após renomear
    df_test = df_fbref[colunas_selecionadas].copy()
    df_test = df_test.rename(columns=colunas_renomeadas)
    
    if 'xAG_FBref' in df_test.columns:
        xag_valor = pd.to_numeric(row[colunas_renomeadas.get('xAG.1', 'xAG')], errors='coerce') or 0
        print(f"xAG_FBref (valor usado): {xag_valor}")
        print(f"  (deve ser xAG.1 = {row.get('xAG.1', 'N/A')}, não xAG = {row.get('xAG', 'N/A')})")
    
    if 'xG_FBref' in df_test.columns:
        xg_valor = pd.to_numeric(row[colunas_renomeadas.get('xG.1', 'xG')], errors='coerce') or 0
        print(f"xG_FBref (valor usado): {xg_valor}")
        print(f"  (deve ser xG.1 = {row.get('xG.1', 'N/A')}, não xG = {row.get('xG', 'N/A')})")

print("\n" + "="*70)




