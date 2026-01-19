import requests
import json

def explorar_raw():
    url = "https://api.github.com/repos/henriquepgomide/caRtola/contents/data/01_raw"
    print(f"Explorando: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            conteudo = response.json()
            for item in conteudo:
                print(f"- {item['name']} ({item['type']})")
                if item['type'] == 'dir':
                     # Lista conteúdo do subdiretório (provavelmente o ano)
                     resp_sub = requests.get(item['url'])
                     if resp_sub.status_code == 200:
                         print(f"  -> {[x['name'] for x in resp_sub.json()]}")
        else:
             print(f"Erro: {response.status_code}")

    except Exception as e:
        print(e)

if __name__ == "__main__":
    explorar_raw()
