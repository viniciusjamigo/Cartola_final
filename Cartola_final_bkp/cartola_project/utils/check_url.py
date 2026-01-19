import requests

ANO = 2018
BASE_URL = f"https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/{ANO}/{{arquivo}}"

# Lista de possíveis nomes de arquivo para testar
arquivos_para_testar = [
    'partidas.csv',
    'matches.csv',
    'partidas_2018.csv',
    'rodadas_2018.csv',
    'dados_partidas.csv'
]

print(f"--- Verificando URLs para o ano de {ANO} ---")

encontrou_url = False
for arquivo in arquivos_para_testar:
    url = BASE_URL.format(arquivo=arquivo)
    try:
        response = requests.head(url) # HEAD é mais rápido que GET, só pega os cabeçalhos
        if response.status_code == 200:
            print(f"[SUCESSO] Encontrado em: {url}")
            encontrou_url = True
        else:
            print(f"[FALHA {response.status_code}] Não encontrado em: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[ERRO] Falha ao tentar acessar {url}: {e}")

if not encontrou_url:
    print("\nNenhuma URL válida foi encontrada nas tentativas.")
