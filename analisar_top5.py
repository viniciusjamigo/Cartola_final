import pandas as pd
import numpy as np
import os

def analisar_frequencia_top5():
    path = "cartola_project/data/historico_2025.csv"
    if not os.path.exists(path):
        print("Arquivo historico_2025.csv nao encontrado.")
        return

    df = pd.read_csv(path)
    
    # Garante que temos as colunas necessarias
    df['pontuacao'] = pd.to_numeric(df['pontuacao'], errors='coerce').fillna(0)
    
    # Mapeamento de nomes de posicao para facilitar
    pos_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Tecnico"}
    df['posicao_nome'] = df['posicao_id'].map(pos_map)
    
    rodadas = sorted(df['rodada'].unique())
    
    # Dicionarios para controle acumulado (resetam por ano para ser justo)
    # { (ano, atleta_id): valor }
    medalhas_contagem = {} 
    jogos_contagem = {}    
    atleta_info = {}       
    
    lista_ranking = []

    # Ordena por ano e depois por rodada
    anos = sorted(df['ano'].unique())
    
    for ano in anos:
        df_ano = df[df['ano'] == ano]
        rodadas = sorted(df_ano['rodada'].unique())
        
        for r in rodadas:
            df_r = df_ano[df_ano['rodada'] == r]
            
            # 1. Identifica os Top 5 da rodada atual
            top5_da_rodada = set()
            for pos_id in range(1, 7):
                top5 = df_r[df_r['posicao_id'] == pos_id].nlargest(5, 'pontuacao')
                for aid in top5['atleta_id'].unique():
                    top5_da_rodada.add(aid)
            
            # 2. Registra dados para quem jogou na rodada
            for _, row in df_r.iterrows():
                aid = row['atleta_id']
                key = (ano, aid)
                
                jogos_contagem[key] = jogos_contagem.get(key, 0) + 1
                if key not in atleta_info:
                    atleta_info[key] = {
                        'nome': row['apelido'],
                        'posicao': pos_map.get(row['posicao_id'], "Outros")
                    }

                medalhas = medalhas_contagem.get(key, 0)
                jogos = jogos_contagem[key]
                percentual = (medalhas / jogos) if jogos > 0 else 0
                
                lista_ranking.append({
                    'ano': ano,
                    'rodada': r,
                    'atleta_id': aid,
                    'apelido': atleta_info[key]['nome'],
                    'posicao': atleta_info[key]['posicao'],
                    'medalhas_acumuladas': medalhas,
                    'percentual_top5': round(percentual, 4)
                })
                
            # 3. Incrementa medalhas para a próxima rodada
            for aid in top5_da_rodada:
                key = (ano, aid)
                medalhas_contagem[key] = medalhas_contagem.get(key, 0) + 1

    # Resultados Finais
    df_ranking = pd.DataFrame(lista_ranking)
    
    # Salva para voce usar depois
    output_path = "cartola_project/data/feature_top5_acumulado.csv"
    df_ranking.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Arquivo {output_path} gerado com sucesso!")
    print(f"Total de registros: {len(df_ranking)}")

if __name__ == "__main__":
    analisar_frequencia_top5()
