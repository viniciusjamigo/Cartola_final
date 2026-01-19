import requests

def listar_primary():
    url = "https://api.github.com/repos/henriquepgomide/caRtola/contents/data/03_primary"
    try:
        resp = requests.get(url)
        items = resp.json()
        print("Conteúdo 03_primary:")
        for i in items:
            print(f"- {i['name']} ({i['type']})")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    listar_primary()
