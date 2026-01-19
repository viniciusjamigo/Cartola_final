# -*- coding: utf-8 -*-
"""Script para debugar cálculo de jogos, média e média básica do Kaio Jorge usando historico_completo.csv."""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv")

print("="*70)
print("DEBUG: Cálculo de JOGOS, MÉDIA e M. BÁSICA - Kaio Jorge")
print("Usando arquivo: historico_2025.csv")
print("="*70)

# Carrega dados do arquivo (já filtrado para 2025)
df_2025 = pd.read_csv(HISTORICAL_2025_PATH, low_memory=False)
print(f"\n1. Total de registros no arquivo (já filtrado para 2025): {len(df_2025)}")

# Procura Kaio Jorge
print("\n" + "="*70)
print("BUSCANDO KAIO JORGE")
print("="*70)

kaio = df_2025[df_2025['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
print(f"\nTotal de linhas com 'Kaio Jorge' em 2025: {len(kaio)}")

if not kaio.empty:
    print(f"Rodadas onde aparece: {sorted(kaio['rodada'].unique())}")
    print(f"Total de rodadas: {len(kaio['rodada'].unique())}")
    
    # Remove duplicatas
    print("\n" + "="*70)
    print("PASSO 1: Remover duplicatas (atleta_id + rodada)")
    print("="*70)
    
    kaio_sem_dup = kaio.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
    print(f"Após remover duplicatas: {len(kaio_sem_dup)} linhas")
    print(f"Rodadas únicas: {sorted(kaio_sem_dup['rodada'].unique())}")
    
    # Calcula JOGOS (TODAS as rodadas únicas onde apareceu, mesmo com pontuacao = 0)
    jogos = kaio_sem_dup['rodada'].nunique()
    print(f"\nJOGOS (rodadas únicas onde apareceu, incluindo pontuacao = 0): {jogos}")
    
    # Filtra onde jogou (pontuacao > 0) para calcular M. BÁSICA
    print("\n" + "="*70)
    print("PASSO 2: Filtrar apenas onde pontuacao > 0 (para M. BÁSICA)")
    print("="*70)
    
    kaio_jogou = kaio_sem_dup[kaio_sem_dup['pontuacao'] > 0].copy()
    print(f"Linhas onde pontuacao > 0: {len(kaio_jogou)}")
    print(f"Rodadas onde jogou: {sorted(kaio_jogou['rodada'].unique())}")
    
    # Calcula MÉDIA (soma pontuacao / numero total de rodadas onde apareceu, incluindo 0)
    soma_pontuacao = kaio_sem_dup['pontuacao'].sum()  # Soma TODA a pontuacao (inclui 0)
    media = soma_pontuacao / jogos if jogos > 0 else 0
    print(f"\nMÉDIA:")
    print(f"  Soma pontuacao (inclui 0): {soma_pontuacao}")
    print(f"  Número total de rodadas onde apareceu: {jogos}")
    print(f"  MÉDIA = {soma_pontuacao} / {jogos} = {media:.2f}")
    
    # Calcula M. BÁSICA (nova fórmula)
    print("\n" + "="*70)
    print("PASSO 3: Calcular M. BÁSICA (NOVA FÓRMULA)")
    print("="*70)
    
    # Verifica se tem colunas G e A
    tem_G = 'G' in kaio_sem_dup.columns
    tem_A = 'A' in kaio_sem_dup.columns
    
    print(f"Tem coluna 'G'? {tem_G}")
    print(f"Tem coluna 'A'? {tem_A}")
    
    if tem_G and tem_A:
        # Nova fórmula: ((SOMA da pontuação) - (soma de pontos por gols + soma de pontos por assistência)) / total de jogos
        soma_pontuacao_total = kaio_sem_dup['pontuacao'].sum()  # Soma TODA a pontuação (inclui 0)
        soma_gols = kaio_sem_dup['G'].fillna(0).sum()
        soma_assistencias = kaio_sem_dup['A'].fillna(0).sum()
        pontos_por_gols = soma_gols * 8
        pontos_por_assistencias = soma_assistencias * 5
        total_jogos = jogos  # Todas as rodadas onde apareceu
        
        media_basica = (soma_pontuacao_total - (pontos_por_gols + pontos_por_assistencias)) / total_jogos
        
        print(f"\nM. BÁSICA (NOVA FÓRMULA):")
        print(f"  Soma pontuação total: {soma_pontuacao_total:.2f}")
        print(f"  Soma gols: {soma_gols}")
        print(f"  Soma assistências: {soma_assistencias}")
        print(f"  Pontos por gols (G*8): {pontos_por_gols}")
        print(f"  Pontos por assistências (A*5): {pontos_por_assistencias}")
        print(f"  Total de jogos: {total_jogos}")
        print(f"  M. BÁSICA = ({soma_pontuacao_total:.2f} - ({pontos_por_gols} + {pontos_por_assistencias})) / {total_jogos}")
        print(f"  M. BÁSICA = {soma_pontuacao_total - (pontos_por_gols + pontos_por_assistencias):.2f} / {total_jogos}")
        print(f"  M. BÁSICA = {media_basica:.2f}")
    else:
        print("AVISO: Colunas G ou A não encontradas!")
        media_basica = 0
    
    # Resultado final
    print("\n" + "="*70)
    print("RESULTADO FINAL PARA KAIO JORGE")
    print("="*70)
    print(f"JOGOS: {jogos}")
    print(f"MÉDIA: {media:.2f}")
    print(f"M. BÁSICA: {media_basica:.2f}")
    
    # Compara com o que está sendo calculado no código atual
    print("\n" + "="*70)
    print("COMPARAÇÃO COM CÓDIGO ATUAL")
    print("="*70)
    
    # Simula o que o código faz
    from utils.analise_estatisticas import carregar_clubes_nome_fantasia
    clubes_map_fantasia = carregar_clubes_nome_fantasia()
    
    df_2025['clube_id'] = pd.to_numeric(df_2025['clube_id'], errors='coerce').fillna(0).astype(int)
    df_2025['clube_nome'] = df_2025['clube_id'].map(clubes_map_fantasia).fillna('')
    
    df_2025_sem_dup = df_2025.drop_duplicates(subset=['atleta_id', 'rodada'], keep='first').copy()
    
    # NOVA LÓGICA: Conta TODAS as rodadas onde apareceu (incluindo pontuacao = 0)
    kaio_codigo = df_2025_sem_dup[df_2025_sem_dup['apelido'].str.contains('Kaio Jorge', case=False, na=False)]
    
    if not kaio_codigo.empty:
        # Agrega TODAS as rodadas (incluindo pontuacao = 0)
        kaio_agg = kaio_codigo.groupby(['atleta_id', 'apelido', 'clube_id', 'clube_nome', 'posicao_id']).agg({
            'rodada': 'nunique',  # Conta TODAS as rodadas
            'pontuacao': ['sum', 'mean'],  # Soma inclui 0
            'G': 'sum',
            'A': 'sum',
        }).reset_index()
        
        # Recalcula média: soma / total_rodadas (inclui 0)
        kaio_agg['Media_Recalculada'] = kaio_agg[('pontuacao', 'sum')] / kaio_agg[('rodada', 'nunique')]
        
        print(f"Resultado do código atual (NOVA LÓGICA):")
        jogos_codigo = kaio_agg[('rodada', 'nunique')].iloc[0] if len(kaio_agg) > 0 else 0
        media_codigo = kaio_agg['Media_Recalculada'].iloc[0] if len(kaio_agg) > 0 else 0
        print(f"  JOGOS: {jogos_codigo}")
        if isinstance(media_codigo, (int, float)):
            print(f"  MÉDIA: {media_codigo:.2f}")
        else:
            print(f"  MÉDIA: {media_codigo}")
        
        # Calcula média básica (NOVA FÓRMULA)
        # ((SOMA da pontuação) - (soma de pontos por gols + soma de pontos por assistência)) / total de jogos
        if len(kaio_agg) > 0:
            soma_pont_total = float(kaio_agg[('pontuacao', 'sum')].iloc[0]) if pd.notna(kaio_agg[('pontuacao', 'sum')].iloc[0]) else 0
            soma_g = float(kaio_agg[('G', 'sum')].iloc[0]) if pd.notna(kaio_agg[('G', 'sum')].iloc[0]) else 0
            soma_a = float(kaio_agg[('A', 'sum')].iloc[0]) if pd.notna(kaio_agg[('A', 'sum')].iloc[0]) else 0
            total_jogos_codigo = float(jogos_codigo) if pd.notna(jogos_codigo) and jogos_codigo > 0 else 0
            
            if total_jogos_codigo > 0:
                media_basica_codigo = (soma_pont_total - (soma_g * 8 + soma_a * 5)) / total_jogos_codigo
            else:
                media_basica_codigo = 0
        else:
            media_basica_codigo = 0
        
        if isinstance(media_basica_codigo, (int, float)):
            print(f"  M. BÁSICA: {media_basica_codigo:.2f}")
        else:
            print(f"  M. BÁSICA: {media_basica_codigo}")

else:
    print("Kaio Jorge não encontrado no arquivo!")

print("\n" + "="*70)
