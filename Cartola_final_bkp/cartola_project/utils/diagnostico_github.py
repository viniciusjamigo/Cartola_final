import requests
import pandas as pd

BASE_URL = "https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/{ano}/{arquivo}"
ANOS = [2023, 2024] # Vamos testar anos garantidos primeiro
ARQUIVOS = ["partidas.csv", "matches.csv"]

print("Diagnóstico de Conexão com GitHub Raw...")

for ano in ANOS:
    for arq in ARQUIVOS:
        url = BASE_URL.format(ano=ano, arquivo=arq)
        print(f"Testando: {url}")
        try:
            resp = requests.get(url)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                print("SUCCESS: Arquivo encontrado!")
                print(resp.text[:100]) # Primeiros caracteres
            else:
                print("FAIL: Arquivo não encontrado ou erro.")
        except Exception as e:
            print(f"ERROR: {e}")
        print("-" * 30)

