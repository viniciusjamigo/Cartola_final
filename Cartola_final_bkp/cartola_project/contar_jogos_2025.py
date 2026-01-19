# -*- coding: utf-8 -*-
"""Script para contar jogos reais de cada jogador em 2025."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")

print("="*70)
print("CONTAGEM DE JOGOS REAIS EM 2025")
print("="*70)

# Carrega dados
df = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
print(f"\n1. Total de registros: {len(df)}")

# Filtra 2025
df_2025 = df[df['ano'] == 2025].copy()
print(f"2. Registros de 2025: {len(df_2025)}")

# Remove duplicatas de rodada por jogador
df_2025 = df_2025.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
print(f"3. Após remover duplicatas (atleta_id + rodada): {len(df_2025)}")

# Procura Kaio Jorge
print("\n" + "="*70)
print("ANÁLISE DO KAIO JORGE")
print("="*70)

kaio = df_2025[df_2025['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
if not kaio.empty:
    print(f"\nTotal de rodadas onde aparece: {len(kaio)}")
    print(f"Rodadas únicas: {kaio['rodada'].nunique()}")
    print(f"Rodadas: {sorted(kaio['rodada'].unique())}")
    
    # Verifica onde pontuou
    kaio_jogou = kaio[kaio['pontuacao'] > 0]
    print(f"\nRodadas onde pontuacao > 0: {len(kaio_jogou)}")
    print(f"Rodadas onde jogou: {sorted(kaio_jogou['rodada'].unique())}")
    
    # Verifica rodadas onde não jogou
    kaio_nao_jogou = kaio[kaio['pontuacao'] <= 0]
    print(f"\nRodadas onde NÃO jogou (pontuacao <= 0): {len(kaio_nao_jogou)}")
    if not kaio_nao_jogou.empty:
        print(f"Rodadas: {sorted(kaio_nao_jogou['rodada'].unique())}")
        print("\nDetalhes das rodadas onde não jogou:")
        print(kaio_nao_jogou[['rodada', 'pontuacao', 'status_id', 'apelido']].to_string())
    
    # Conta rodadas únicas onde jogou
    rodadas_onde_jogou = kaio_jogou['rodada'].nunique()
    print(f"\nRESULTADO: Kaio Jorge jogou {rodadas_onde_jogou} rodadas em 2025")
else:
    print("Kaio Jorge não encontrado!")

# Agregação geral
print("\n" + "="*70)
print("AGREGAÇÃO GERAL (TODOS OS JOGADORES)")
print("="*70)

# Filtra apenas onde jogou (pontuacao > 0)
df_jogou = df_2025[df_2025['pontuacao'] > 0].copy()

# Agrega por jogador
df_agg = df_jogou.groupby(['atleta_id', 'apelido']).agg({
    'rodada': 'nunique',  # Conta rodadas únicas onde jogou
    'pontuacao': ['sum', 'mean'],
}).reset_index()

df_agg.columns = ['atleta_id', 'apelido', 'Jogos', 'Pontuacao_Total', 'Media']

# Ordena por jogos
df_agg = df_agg.sort_values('Jogos', ascending=False)

print(f"\nTotal de jogadores únicos que jogaram: {len(df_agg)}")
print(f"\nTop 10 por número de jogos:")
print(df_agg.head(10)[['apelido', 'Jogos', 'Media']].to_string(index=False))

# Verifica Kaio Jorge na agregação
kaio_agg = df_agg[df_agg['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
if not kaio_agg.empty:
    print(f"\nKaio Jorge na agregação:")
    print(kaio_agg[['apelido', 'Jogos', 'Media']].to_string(index=False))

print("\n" + "="*70)




