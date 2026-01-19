import pandas as pd
import numpy as np
import os
import sys

# Ajusta o path para encontrar o pacote utils dentro de cartola_project
sys.path.append(os.path.join(os.getcwd(), 'cartola_project'))

from utils.config import config, logger

def simular_core(df_analise, n_simulacoes, orcamentos, pontos_alvo, top_n=None):
    """Função base para rodar a simulação de Monte Carlo."""
    resultados_rodadas = []
    medias_pontuacao_por_orcamento = {lim: [] for lim in orcamentos}
    
    rodadas = sorted(df_analise['rodada'].unique())
    
    for r in rodadas:
        df_r = df_analise[df_analise['rodada'] == r].copy()
        
        # Estrutura do Pool
        pool = {}
        for pos in [1, 2, 3, 4, 5, 6]:
            df_pos = df_r[df_r['posicao_normalizada'] == pos]
            
            # Se o filtro Top N estiver ativo, pega apenas os melhores por média acumulada
            if top_n and len(df_pos) > top_n:
                df_pos = df_pos.sort_values('media_acumulada', ascending=False).head(top_n)
            
            pool[pos] = df_pos[['pontuacao', 'preco_num']].values
        
        # Validação de pool mínimo para 4-3-3
        if any(len(pool[pos]) < count for pos, count in {1:1, 2:2, 3:2, 4:3, 5:3, 6:1}.items()):
            continue

        contadores = np.zeros((len(orcamentos), len(pontos_alvo)))
        total_validos = np.zeros(len(orcamentos))
        soma_pontos_validos = np.zeros(len(orcamentos))

        for _ in range(n_simulacoes):
            # Sorteio
            time_indices = [
                np.random.choice(len(pool[1]), 1), # GOL
                np.random.choice(len(pool[2]), 2, replace=False), # LAT
                np.random.choice(len(pool[3]), 2, replace=False), # ZAG
                np.random.choice(len(pool[4]), 3, replace=False), # MEI
                np.random.choice(len(pool[5]), 3, replace=False), # ATA
                np.random.choice(len(pool[6]), 1)  # TEC
            ]
            
            time_data = np.concatenate([pool[pos][idx] for pos, idx in zip([1,2,3,4,5,6], time_indices)])
            pontos = time_data[:, 0]
            preco_total = time_data[:, 1].sum()
            score_final = pontos.sum() + (pontos.max() * 0.5)
            
            for i, limite in enumerate(orcamentos):
                if preco_total <= limite:
                    total_validos[i] += 1
                    soma_pontos_validos[i] += score_final
                    for j, alvo in enumerate(pontos_alvo):
                        if score_final >= alvo:
                            contadores[i, j] += 1
        
        res_r = {'rodada': r}
        for i, limite in enumerate(orcamentos):
            n_v = total_validos[i] if total_validos[i] > 0 else 1
            medias_pontuacao_por_orcamento[limite].append(soma_pontos_validos[i] / n_v)
            for j, alvo in enumerate(pontos_alvo):
                res_r[f'C${limite}_pts{alvo}'] = (contadores[i, j] / n_v) * 100
        
        resultados_rodadas.append(res_r)
        
    return pd.DataFrame(resultados_rodadas), medias_pontuacao_por_orcamento

def imprimir_matriz(titulo, df_res, medias_score, orcamentos, pontos_alvo):
    print("\n" + "="*95)
    print(titulo)
    print("="*95)
    header = f"{'ORÇAMENTO':<15} | {'MÉDIA PONTOS':>15} | {'ACIMA 80 PTS':>15} | {'ACIMA 90 PTS':>15} | {'ACIMA 100 PTS':>15} |"
    print(header)
    print("-" * len(header))
    for limite in orcamentos:
        avg_score = np.mean(medias_score[limite])
        c80 = df_res[f'C${limite}_pts80'].mean()
        c90 = df_res[f'C${limite}_pts90'].mean()
        c100 = df_res[f'C${limite}_pts100'].mean()
        print(f"C$ {limite:<11} | {avg_score:>14.2f}  | {c80:>14.3f}% | {c90:>14.3f}% | {c100:>14.3f}% |")
    print("-" * len(header))

def executar_comparativo(ano=None, n_sim=20000):
    if ano is None:
        ano = config.PREVIOUS_YEAR
    caminho = config.HISTORICAL_DATA_PATH
    df = pd.read_csv(caminho, low_memory=False)
    
    # Limpeza e Normalização
    df['pontuacao'] = pd.to_numeric(df['pontuacao'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df['preco_num'] = pd.to_numeric(df['preco_num'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    mapa_pos = {'1':1,'gol':1,'Goleiro':1,'2':2,'lat':2,'Lateral':2,'3':3,'zag':3,'Zagueiro':3,
                '4':4,'mei':4,'Meia':4,'5':5,'ata':5,'Atacante':5,'6':6,'tec':6,'Técnico':6}
    df['posicao_normalizada'] = df['posicao_id'].apply(lambda x: mapa_pos.get(str(x).strip(), 0))
    
    df = df[(df['ano'] == ano) & (df['preco_num'] > 0)].copy()

    # Cálculo da Média Acumulada (Ponto chave para o cenário Expert)
    df = df.sort_values(['atleta_id', 'rodada'])
    df['media_acumulada'] = df.groupby('atleta_id')['pontuacao'].transform(lambda x: x.shift().expanding().mean()).fillna(0)
    
    # Filtro de quem jogou para a simulação
    df_jogou = df[df['pontuacao'] != 0].copy()

    orcamentos = [100, 120, 150]
    pontos_alvo = [80, 90, 100]

    print(f"🚀 Iniciando Estudo Comparativo - Temporada {ano}")
    
    # 1. Simulação Aleatória
    print("\n[1/2] Rodando Simulação Aleatória (Sorte Pura)...")
    res_aleat, med_aleat = simular_core(df_jogou, n_sim, orcamentos, pontos_alvo)
    
    # 2. Simulação Expert (Top 20)
    print("[2/2] Rodando Simulação Expert (Top 20 Médias)...")
    res_expert, med_expert = simular_core(df_jogou, n_sim, orcamentos, pontos_alvo, top_n=20)

    # Exibição dos Resultados
    imprimir_matriz(f"MATRIZ 1: SORTE PURA (Qualquer jogador que entrou em campo)", res_aleat, med_aleat, orcamentos, pontos_alvo)
    imprimir_matriz(f"MATRIZ 2: ESTRATÉGIA EXPERT (Apenas os Top 20 por média de cada posição)", res_expert, med_expert, orcamentos, pontos_alvo)
    
    # Insight de Comparação
    ganho_media = (np.mean(med_expert[120]) - np.mean(med_aleat[120]))
    chance_expert = res_expert['C$120_pts90'].mean()
    chance_aleat = res_aleat['C$120_pts90'].mean()
    multiplicador = chance_expert / chance_aleat if chance_aleat > 0 else 0
    
    print(f"\n💡 CONCLUSÃO DO ESTUDO:")
    print(f"1. Escalar por média aumenta sua pontuação média em +{ganho_media:.1f} pontos por rodada.")
    print(f"2. Sua chance de fazer 90+ pontos salta de {chance_aleat:.3f}% para {chance_expert:.3f}%.")
    print(f"3. Resultado: Você tem {multiplicador:.1f}x mais chances de mitar apenas filtrando os melhores jogadores!")
    print("="*95)

if __name__ == "__main__":
    executar_comparativo(n_sim=20000)
