# -*- coding: utf-8 -*-
"""Script de debug para verificar se MP está sendo lido corretamente."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG: Verificando leitura da coluna MP do FBref")
print("="*70)

# Carrega dados do FBref
df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)
print(f"\n1. Total de linhas no arquivo: {len(df_fbref)}")
print(f"   Colunas disponíveis: {list(df_fbref.columns)[:10]}...")

# Verifica se MP existe
if 'MP' in df_fbref.columns:
    print(f"\n2. [OK] Coluna 'MP' encontrada")
    print(f"   Tipo: {df_fbref['MP'].dtype}")
    print(f"   Valores únicos (primeiros 10): {sorted(df_fbref['MP'].dropna().unique())[:10]}")
    
    # Procura Kaio Jorge
    if 'Player' in df_fbref.columns:
        kaio = df_fbref[df_fbref['Player'].str.contains('Kaio', case=False, na=False)]
        if not kaio.empty:
            print(f"\n3. [OK] Kaio Jorge encontrado:")
            for idx, row in kaio.iterrows():
                print(f"   Nome: {row['Player']}")
                print(f"   MP: {row['MP']}")
                print(f"   Tipo MP: {type(row['MP'])}")
                if 'Clube' in row:
                    print(f"   Clube: {row['Clube']}")
else:
    print("\n2. [ERRO] Coluna 'MP' NÃO encontrada!")
    print(f"   Colunas disponíveis: {list(df_fbref.columns)}")

# Testa o mapeamento
print("\n4. Testando mapeamento:")
colunas_necessarias = {
    'Jogos_FBref': ['MP'],
}

colunas_selecionadas = []
colunas_renomeadas = {}

for nome_final, possiveis_nomes in colunas_necessarias.items():
    for nome_possivel in possiveis_nomes:
        if nome_possivel in df_fbref.columns:
            colunas_selecionadas.append(nome_possivel)
            colunas_renomeadas[nome_possivel] = nome_final
            print(f"   [OK] '{nome_possivel}' -> '{nome_final}'")
            break
    else:
        print(f"   [ERRO] Nenhum nome encontrado para '{nome_final}'")

if colunas_selecionadas:
    df_test = df_fbref[colunas_selecionadas].copy()
    df_test = df_test.rename(columns=colunas_renomeadas)
    print(f"\n5. Após renomeação:")
    print(f"   Colunas: {list(df_test.columns)}")
    if 'Jogos_FBref' in df_test.columns:
        kaio_test = df_test[df_fbref['Player'].str.contains('Kaio', case=False, na=False)]
        if not kaio_test.empty:
            print(f"   Kaio Jorge - Jogos_FBref: {kaio_test['Jogos_FBref'].iloc[0]}")
            print(f"   Tipo: {type(kaio_test['Jogos_FBref'].iloc[0])}")

print("\n" + "="*70)




