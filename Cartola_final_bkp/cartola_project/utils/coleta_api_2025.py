import requests
import pandas as pd
import os
import time

# --- CAMINHOS E URLs ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "historico_2025.csv")

API_PONTUADOS_URL = "https://api.cartolafc.globo.com/atletas/pontuados/{rodada}"

def coletar_2025(total_rodadas=38):
    print(f"Iniciando a coleta de dados da temporada 2025 via API...")
    todos_os_dados = []
    
    # Rodadas que já aconteceram (vamos tentar até a 38, se der 404 a gente para)
    for rodada in range(1, total_rodadas + 1):
        print(f"Processando rodada {rodada}...", end=" ")
        try:
            url = API_PONTUADOS_URL.format(rodada=rodada)
            response = requests.get(url)
            
            if response.status_code == 404:
                print("Rodada não encontrada (futura ou inválida).")
                continue # Ou break se quisermos parar na primeira falha
            
            response.raise_for_status()
            
            dados_rodada = response.json()
            atletas = dados_rodada.get('atletas', {})
            
            if not atletas:
                print(f"Sem dados de atletas.")
                continue

            count = 0
            for atleta_id, dados_atleta in atletas.items():
                registro = {
                    'ano': 2025,
                    'atleta_id': int(atleta_id),
                    'rodada': rodada,
                    'apelido': dados_atleta.get('apelido'),
                    'clube_id': dados_atleta.get('clube_id'),
                    'posicao_id': dados_atleta.get('posicao_id'),
                    'pontuacao': dados_atleta.get('pontuacao'),
                }
                
                # Scouts
                scouts = dados_atleta.get('scout', {})
                if scouts:
                    registro.update(scouts)
                
                todos_os_dados.append(registro)
                count += 1
            
            print(f"Ok ({count} atletas)")
            time.sleep(0.5) # Respeitar API

        except Exception as e:
            print(f"Erro: {e}")
            continue

    if not todos_os_dados:
        print("Nenhum dado coletado.")
        return

    df = pd.DataFrame(todos_os_dados)
    df.fillna(0, inplace=True)
    
    # Padronizar colunas (maiúsculas para bater com o histórico antigo)
    # O histórico antigo tem colunas tipo 'G', 'A', 'DS'. A API retorna isso mesmo.
    # Mas precisamos garantir.
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nColeta 2025 finalizada! Salvo em: {OUTPUT_FILE}")
    print(f"Total registros: {len(df)}")

if __name__ == "__main__":
    # Tenta pegar até a rodada 38 (vai falhar nas futuras, sem problema)
    coletar_2025(total_rodadas=38)

