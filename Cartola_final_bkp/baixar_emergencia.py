import pandas as pd
import requests
import os
from io import StringIO

def baixar_dados():
    # Define o caminho ABSOLUTO baseado na localização deste script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TARGET_DIR = os.path.join(BASE_DIR, "cartola_project", "data")
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    anos = [2018, 2019, 2020, 2022, 2023]
    url_template = "https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/01_raw/{ano}/rodada-{rodada}.csv"
    
    frames = []
    print(f"Baixando dados para: {TARGET_DIR}")
    
    for ano in anos:
        print(f"Ano {ano}...", end=" ")
        for rodada in range(1, 39):
            try:
                r = requests.get(url_template.format(ano=ano, rodada=rodada))
                if r.status_code == 200:
                    df = pd.read_csv(StringIO(r.text))
                    # Normaliza colunas básicas
                    df.columns = [c.lower() for c in df.columns]
                    df['ano'] = ano
                    if 'rodada' not in df.columns: df['rodada'] = rodada
                    
                    # Garante pontuação
                    if 'pontuacao' in df.columns:
                        frames.append(df)
            except:
                pass
        print("OK")

    if not frames:
        print("Falha ao baixar dados.")
        return

    print("Consolidando...")
    full_df = pd.concat(frames, ignore_index=True)
    
    # Salva
    dest = os.path.join(TARGET_DIR, "historico_jogadores.csv")
    full_df.to_csv(dest, index=False)
    print(f"Salvo em: {dest}")
    print(f"Total linhas: {len(full_df)}")
    print(f"Pontuações não-zero: {(full_df['pontuacao'] != 0).sum()}")

if __name__ == "__main__":
    baixar_dados()

