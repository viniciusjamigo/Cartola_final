import pandas as pd
import numpy as np
import os

def calcular_probabilidade_sg():
    path = "cartola_project/data/historico_partidas.csv"
    if not os.path.exists(path):
        print("Arquivo historico_partidas.csv nao encontrado.")
        return

    df = pd.read_csv(path)
    
    # Ordenar para garantir cronologia
    df = df.sort_values(['ano', 'rodada'])
    
    lista_sg = []
    
    # Dicionários para guardar histórico de gols (dinâmico)
    # { (ano, time_id): [lista de gols marcados/sofridos] }
    gols_feitos_mandante = {}
    gols_sofridos_mandante = {}
    gols_feitos_visitante = {}
    gols_sofridos_visitante = {}

    for _, row in df.iterrows():
        ano = int(row['ano'])
        rodada = int(row['rodada'])
        m_id = int(row['mandante_id'])
        v_id = int(row['visitante_id'])
        m_gols = row['placar_mandante']
        v_gols = row['placar_visitante']
        
        # --- CÁLCULO DAS PROBABILIDADES (Antes de computar o resultado desta partida) ---
        
        def get_prob_sg_defesa(time_id, ano, local='mandante'):
            # Local: 'mandante' ou 'visitante'
            key = (ano, time_id)
            if local == 'mandante':
                sofridos = gols_sofridos_mandante.get(key, [])
            else:
                sofridos = gols_sofridos_visitante.get(key, [])
            
            if not sofridos: return 0.5 # Fallback: 50%
            # Probabilidade = Jogos com 0 gols sofridos / Total de jogos
            # Damos peso maior para os últimos 5 jogos (rolling 5)
            last_5 = sofridos[-5:]
            return last_5.count(0) / len(last_5)

        def get_prob_sg_ataque_adversario(time_id, ano, local='visitante'):
            # local: onde o ADVERSÁRIO está jogando
            key = (ano, time_id)
            if local == 'visitante':
                feitos = gols_feitos_visitante.get(key, [])
            else:
                feitos = gols_feitos_mandante.get(key, [])
                
            if not feitos: return 0.5
            # Probabilidade do adversário NÃO marcar = Jogos com 0 gols feitos / Total
            last_5 = feitos[-5:]
            return last_5.count(0) / len(last_5)

        # Probabilidade para o Mandante segurar SG
        prob_def_m = get_prob_sg_defesa(m_id, ano, 'mandante')
        prob_adv_v = get_prob_sg_ataque_adversario(v_id, ano, 'visitante')
        # Média entre a solidez da defesa e a inofensividade do ataque adversário
        prob_sg_mandante = (prob_def_m + prob_adv_v) / 2
        
        # Probabilidade para o Visitante segurar SG
        prob_def_v = get_prob_sg_defesa(v_id, ano, 'visitante')
        prob_adv_m = get_prob_sg_ataque_adversario(m_id, ano, 'mandante')
        prob_sg_visitante = (prob_def_v + prob_adv_m) / 2

        lista_sg.append({
            'ano': ano,
            'rodada': rodada,
            'clube_id': m_id,
            'probabilidade_sg': round(prob_sg_mandante, 4)
        })
        lista_sg.append({
            'ano': ano,
            'rodada': rodada,
            'clube_id': v_id,
            'probabilidade_sg': round(prob_sg_visitante, 4)
        })

        # --- ATUALIZAÇÃO DO HISTÓRICO (Para as próximas rodadas) ---
        key_m = (ano, m_id)
        key_v = (ano, v_id)
        
        gols_feitos_mandante.setdefault(key_m, []).append(m_gols)
        gols_sofridos_mandante.setdefault(key_m, []).append(v_gols)
        gols_feitos_visitante.setdefault(key_v, []).append(v_gols)
        gols_sofridos_visitante.setdefault(key_v, []).append(m_gols)

    df_sg = pd.DataFrame(lista_sg)
    output_path = "cartola_project/data/feature_probabilidade_sg.csv"
    df_sg.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Arquivo {output_path} gerado com sucesso!")

if __name__ == "__main__":
    calcular_probabilidade_sg()

