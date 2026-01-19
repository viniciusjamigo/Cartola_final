import pandas as pd
import os
import sys

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICAL_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")

sys.path.append(PROJECT_ROOT)
from utils.modelagem import preparar_features_historicas

def check_leakage():
    print(f"Carregando histórico de: {HISTORICAL_PATH}")
    df = pd.read_csv(HISTORICAL_PATH)
    
    # Check if media_num exists in raw file
    if 'media_num' in df.columns:
        print("⚠️ ALERTA: Coluna 'media_num' encontrada no arquivo original!")
        # Check if it leaks
        # For the last round, does media_num include the current score?
    else:
        print("✅ Coluna 'media_num' NÃO encontrada no arquivo original.")

    # Convert types
    df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
    
    # Filter for a specific player and recent rounds to inspect
    # Let's find a player with high variation/score in the last available round
    
    # Convert types
    df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['pontuacao'] = pd.to_numeric(df['pontuacao'], errors='coerce')
    df['atleta_id'] = pd.to_numeric(df['atleta_id'], errors='coerce')
    df['variacao_num'] = pd.to_numeric(df['variacao_num'], errors='coerce').fillna(0)
    df['preco_num'] = pd.to_numeric(df['preco_num'], errors='coerce').fillna(0)
    
    # Filter 2025
    df_2025 = df[df['ano'] == 2025].copy()
    if df_2025.empty:
        # Fallback to last available year
        max_year = df['ano'].max()
        df_2025 = df[df['ano'] == max_year].copy()
        print(f"Usando ano {max_year}")
    
    # Pick a round
    target_rodada = 34
    print(f"Analisando Rodada {target_rodada} do ano 2025")
    
    # Apply feature engineering
    print("Aplicando Feature Engineering...")
    df_features = preparar_features_historicas(df_2025.copy())
    
    # Pick a player who played in max_rodada
    df_round = df_features[df_features['rodada'] == target_rodada]
    if df_round.empty:
        print("Sem dados na rodada alvo.")
        return

    # Find top scorer
    top_scorer = df_round.loc[df_round['pontuacao'].idxmax()]
    
    print("\n--- INSPEÇÃO DE LEAKAGE ---")
    print(f"Atleta: {top_scorer['apelido']} (ID: {top_scorer['atleta_id']})")
    print(f"Rodada: {top_scorer['rodada']}")
    print(f"Pontuação Real: {top_scorer['pontuacao']}")
    
    # Check Price Leakage
    preco_pos = top_scorer['preco_num'] # This comes from the processed df
    variacao = top_scorer['variacao_num']
    preco_pre_calc = preco_pos - variacao
    
    # Get previous round price
    prev_rounds = df_features[(df_features['atleta_id'] == top_scorer['atleta_id']) & (df_features['rodada'] < target_rodada)]
    if not prev_rounds.empty:
        preco_anterior_real = prev_rounds.iloc[-1]['preco_num']
        print(f"\nPreço Rodada Anterior (Real): {preco_anterior_real}")
    else:
        preco_anterior_real = 0
        
    print(f"Preço Pós-Rodada (Atual): {preco_pos}")
    print(f"Variação Registrada: {variacao}")
    print(f"Preço Pré-Rodada (Calculado: Pos - Var): {preco_pre_calc}")
    
    diff = abs(preco_pre_calc - preco_anterior_real)
    if diff > 0.1:
        print(f"⚠️ LEAKAGE DETECTADO NO PREÇO! Diferença de {diff:.2f}")
        print("  O cálculo (Preco - Variacao) não bate com o preço da rodada anterior.")
        print("  Provável causa: variacao_num incorreta ou 0.")
    else:
        print("✅ Preço Pré-Rodada parece consistente.")


if __name__ == "__main__":
    check_leakage()

