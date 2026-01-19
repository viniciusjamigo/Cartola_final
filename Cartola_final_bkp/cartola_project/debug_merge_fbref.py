# -*- coding: utf-8 -*-
"""Script para debugar o merge entre FBref e Cartola, especialmente XA/jogo e XG/jogo."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG: Merge FBref x Cartola - XA/jogo e XG/jogo")
print("="*70)

# Carrega dados
df_cartola = pd.read_csv(HISTORICAL_2025_PATH, low_memory=False)
df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)

print(f"\n1. Total de registros no Cartola: {len(df_cartola)}")
print(f"2. Total de registros no FBref: {len(df_fbref)}")

# Verifica colunas do FBref
print(f"\n3. Colunas do FBref:")
print(df_fbref.columns.tolist()[:20])  # Primeiras 20 colunas

# Procura por colunas relacionadas a XA e XG
print(f"\n4. Colunas relacionadas a XA/XG:")
colunas_xa_xg = [col for col in df_fbref.columns if 'x' in col.lower() or 'xa' in col.lower() or 'xg' in col.lower()]
print(colunas_xa_xg)

# Verifica se tem coluna MP (Matches Played)
print(f"\n5. Coluna MP (Matches Played) existe? {'MP' in df_fbref.columns}")
if 'MP' in df_fbref.columns:
    print(f"   Valores únicos de MP: {sorted(df_fbref['MP'].dropna().unique())[:10]}")

# Simula o matching para alguns jogadores
print("\n" + "="*70)
print("6. SIMULANDO MATCHING PARA ALGUNS JOGADORES")
print("="*70)

from utils.analise_estatisticas import normalizar_nome, normalizar_clube, similaridade_nomes, carregar_clubes_nome_fantasia

# Prepara dados do Cartola
clubes_map_fantasia = carregar_clubes_nome_fantasia()
df_cartola['clube_id'] = pd.to_numeric(df_cartola['clube_id'], errors='coerce').fillna(0).astype(int)
df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia).fillna('')
df_cartola = df_cartola.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()

# Agrega Cartola
df_cartola_agg = df_cartola.groupby(['atleta_id', 'apelido']).agg({
    'rodada': 'nunique',
    'pontuacao': 'sum',
    'G': 'sum',
    'A': 'sum',
}).reset_index()
df_cartola_agg.columns = ['atleta_id', 'Nome_Cartola', 'Jogos_Cartola', 'Pontuacao_Total', 'Gols_Cartola', 'Assistencias_Cartola']
df_cartola_agg['Nome_Normalizado'] = df_cartola_agg['Nome_Cartola'].apply(normalizar_nome)

# Pega clube mais recente
df_cartola_ultimo_clube = df_cartola.sort_values('rodada').groupby(['atleta_id', 'apelido']).last()[['clube_id', 'clube_nome']].reset_index()
df_cartola_agg = df_cartola_agg.merge(df_cartola_ultimo_clube[['atleta_id', 'clube_id', 'clube_nome']], on='atleta_id', how='left')
df_cartola_agg['Clube_Normalizado'] = df_cartola_agg['clube_nome'].apply(normalizar_clube)

# Prepara dados do FBref
if 'Player' in df_fbref.columns:
    df_fbref = df_fbref[df_fbref['Player'].notna()].copy()
    df_fbref['Nome_Normalizado'] = df_fbref['Player'].apply(normalizar_nome)
if 'Clube' in df_fbref.columns:
    df_fbref['Clube_Normalizado'] = df_fbref['Clube'].apply(normalizar_clube)

# Procura colunas XA e XG
coluna_xag = None
coluna_xg = None
for col in df_fbref.columns:
    if 'xag' in col.lower() or ('x' in col.lower() and 'a' in col.lower() and 'g' in col.lower()):
        coluna_xag = col
    if 'xg' in col.lower() and coluna_xg is None:
        coluna_xg = col

print(f"\nColuna XAG encontrada: {coluna_xag}")
print(f"Coluna XG encontrada: {coluna_xg}")

# Testa matching para alguns jogadores conhecidos
jogadores_teste = ['Arrascaeta', 'Kaio Jorge', 'Pedro', 'Marcos Rocha']

for nome_teste in jogadores_teste:
    print(f"\n--- Testando: {nome_teste} ---")
    
    # Procura no Cartola
    cartola_match = df_cartola_agg[df_cartola_agg['Nome_Cartola'].str.contains(nome_teste, case=False, na=False)]
    
    if not cartola_match.empty:
        row_cartola = cartola_match.iloc[0]
        print(f"  Cartola: {row_cartola['Nome_Cartola']} - Jogos: {row_cartola['Jogos_Cartola']} - Clube: {row_cartola['clube_nome']}")
        
        # Procura no FBref
        nome_cartola_norm = row_cartola['Nome_Normalizado']
        clube_cartola_norm = row_cartola['Clube_Normalizado']
        
        df_match = df_fbref[df_fbref['Clube_Normalizado'] == clube_cartola_norm].copy()
        if df_match.empty:
            df_match = df_fbref.copy()
        
        if not df_match.empty:
            df_match['Similaridade'] = df_match['Nome_Normalizado'].apply(
                lambda x: similaridade_nomes(nome_cartola_norm, x)
            )
            melhor_match = df_match[df_match['Similaridade'] > 0.7].nlargest(1, 'Similaridade')
            if melhor_match.empty:
                melhor_match = df_match[df_match['Similaridade'] > 0.5].nlargest(1, 'Similaridade')
            
            if not melhor_match.empty:
                row_fbref = melhor_match.iloc[0]
                print(f"  FBref: {row_fbref.get('Player', 'N/A')} - Similaridade: {melhor_match['Similaridade'].iloc[0]:.2f}")
                
                # Verifica MP
                mp_fbref = row_fbref.get('MP', 0)
                print(f"  MP (FBref): {mp_fbref}")
                print(f"  Jogos (Cartola): {row_cartola['Jogos_Cartola']}")
                
                # Verifica XAG e XG
                if coluna_xag:
                    xag_valor = pd.to_numeric(row_fbref.get(coluna_xag, 0), errors='coerce') or 0
                    print(f"  {coluna_xag}: {xag_valor}")
                    if row_cartola['Jogos_Cartola'] > 0:
                        xa_jogo = xag_valor / row_cartola['Jogos_Cartola']
                        print(f"  XA/jogo (usando jogos Cartola): {xa_jogo:.3f}")
                    if mp_fbref > 0:
                        xa_jogo_fbref = xag_valor / mp_fbref
                        print(f"  XA/jogo (usando MP FBref): {xa_jogo_fbref:.3f}")
                
                if coluna_xg:
                    xg_valor = pd.to_numeric(row_fbref.get(coluna_xg, 0), errors='coerce') or 0
                    print(f"  {coluna_xg}: {xg_valor}")
                    if row_cartola['Jogos_Cartola'] > 0:
                        xg_jogo = xg_valor / row_cartola['Jogos_Cartola']
                        print(f"  XG/jogo (usando jogos Cartola): {xg_jogo:.3f}")
                    if mp_fbref > 0:
                        xg_jogo_fbref = xg_valor / mp_fbref
                        print(f"  XG/jogo (usando MP FBref): {xg_jogo_fbref:.3f}")
            else:
                print(f"  FBref: Nenhum match encontrado")
        else:
            print(f"  FBref: Nenhum candidato disponível")
    else:
        print(f"  Cartola: Não encontrado")

print("\n" + "="*70)




