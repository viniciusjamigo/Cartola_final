import pandas as pd
import os

# --- Caminhos ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
HISTORICAL_MATCHES_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")

def diagnosticar_cobertura_de_dados():
    """
    Verifica a compatibilidade de anos e rodadas entre o histórico de jogadores
    e o histórico de partidas para identificar dados faltantes.
    """
    print("--- INICIANDO DIAGNÓSTICO DE COBERTURA DE DADOS ---")

    # 1. Carregar pares (ano, rodada) do histórico de jogadores
    if not os.path.exists(HISTORICAL_DATA_PATH):
        print(f"Erro: Arquivo de histórico de jogadores não encontrado em {HISTORICAL_DATA_PATH}")
        return
    try:
        df_jogadores = pd.read_csv(HISTORICAL_DATA_PATH, usecols=['ano', 'rodada'], low_memory=False)
        df_jogadores.dropna(inplace=True)
        # Cria um set de tuplas (ano, rodada) para busca rápida
        jogadores_pares = set(map(tuple, df_jogadores[['ano', 'rodada']].astype(int).values))
        print(f"Encontrados {len(jogadores_pares)} pares (ano, rodada) únicos no histórico de jogadores.")
    except Exception as e:
        print(f"Erro ao processar o histórico de jogadores: {e}")
        return

    # 2. Carregar pares (ano, rodada) do histórico de partidas
    if not os.path.exists(HISTORICAL_MATCHES_PATH):
        print(f"Erro: Arquivo de histórico de partidas não encontrado em {HISTORICAL_MATCHES_PATH}")
        return
    try:
        df_partidas = pd.read_csv(HISTORICAL_MATCHES_PATH, usecols=['ano', 'rodada'])
        df_partidas.dropna(inplace=True)
        # Cria um set de tuplas (ano, rodada)
        partidas_pares = set(map(tuple, df_partidas[['ano', 'rodada']].astype(int).values))
        print(f"Encontrados {len(partidas_pares)} pares (ano, rodada) únicos no histórico de partidas.")
    except Exception as e:
        print(f"Erro ao processar o histórico de partidas: {e}")
        return

    # 3. Identificar os pares faltantes
    pares_faltantes = jogadores_pares - partidas_pares
    
    if not pares_faltantes:
        print("\n--- RESULTADO ---")
        print("✅ Sucesso! Todos os pares (ano, rodada) do histórico de jogadores estão presentes no histórico de partidas.")
        return
        
    print(f"\n--- RESULTADO: DADOS DE PARTIDAS FALTANTES ---")
    print(f"Encontrados {len(pares_faltantes)} pares (ano, rodada) que existem nos dados dos jogadores mas não no histórico de partidas.")
    
    # Agrupa os resultados por ano para melhor visualização
    faltantes_por_ano = {}
    for ano, rodada in sorted(list(pares_faltantes)):
        if ano not in faltantes_por_ano:
            faltantes_por_ano[ano] = []
        faltantes_por_ano[ano].append(rodada)
        
    print("\nLista de rodadas faltantes por ano:")
    for ano, rodadas in sorted(faltantes_por_ano.items()):
        print(f"  - Ano {ano}: Faltam {len(rodadas)} rodadas.") # Rodadas: {sorted(rodadas)}

if __name__ == "__main__":
    diagnosticar_cobertura_de_dados()
