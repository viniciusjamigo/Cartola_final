import pandas as pd
import requests
import os
from io import StringIO
import json

# Mapeamento de colunas para padronização
COLUNAS_PADRAO = {
    # Identificação
    'atleta_id': 'atleta_id',
    'rodada_id': 'rodada',
    'clube_id': 'clube_id',
    'posicao_id': 'posicao_id',
    'apelido': 'apelido',
    'pontuacao': 'pontuacao',
    'pontos_num': 'pontuacao', # Mapeia pontos_num para pontuacao
    'preco_num': 'preco_num',
    'variacao_num': 'variacao_num',
    'status_id': 'status_id',
    
    # Scouts (nomes comuns na API do Cartola)
    'G': 'G', 'A': 'A', 'FT': 'FT', 'FD': 'FD', 'FF': 'FF', 'FS': 'FS', 
    'PP': 'PP', 'I': 'I', 'PE': 'PE', 'SG': 'SG', 'DP': 'DP', 'DD': 'DD', 
    'DS': 'DS', 'RB': 'DS', # RB virou DS
    'GC': 'GC', 'CV': 'CV', 'CA': 'CA', 'GS': 'GS',
    'FC': 'FC', 'DE': 'DE', 'PS': 'PS', 'V': 'V'
}

def padronizar_dataframe(df, ano):
    """Limpa e padroniza o dataframe de uma rodada."""
    # Converter nomes de colunas para minúsculo para facilitar
    df.columns = [c.lower() for c in df.columns]
    
    # Mapeamento reverso se necessário (alguns csvs usam prefixo 'atletas.')
    novas_cols = {}
    for col in df.columns:
        # Remove prefixos comuns
        clean_col = col.replace('atletas.', '').replace('scout.', '')
        
        # Tenta mapear para o padrão
        for padrao, alvo in COLUNAS_PADRAO.items():
            if clean_col == padrao.lower():
                novas_cols[col] = alvo
                break
                
    df = df.rename(columns=novas_cols)
    
    # Adiciona coluna de ano
    df['ano'] = ano
    
    # Remove colunas duplicadas (mantendo a primeira)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Filtra apenas colunas que nos interessam (que estão no dicionário alvo)
    cols_finais = [c for c in df.columns if c in COLUNAS_PADRAO.values() or c == 'ano']
    df = df[cols_finais]
    
    # Garante que scouts vazios sejam 0
    scout_cols = [c for c in df.columns if c not in ['ano', 'atleta_id', 'rodada', 'clube_id', 'posicao_id', 'apelido', 'status_id']]
    df[scout_cols] = df[scout_cols].fillna(0)
    
    return df

def baixar_dados():
    # Incluindo 2024 e 2025 na tentativa de download
    anos_padrao = [2018, 2019, 2020, 2022, 2023, 2024, 2025] 
    base_url = "https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/01_raw/{ano}/rodada-{rodada}.csv"
    
    dados_todos = []
    
    print("--- INICIANDO DOWNLOAD DE DADOS HISTÓRICOS ---")
    
    for ano in anos_padrao:
        print(f"\nBaixando {ano}...")
        for rodada in range(1, 39):
            url = base_url.format(ano=ano, rodada=rodada)
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    # Lê o CSV
                    csv_io = StringIO(r.text)
                    df = pd.read_csv(csv_io)
                    
                    # Se não tiver coluna 'rodada', adiciona
                    if 'rodada_id' not in df.columns and 'rodada' not in df.columns:
                        df['rodada'] = rodada
                        
                    df_limpo = padronizar_dataframe(df, ano)
                    dados_todos.append(df_limpo)
                    print(f".", end="", flush=True)
                else:
                    # Tenta sem hífen (ex: rodada1.csv) ou outras variações se falhar
                    print("x", end="", flush=True)
            except Exception as e:
                print(f"E", end="", flush=True)
                
    # Tentar 2021 (formato txt/json ou csv diferente)
    # O script de listagem mostrou Mercado_XX.txt. Vamos pular por simplicidade agora ou investigar depois.
    
    if not dados_todos:
        print("\nNenhum dado baixado.")
        return
        
    print("\n\nConsolidando dados...")
    df_final = pd.concat(dados_todos, ignore_index=True)
    
    # Caminho relativo ao script para ser à prova de CWD
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # Sobe um nível (sai de utils, vai para cartola_project)
    
    caminho = os.path.join(PROJECT_ROOT, "data", "historico_jogadores.csv")
    
    # Garante que a pasta existe
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    
    df_final.to_csv(caminho, index=False)
    print(f"Arquivo salvo: {caminho}")
    print(f"Total de linhas: {len(df_final)}")
    print(f"Colunas: {list(df_final.columns)}")

if __name__ == "__main__":
    baixar_dados()
