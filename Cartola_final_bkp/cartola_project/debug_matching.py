# -*- coding: utf-8 -*-
"""Script de debug para verificar o matching entre Cartola e FBref."""

import os
import sys
import pandas as pd

# Adiciona o diretório do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from utils.analise_estatisticas import normalizar_nome, normalizar_clube, similaridade_nomes

# Caminhos
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
FBREF_JOGADORES_PATH = os.path.join(DATA_DIR, "fbref", "fbref_jogadores_serie_a.csv")

print("="*70)
print("DEBUG: Matching Cartola + FBref")
print("="*70)

# Carrega dados do Cartola
print("\n1. Carregando dados do Cartola (ano 2025)...")
if not os.path.exists(HISTORICAL_PLAYERS_PATH):
    print(f"   [ERRO] Arquivo não encontrado: {HISTORICAL_PLAYERS_PATH}")
    sys.exit(1)

df_cartola = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
df_cartola = df_cartola[df_cartola['ano'] == 2025].copy()
print(f"   [OK] {len(df_cartola)} registros do Cartola para 2025")

# Agrega por jogador
from utils.analise_estatisticas import carregar_clubes_nome_fantasia, carregar_clubes
clubes_map_fantasia = carregar_clubes_nome_fantasia()
clubes_map = carregar_clubes()

print(f"   DEBUG: Mapeamento de clubes carregado")
print(f"   - Total de clubes no mapa: {len(clubes_map_fantasia)}")
print(f"   - Exemplos: {list(clubes_map_fantasia.items())[:5]}")

# Verifica clube_id no Cartola
print(f"   DEBUG: clube_id únicos no Cartola: {sorted(df_cartola['clube_id'].unique())[:10]}")

df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia)
print(f"   DEBUG: Clubes mapeados (não vazios): {df_cartola['clube_nome'].notna().sum()} de {len(df_cartola)}")
print(f"   DEBUG: Exemplos de mapeamento:")
for clube_id in df_cartola['clube_id'].unique()[:5]:
    nome = clubes_map_fantasia.get(clube_id, 'NÃO ENCONTRADO')
    print(f"      clube_id {clube_id} -> {nome}")

df_cartola['clube_nome'] = df_cartola['clube_id'].map(clubes_map_fantasia).fillna('')

df_cartola_agg = df_cartola.groupby(['atleta_id', 'apelido', 'clube_id', 'clube_nome', 'posicao_id']).agg({
    'pontuacao': ['count', 'mean'],
}).reset_index()
df_cartola_agg.columns = ['atleta_id', 'Nome_Cartola', 'clube_id', 'Clube_Cartola', 'posicao_id', 
                           'Jogos_Cartola', 'Media_Cartola']

print(f"   [OK] {len(df_cartola_agg)} jogadores únicos no Cartola")
print(f"   Clubes no Cartola (não vazios): {[c for c in sorted(df_cartola_agg['Clube_Cartola'].unique()) if c][:10]}...")

# Carrega dados do FBref
print("\n2. Carregando dados do FBref...")
if not os.path.exists(FBREF_JOGADORES_PATH):
    print(f"   [ERRO] Arquivo não encontrado: {FBREF_JOGADORES_PATH}")
    sys.exit(1)

df_fbref = pd.read_csv(FBREF_JOGADORES_PATH, low_memory=False)
print(f"   [OK] {len(df_fbref)} registros do FBref")

if 'Player' in df_fbref.columns:
    df_fbref = df_fbref[df_fbref['Player'].notna()].copy()
    df_fbref = df_fbref[df_fbref['Player'] != 'Player'].copy()
    df_fbref = df_fbref[df_fbref['Player'] != ''].copy()

print(f"   [OK] {len(df_fbref)} registros válidos após limpeza")
print(f"   Colunas disponíveis: {list(df_fbref.columns)[:10]}...")

# Verifica coluna Clube
if 'Clube' in df_fbref.columns:
    print(f"   Clubes no FBref: {sorted(df_fbref['Clube'].dropna().unique())[:10]}...")
else:
    print("   [AVISO] Coluna 'Clube' não encontrada no FBref!")

# Normaliza dados
print("\n3. Normalizando dados...")
df_cartola_agg['Nome_Normalizado'] = df_cartola_agg['Nome_Cartola'].apply(normalizar_nome)
df_cartola_agg['Clube_Normalizado'] = df_cartola_agg['Clube_Cartola'].apply(normalizar_clube)

if 'Player' in df_fbref.columns:
    df_fbref['Nome_Normalizado'] = df_fbref['Player'].apply(normalizar_nome)
if 'Clube' in df_fbref.columns:
    df_fbref['Clube_Normalizado'] = df_fbref['Clube'].apply(normalizar_clube)

print(f"   [OK] Dados normalizados")

# Testa matching
print("\n4. Testando matching...")
print(f"   Jogadores Cartola: {len(df_cartola_agg)}")
print(f"   Jogadores FBref: {len(df_fbref)}")

# Testa alguns exemplos
print("\n5. Exemplos de matching:")
exemplos_cartola = df_cartola_agg.head(10)
for idx, row in exemplos_cartola.iterrows():
    nome_cartola = row['Nome_Cartola']
    clube_cartola = row['Clube_Cartola']
    nome_norm_cartola = row['Nome_Normalizado']
    clube_norm_cartola = row['Clube_Normalizado']
    
    print(f"\n   Cartola: {nome_cartola} ({clube_cartola})")
    print(f"   Normalizado: {nome_norm_cartola} ({clube_norm_cartola})")
    
    # Procura no FBref
    df_match = df_fbref[df_fbref['Clube_Normalizado'] == clube_norm_cartola].copy()
    if not df_match.empty:
        print(f"   [OK] Encontrados {len(df_match)} jogadores do mesmo clube no FBref")
        
        # Calcula similaridade
        df_match['Similaridade'] = df_match['Nome_Normalizado'].apply(
            lambda x: similaridade_nomes(nome_norm_cartola, x)
        )
        melhor_match = df_match.nlargest(1, 'Similaridade')
        if not melhor_match.empty:
            melhor = melhor_match.iloc[0]
            print(f"   Melhor match: {melhor['Player']} (similaridade: {melhor['Similaridade']:.2f})")
            if melhor['Similaridade'] > 0.7:
                print(f"   [OK] Match válido!")
            else:
                print(f"   [AVISO] Similaridade abaixo do threshold (0.7)")
    else:
        print(f"   [ERRO] Nenhum jogador do clube '{clube_cartola}' encontrado no FBref")
        print(f"   Clubes disponíveis no FBref: {sorted(df_fbref['Clube_Normalizado'].dropna().unique())[:5]}...")

print("\n" + "="*70)
print("DEBUG CONCLUÍDO")
print("="*70)

