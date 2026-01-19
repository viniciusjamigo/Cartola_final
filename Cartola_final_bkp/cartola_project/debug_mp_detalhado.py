# -*- coding: utf-8 -*-
"""Script de debug detalhado para verificar MP."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from utils.analise_estatisticas import normalizar_nome, normalizar_clube, similaridade_nomes, safe_int

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG DETALHADO: Verificando MP do Kaio Jorge")
print("="*70)

# Carrega FBref
df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)
if 'Player' in df_fbref.columns:
    df_fbref = df_fbref[df_fbref['Player'].notna()].copy()
    df_fbref = df_fbref[df_fbref['Player'] != 'Player'].copy()
    df_fbref = df_fbref[df_fbref['Player'] != ''].copy()

print(f"\n1. FBref carregado: {len(df_fbref)} linhas")

# Testa mapeamento
colunas_necessarias = {
    'Nome_FBref': ['Player'],
    'Clube_FBref': ['Clube'],
    'Jogos_FBref': ['MP'],
    'Gols_FBref': ['Gls', 'Gls.1'],
    'Assistencias_FBref': ['Ast', 'Ast.1'],
    'G_mais_A_FBref': ['G+A', 'G+A.1'],
    'xG_FBref': ['xG', 'xG.1'],
    'xAG_FBref': ['xAG', 'xAG.1'],
    'Posicao_FBref': ['Pos'],
}

colunas_selecionadas = []
colunas_renomeadas = {}

for nome_final, possiveis_nomes in colunas_necessarias.items():
    for nome_possivel in possiveis_nomes:
        if nome_possivel in df_fbref.columns:
            colunas_selecionadas.append(nome_possivel)
            colunas_renomeadas[nome_possivel] = nome_final
            print(f"   Mapeado: '{nome_possivel}' -> '{nome_final}'")
            break

if 'Clube' in df_fbref.columns and 'Clube' not in colunas_selecionadas:
    colunas_selecionadas.append('Clube')
    colunas_renomeadas['Clube'] = 'Clube_FBref'

df_fbref_clean = df_fbref[colunas_selecionadas].copy()
df_fbref_clean = df_fbref_clean.rename(columns=colunas_renomeadas)

print(f"\n2. Após renomeação:")
print(f"   Colunas: {list(df_fbref_clean.columns)}")
print(f"   'Jogos_FBref' está presente? { 'Jogos_FBref' in df_fbref_clean.columns}")

# Procura Kaio Jorge
kaio_fbref = df_fbref_clean[df_fbref_clean['Nome_FBref'].str.contains('Kaio', case=False, na=False)]
if not kaio_fbref.empty:
    print(f"\n3. Kaio Jorge no FBref:")
    for idx, row in kaio_fbref.iterrows():
        print(f"   Nome: {row['Nome_FBref']}")
        print(f"   Clube: {row.get('Clube_FBref', 'N/A')}")
        print(f"   Jogos_FBref (raw): {row.get('Jogos_FBref', 'N/A')}")
        print(f"   Tipo: {type(row.get('Jogos_FBref', None))}")
        if 'Jogos_FBref' in row.index:
            valor_mp = row['Jogos_FBref']
            print(f"   Valor MP: {valor_mp}")
            print(f"   safe_int(MP): {safe_int(valor_mp)}")
            print(f"   int(MP): {int(valor_mp) if pd.notna(valor_mp) else 'NaN'}")

# Carrega Cartola
df_cartola = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
df_cartola = df_cartola[df_cartola['ano'] == 2025].copy()
df_cartola['clube_id'] = pd.to_numeric(df_cartola['clube_id'], errors='coerce').fillna(0).astype(int)

from utils.analise_estatisticas import carregar_clubes_nome_fantasia
clubes_map_fantasia = carregar_clubes_nome_fantasia()
df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia).fillna('')

df_cartola_jogou = df_cartola[df_cartola['pontuacao'] > 0].copy()
df_cartola_jogou = df_cartola_jogou.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()

df_cartola_agg = df_cartola_jogou.groupby(['atleta_id', 'apelido', 'clube_id', 'clube_nome', 'posicao_id']).agg({
    'pontuacao': 'mean',
    'G': 'sum',
    'A': 'sum',
}).reset_index()

df_cartola_agg.columns = ['atleta_id', 'Nome_Cartola', 'clube_id', 'Clube_Cartola', 'posicao_id', 
                           'Media_Cartola', 'Gols_Cartola', 'Assistencias_Cartola']

df_cartola_agg['Nome_Normalizado'] = df_cartola_agg['Nome_Cartola'].apply(normalizar_nome)
df_cartola_agg['Clube_Normalizado'] = df_cartola_agg['Clube_Cartola'].apply(normalizar_clube)

df_fbref_clean['Nome_Normalizado'] = df_fbref_clean['Nome_FBref'].apply(normalizar_nome)
df_fbref_clean['Clube_Normalizado'] = df_fbref_clean['Clube_FBref'].apply(normalizar_clube)

# Procura Kaio Jorge no Cartola
kaio_cartola = df_cartola_agg[df_cartola_agg['Nome_Cartola'].str.contains('Kaio', case=False, na=False)]
if not kaio_cartola.empty:
    print(f"\n4. Kaio Jorge no Cartola:")
    for idx, row in kaio_cartola.iterrows():
        print(f"   Nome: {row['Nome_Cartola']}")
        print(f"   Clube: {row['Clube_Cartola']}")
        print(f"   Nome Normalizado: {row['Nome_Normalizado']}")
        print(f"   Clube Normalizado: {row['Clube_Normalizado']}")
        
        # Tenta fazer matching
        df_match = df_fbref_clean[
            (df_fbref_clean['Clube_Normalizado'] == row['Clube_Normalizado'])
        ].copy()
        
        if not df_match.empty:
            print(f"   Encontrados {len(df_match)} jogadores do mesmo clube no FBref")
            df_match['Similaridade'] = df_match['Nome_Normalizado'].apply(
                lambda x: similaridade_nomes(row['Nome_Normalizado'], x)
            )
            melhor_match = df_match[df_match['Similaridade'] > 0.7].nlargest(1, 'Similaridade')
            
            if not melhor_match.empty:
                row_fbref = melhor_match.iloc[0]
                print(f"   Melhor match: {row_fbref['Nome_FBref']} (similaridade: {row_fbref['Similaridade']:.2f})")
                print(f"   Clube match: {row_fbref.get('Clube_FBref', 'N/A')}")
                
                # Tenta acessar Jogos_FBref
                print(f"\n   Tentando acessar Jogos_FBref:")
                print(f"   'Jogos_FBref' in row_fbref.index? { 'Jogos_FBref' in row_fbref.index}")
                print(f"   row_fbref.index: {list(row_fbref.index)[:10]}...")
                
                try:
                    jogos_fbref = row_fbref['Jogos_FBref']
                    print(f"   row_fbref['Jogos_FBref'] = {jogos_fbref}")
                    print(f"   Tipo: {type(jogos_fbref)}")
                    print(f"   safe_int(jogos_fbref) = {safe_int(jogos_fbref)}")
                except KeyError as e:
                    print(f"   ERRO KeyError: {e}")
                    # Tenta MP
                    if 'MP' in row_fbref.index:
                        print(f"   Tentando MP direto: {row_fbref['MP']}")
                        print(f"   safe_int(MP) = {safe_int(row_fbref['MP'])}")
            else:
                print(f"   Nenhum match com similaridade > 0.7")
        else:
            print(f"   Nenhum jogador do clube '{row['Clube_Cartola']}' encontrado no FBref")

print("\n" + "="*70)




