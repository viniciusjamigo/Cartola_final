# -*- coding: utf-8 -*-
"""Script para debugar exatamente como as rodadas são contadas."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PLAYERS_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")

print("="*70)
print("DEBUG: Como as rodadas são contadas para Kaio Jorge")
print("="*70)

# Carrega dados
df = pd.read_csv(HISTORICAL_PLAYERS_PATH, low_memory=False)
print(f"\n1. Total de registros no arquivo: {len(df)}")

# Filtra 2025
df_2025 = df[df['ano'] == 2025].copy()
print(f"2. Registros de 2025: {len(df_2025)}")

# Procura Kaio Jorge ANTES de qualquer filtro
print("\n" + "="*70)
print("PASSO 1: Buscar Kaio Jorge no arquivo (sem filtros)")
print("="*70)

kaio_todos = df_2025[df_2025['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
print(f"Total de linhas com 'Kaio Jorge' em 2025: {len(kaio_todos)}")

if not kaio_todos.empty:
    print(f"\nRodadas onde aparece (ANTES de remover duplicatas):")
    rodadas_antes = sorted(kaio_todos['rodada'].unique())
    print(f"  Total: {len(rodadas_antes)} rodadas")
    print(f"  Rodadas: {rodadas_antes}")
    
    # Verifica especificamente a rodada 2
    kaio_rodada_2 = kaio_todos[kaio_todos['rodada'] == 2]
    print(f"\nRodada 2 especificamente:")
    if not kaio_rodada_2.empty:
        print(f"  Encontrada! {len(kaio_rodada_2)} linha(s)")
        print(kaio_rodada_2[['ano', 'rodada', 'atleta_id', 'apelido', 'pontuacao', 'status_id', 'clube_id']].to_string())
    else:
        print("  NÃO encontrada!")
    
    # Remove duplicatas
    print("\n" + "="*70)
    print("PASSO 2: Remover duplicatas (atleta_id + rodada)")
    print("="*70)
    
    kaio_sem_dup = kaio_todos.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
    print(f"Após remover duplicatas: {len(kaio_sem_dup)} linhas")
    
    rodadas_sem_dup = sorted(kaio_sem_dup['rodada'].unique())
    print(f"Rodadas únicas: {len(rodadas_sem_dup)}")
    print(f"Rodadas: {rodadas_sem_dup}")
    
    # Filtra onde jogou
    print("\n" + "="*70)
    print("PASSO 3: Filtrar apenas onde pontuacao > 0")
    print("="*70)
    
    kaio_jogou = kaio_sem_dup[kaio_sem_dup['pontuacao'] > 0].copy()
    print(f"Linhas onde pontuacao > 0: {len(kaio_jogou)}")
    
    rodadas_onde_jogou = sorted(kaio_jogou['rodada'].unique())
    print(f"Rodadas onde jogou: {len(rodadas_onde_jogou)}")
    print(f"Rodadas: {rodadas_onde_jogou}")
    
    # Mostra rodadas que foram excluídas
    rodadas_excluidas = [r for r in rodadas_sem_dup if r not in rodadas_onde_jogou]
    print(f"\nRodadas EXCLUÍDAS (pontuacao <= 0): {len(rodadas_excluidas)}")
    print(f"Rodadas: {rodadas_excluidas}")
    
    if rodadas_excluidas:
        print("\nDetalhes das rodadas excluídas:")
        kaio_excluidas = kaio_sem_dup[kaio_sem_dup['rodada'].isin(rodadas_excluidas)]
        print(kaio_excluidas[['rodada', 'pontuacao', 'status_id', 'clube_id', 'apelido']].to_string())
    
    # Agregação final (como no código)
    print("\n" + "="*70)
    print("PASSO 4: Agregação final (como no código)")
    print("="*70)
    
    df_2025_sem_dup = df_2025.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
    kaio_agg = df_2025_sem_dup[df_2025_sem_dup['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
    
    kaio_jogou_agg = kaio_agg[kaio_agg['pontuacao'] > 0].copy()
    
    resultado = kaio_jogou_agg.groupby(['atleta_id', 'apelido']).agg({
        'rodada': 'nunique',
    }).reset_index()
    
    print(f"Resultado da agregação:")
    print(f"  Jogos (rodada nunique onde pontuacao > 0): {resultado['rodada'].iloc[0] if len(resultado) > 0 else 'N/A'}")
    
    # Mostra todas as rodadas com detalhes
    print("\n" + "="*70)
    print("TODAS AS RODADAS DO KAIO JORGE (após remover duplicatas)")
    print("="*70)
    kaio_detalhes = kaio_sem_dup.sort_values('rodada')[['rodada', 'pontuacao', 'status_id', 'clube_id', 'apelido']]
    print(kaio_detalhes.to_string(index=False))

print("\n" + "="*70)




