# -*- coding: utf-8 -*-
"""Script de teste simplificado para analise combinada."""

import os
import sys

# Adiciona o diretório do projeto ao path
caminho_projeto = os.path.join(os.path.dirname(__file__), 'cartola_project')
sys.path.insert(0, caminho_projeto)

# Muda para o diretório do projeto
os.chdir(caminho_projeto)

# Importa e testa
from utils.analise_estatisticas import analise_combinada_cartola_fbref

print("="*70)
print("TESTE: Análise Combinada Cartola + FBref")
print("="*70)

# Teste básico
print("\n1. Testando análise básica (ano 2025, sem filtros)...")
df_resultado, erro = analise_combinada_cartola_fbref(ano=2025)

if erro:
    print(f"   [ERRO] {erro}")
    sys.exit(1)

if df_resultado is None or df_resultado.empty:
    print("   [ERRO] Nenhum resultado retornado")
    sys.exit(1)

print(f"   [OK] {len(df_resultado)} jogadores encontrados")
print(f"   Colunas: {list(df_resultado.columns)}")
print(f"\n   Primeiros 5 registros:")
print(df_resultado.head().to_string())

print(f"\n   Estatísticas:")
print(f"   - Total de jogadores: {len(df_resultado)}")
print(f"   - Clubes únicos: {df_resultado['CLUBE'].nunique()}")
print(f"   - Posições: {df_resultado['POS'].unique()}")
print(f"   - JOGOS: min={df_resultado['JOGOS'].min()}, max={df_resultado['JOGOS'].max()}, média={df_resultado['JOGOS'].mean():.1f}")
print(f"   - MÉDIA: min={df_resultado['MÉDIA'].min():.2f}, max={df_resultado['MÉDIA'].max():.2f}")
print(f"   - XA/JOGO: min={df_resultado['XA/JOGO'].min():.3f}, max={df_resultado['XA/JOGO'].max():.3f}")
print(f"   - XG/JOGO: min={df_resultado['XG/JOGO'].min():.3f}, max={df_resultado['XG/JOGO'].max():.3f}")

print("\n" + "="*70)
print("TESTE CONCLUÍDO COM SUCESSO!")
print("="*70)




