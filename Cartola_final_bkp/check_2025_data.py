import pandas as pd

try:
    df = pd.read_csv('cartola_project/data/historico_jogadores.csv')
    df_2025 = df[df['ano'] == 2025]
    
    print(f"Total registros 2025: {len(df_2025)}")
    print(f"Pontuações zeradas: {(df_2025['pontuacao'] == 0).sum()}")
    print(f"Pontuações válidas (>0 ou <0): {(df_2025['pontuacao'] != 0).sum()}")
    
    if not df_2025.empty:
        print("Exemplo de pontuações não nulas:")
        print(df_2025[df_2025['pontuacao'] != 0][['apelido', 'rodada', 'pontuacao']].head())
except Exception as e:
    print(e)

