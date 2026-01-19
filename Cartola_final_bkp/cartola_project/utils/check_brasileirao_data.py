import pandas as pd

url = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/campeonato-brasileiro-full.csv"
print(f"Testando dataset: {url}")

try:
    df = pd.read_csv(url)
    print("Colunas:", df.columns.tolist())
    print("Últimos anos:", df['data'].apply(lambda x: x[:4]).unique()[-5:])
    print(df.tail())
except Exception as e:
    print(f"Erro: {e}")

