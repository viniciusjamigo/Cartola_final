import pandas as pd
import os

# Define o caminho do workspace (usando *rea de Trabalho sem acento como o usuário pediu)
# Tenta diferentes variações do caminho
try:
    workspace = r'C:\Users\vinic\OneDrive\*rea de Trabalho\Projetos Cursor\Cartola_final'
    if os.path.exists(workspace):
        os.chdir(workspace)
except:
    # Tenta com o caminho padrão
    try:
        workspace = os.path.dirname(os.path.abspath(__file__))
        os.chdir(workspace)
    except:
        pass

# Lê o arquivo CSV
caminho_csv = 'teste.csv'
if not os.path.exists(caminho_csv):
    # Tenta com caminho completo
    caminho_csv = r'C:\Users\vinic\OneDrive\*rea de Trabalho\Projetos Cursor\Cartola_final\teste.csv'

df = pd.read_csv(caminho_csv)

# Calcula as médias das colunas solicitadas
medias = {
    'Vini (Você)': df['Vini (Você)'].mean(),
    'Máximo Possível': df['Máximo Possível'].mean(),
    'IA Nova (Com Mando)': df['IA Nova (Com Mando)'].mean(),
    'IA Legado (Sem Mando)': df['IA Legado (Sem Mando)'].mean()
}

# Cria DataFrame com as médias
df_medias = pd.DataFrame([medias])

# Mostra os resultados
print("=" * 80)
print("MÉDIAS DAS COLUNAS")
print("=" * 80)
print()
print(df_medias.to_string(index=False, float_format='%.2f'))
print()
print("=" * 80)
print(f"Total de rodadas analisadas: {len(df)}")
print("=" * 80)

