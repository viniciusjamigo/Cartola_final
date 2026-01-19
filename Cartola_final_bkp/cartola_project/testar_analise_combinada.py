"""
Script de teste para verificar se a função analise_combinada_cartola_fbref está funcionando.
"""

import os
import sys
import pandas as pd

# Adiciona o diretório do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Muda para o diretório do projeto para garantir que os caminhos relativos funcionem
os.chdir(PROJECT_ROOT)

# Importa a função
from utils.analise_estatisticas import analise_combinada_cartola_fbref

def testar_analise_combinada():
    """Testa a função de análise combinada."""
    
    print("="*70)
    print("TESTE: Análise Combinada Cartola + FBref")
    print("="*70)
    
    # Teste 1: Análise básica (ano 2025, sem filtros)
    print("\n1. Testando análise básica (ano 2025, sem filtros)...")
    df_resultado, erro = analise_combinada_cartola_fbref(ano=2025)
    
    if erro:
        print(f"   [ERRO] {erro}")
        return False
    
    if df_resultado is None or df_resultado.empty:
        print("   [ERRO] Nenhum resultado retornado")
        return False
    
    print(f"   [OK] {len(df_resultado)} jogadores encontrados")
    print(f"   Colunas: {list(df_resultado.columns)}")
    print(f"\n   Primeiros 5 registros:")
    print(df_resultado.head().to_string())
    
    # Teste 2: Com filtro de posição
    print("\n2. Testando com filtro de posição (ATA)...")
    df_resultado2, erro2 = analise_combinada_cartola_fbref(ano=2025, posicao_filtro='ATA')
    
    if erro2:
        print(f"   [ERRO] {erro2}")
    elif df_resultado2 is not None and not df_resultado2.empty:
        print(f"   [OK] {len(df_resultado2)} atacantes encontrados")
        print(f"   Verificando posicoes: {df_resultado2['POS'].unique()}")
    else:
        print("   [AVISO] Nenhum resultado com filtro de posicao")
    
    # Teste 3: Com filtro de clube
    print("\n3. Testando com filtro de clube (Flamengo)...")
    df_resultado3, erro3 = analise_combinada_cartola_fbref(ano=2025, clubes_filtro=['Flamengo'])
    
    if erro3:
        print(f"   [ERRO] {erro3}")
    elif df_resultado3 is not None and not df_resultado3.empty:
        print(f"   [OK] {len(df_resultado3)} jogadores do Flamengo encontrados")
        print(f"   Verificando clubes: {df_resultado3['CLUBE'].unique()}")
    else:
        print("   [AVISO] Nenhum resultado com filtro de clube")
    
    # Teste 4: Com mínimo de jogos
    print("\n4. Testando com mínimo de jogos (10)...")
    df_resultado4, erro4 = analise_combinada_cartola_fbref(ano=2025, min_jogos=10)
    
    if erro4:
        print(f"   [ERRO] {erro4}")
    elif df_resultado4 is not None and not df_resultado4.empty:
        print(f"   [OK] {len(df_resultado4)} jogadores com 10+ jogos")
        print(f"   Jogos minimo: {df_resultado4['JOGOS'].min()}")
        print(f"   Jogos maximo: {df_resultado4['JOGOS'].max()}")
    else:
        print("   [AVISO] Nenhum resultado com minimo de jogos")
    
    # Verificação de dados
    print("\n5. Verificando qualidade dos dados...")
    if df_resultado is not None and not df_resultado.empty:
        print(f"   Total de jogadores: {len(df_resultado)}")
        print(f"   Clubes únicos: {df_resultado['CLUBE'].nunique()}")
        print(f"   Posições únicas: {df_resultado['POS'].unique()}")
        print(f"\n   Estatísticas das métricas:")
        print(f"   - JOGOS: min={df_resultado['JOGOS'].min()}, max={df_resultado['JOGOS'].max()}, média={df_resultado['JOGOS'].mean():.1f}")
        print(f"   - MÉDIA: min={df_resultado['MÉDIA'].min():.2f}, max={df_resultado['MÉDIA'].max():.2f}, média={df_resultado['MÉDIA'].mean():.2f}")
        print(f"   - XA/JOGO: min={df_resultado['XA/JOGO'].min():.3f}, max={df_resultado['XA/JOGO'].max():.3f}, média={df_resultado['XA/JOGO'].mean():.3f}")
        print(f"   - XG/JOGO: min={df_resultado['XG/JOGO'].min():.3f}, max={df_resultado['XG/JOGO'].max():.3f}, média={df_resultado['XG/JOGO'].mean():.3f}")
        print(f"   - ASSISTÊNCIAS: total={df_resultado['ASSISTÊNCIAS'].sum()}, média={df_resultado['ASSISTÊNCIAS'].mean():.1f}")
        print(f"   - GOLS: total={df_resultado['GOLS'].sum()}, média={df_resultado['GOLS'].mean():.1f}")
        print(f"   - G + A: total={df_resultado['G + A'].sum()}, média={df_resultado['G + A'].mean():.1f}")
        
        # Verifica se há valores zerados ou inválidos
        print(f"\n   Verificando valores inválidos:")
        print(f"   - XA/JOGO zerado: {(df_resultado['XA/JOGO'] == 0).sum()} jogadores")
        print(f"   - XG/JOGO zerado: {(df_resultado['XG/JOGO'] == 0).sum()} jogadores")
        print(f"   - ASSISTÊNCIAS zerado: {(df_resultado['ASSISTÊNCIAS'] == 0).sum()} jogadores")
        print(f"   - GOLS zerado: {(df_resultado['GOLS'] == 0).sum()} jogadores")
        
        # Mostra alguns exemplos
        print(f"\n   Top 5 por MÉDIA:")
        print(df_resultado.nlargest(5, 'MÉDIA')[['CLUBE', 'POS', 'NOME', 'JOGOS', 'MÉDIA', 'XA/JOGO', 'XG/JOGO', 'GOLS', 'ASSISTÊNCIAS']].to_string(index=False))
        
        print(f"\n   Top 5 por XG/JOGO:")
        print(df_resultado.nlargest(5, 'XG/JOGO')[['CLUBE', 'POS', 'NOME', 'JOGOS', 'MÉDIA', 'XA/JOGO', 'XG/JOGO', 'GOLS', 'ASSISTÊNCIAS']].to_string(index=False))
    
    print("\n" + "="*70)
    print("TESTE CONCLUÍDO")
    print("="*70)
    
    return True

if __name__ == "__main__":
    testar_analise_combinada()

