import pandas as pd
import os
import random

# Caminho do arquivo
DATA_DIR = os.path.join("cartola_project", "data")
PARTIDAS_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")

def gerar_tabela_2025():
    if not os.path.exists(PARTIDAS_PATH):
        print("Arquivo de partidas não encontrado.")
        return

    df = pd.read_csv(PARTIDAS_PATH)
    
    # Verifica se já tem 2025
    if 2025 in df['ano'].unique():
        print("Já existem dados de 2025.")
        return

    print("Gerando tabela simulada para 2025 (Baseada em 2024)...")
    
    # Pega jogos de 2024
    df_2024 = df[df['ano'] == 2024].copy()
    
    if df_2024.empty:
        print("Não há dados de 2024 para basear.")
        return

    # Cria 2025 replicando 2024
    df_2025 = df_2024.copy()
    df_2025['ano'] = 2025
    
    # Opcional: Randomizar placares para não ficar idêntico
    # Mas manter mandante/visitante para ter a feature 'fl_mandante' consistente
    # Nota: Isso assume que os times são os mesmos (ignora rebaixamento)
    # Para fins de teste do modelo de Mando de Campo, serve perfeitamente.
    
    # Limita até a rodada 33 (conforme seu pedido)
    df_2025 = df_2025[df_2025['rodada'] <= 33]
    
    print(f"Criando {len(df_2025)} partidas para 2025...")
    
    # Concatena e salva
    df_final = pd.concat([df, df_2025], ignore_index=True)
    df_final.to_csv(PARTIDAS_PATH, index=False)
    print("Arquivo historico_partidas.csv atualizado com sucesso!")

if __name__ == "__main__":
    gerar_tabela_2025()



