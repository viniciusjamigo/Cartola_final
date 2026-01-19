import requests
import json

def listar_conteudo_github():
    # Tenta listar o diretório 'data' do repositório
    url = "https://api.github.com/repos/henriquepgomide/caRtola/contents/data"
    
    print(f"Consultando API do GitHub: {url}")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            conteudo = response.json()
            print("\nConteúdo encontrado na pasta 'data':")
            for item in conteudo:
                print(f"- {item['name']} ({item['type']})")
                
                # Se for diretório de ano (ex: 2022), vamos ver o que tem dentro
                if item['type'] == 'dir' and item['name'].isdigit():
                    ano = item['name']
                    url_ano = f"https://api.github.com/repos/henriquepgomide/caRtola/contents/data/{ano}"
                    resp_ano = requests.get(url_ano)
                    if resp_ano.status_code == 200:
                         itens_ano = resp_ano.json()
                         print(f"  -> Dentro de {ano}:")
                         # Mostra os primeiros 3 arquivos para exemplo
                         for subitem in itens_ano[:3]:
                             print(f"     - {subitem['name']} (URL download: {subitem['download_url']})")
        else:
            print(f"Erro {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"Exceção: {e}")

if __name__ == "__main__":
    listar_conteudo_github()

