import pandas as pd
import os

# Caminho relativo ao workspace root
caminho_csv = 'cartola_project/data/historico_jogadores.csv'

print(f"Tentando ler: {caminho_csv}")

if os.path.exists(caminho_csv):
    try:
        df = pd.read_csv(caminho_csv)
        print("Arquivo carregado com sucesso.")
        
        # Filtra 2025
        df_2025 = df[df['ano'] == 2025]
        total_2025 = len(df_2025)
        print(f"Total de registros em 2025: {total_2025}")
        
        if total_2025 > 0:
            # Verifica pontuações
            zeros = (df_2025['pontuacao'] == 0).sum()
            validos = (df_2025['pontuacao'] != 0).sum()
            
            print(f"Registros com pontuação 0.0: {zeros}")
            print(f"Registros com pontuação válida (!= 0): {validos}")
            
            if validos > 0:
                print("Exemplo de pontuações válidas:")
                print(df_2025[df_2025['pontuacao'] != 0][['apelido', 'rodada', 'pontuacao']].head())
                print("Média das pontuações válidas 2025:", df_2025[df_2025['pontuacao'] != 0]['pontuacao'].mean())
            else:
                print("ALERTA: Nenhum jogador pontuou em 2025 neste arquivo. O RMSE não pode ser calculado sem gabarito.")
                
                # Mostra um exemplo de linha crua para ver se tem erro de leitura
                print("Exemplo de linha de 2025 (crua):")
                print(df_2025.iloc[0])
        else:
            print("Nenhum dado de 2025 encontrado.")
            
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
else:
    print("Arquivo não encontrado no caminho especificado.")

