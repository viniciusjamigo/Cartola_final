import pandas as pd
import os
import pulp
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary
from utils.config import config, logger

def otimizar_escalacao(
    df_jogadores, 
    coluna_pontos='pontuacao_prevista', 
    coluna_preco='preco_num',
    orcamento_total=100,
    formacao_t_str="4-3-3",
    fator_risco=0.0, # Novo parâmetro: 0.0 (Seguro) a 1.0 (Arriscado)
    jogadores_fixos=None, # Lista de IDs de jogadores que DEVEM estar no time
    jogadores_excluidos=None # Lista de IDs de jogadores que NÃO podem estar no time
):
    """
    Otimiza a escalação do time do Cartola FC.
    """
    
    if jogadores_fixos is None: jogadores_fixos = []
    if jogadores_excluidos is None: jogadores_excluidos = []

    # VALIDAÇÃO: Remove duplicatas de atleta_id antes da otimização
    if 'atleta_id' in df_jogadores.columns:
        duplicados_antes = df_jogadores.duplicated(subset=['atleta_id'], keep=False).sum()
        if duplicados_antes > 0:
            logger.warning(f"{duplicados_antes} duplicatas de atleta_id encontradas. Removendo...")
            df_jogadores = df_jogadores.sort_values(coluna_pontos, ascending=False).drop_duplicates(subset=['atleta_id'], keep='first')

    map_posicao = {
        "4-3-3": {"Goleiro": 1, "Lateral": 2, "Zagueiro": 2, "Meia": 3, "Atacante": 3, "Técnico": 1},
        "4-4-2": {"Goleiro": 1, "Lateral": 2, "Zagueiro": 2, "Meia": 4, "Atacante": 2, "Técnico": 1},
        "3-4-3": {"Goleiro": 1, "Zagueiro": 3, "Meia": 4, "Atacante": 3, "Técnico": 1},
        "3-5-2": {"Goleiro": 1, "Zagueiro": 3, "Meia": 5, "Atacante": 2, "Técnico": 1},
    }
    
    if formacao_t_str not in map_posicao:
        raise ValueError("Formação tática inválida.")
        
    formacao_t = map_posicao[formacao_t_str]
    
    # 1. Definir o problema
    prob = LpProblem("OtimizacaoCartolaFC", LpMaximize)
    
    # 2. Criar as variáveis de decisão
    jogadores_vars = LpVariable.dicts(
        "Jogador", df_jogadores.index, cat=LpBinary
    )

    # 3. Definir a função objetivo (Maximizar Pontos + Bônus de Risco)
    tem_volatilidade = 'volatilidade' in df_jogadores.columns
    
    prob += lpSum(
        (float(df_jogadores.loc[i, coluna_pontos]) + 
         (float(df_jogadores.loc[i, 'volatilidade']) * float(fator_risco) if tem_volatilidade else 0.0)) 
        * jogadores_vars[i] 
        for i in df_jogadores.index
    ), "Total_Valor_Esperado"

    # 4. Adicionar as restrições
    # Restrição de orçamento
    prob += lpSum(
        float(df_jogadores.loc[i, coluna_preco]) * jogadores_vars[i] for i in df_jogadores.index
    ) <= float(orcamento_total), "Total_Custo"

    # Restrição de número de jogadores por posição
    for posicao, numero in formacao_t.items():
        prob += lpSum(
            jogadores_vars[i] for i in df_jogadores.index if df_jogadores.loc[i, 'posicao'] == posicao
        ) == numero, f"Num_{posicao.replace(' ', '_')}"

    # Restrição de no máximo 5 jogadores por clube
    for clube in df_jogadores['clube'].unique():
        prob += lpSum(
            jogadores_vars[i] for i in df_jogadores.index if df_jogadores.loc[i, 'clube'] == clube
        ) <= 5, f"Max_Jogadores_{clube.replace(' ', '_').replace('.', '')}"

    # Fixar jogadores (Intocáveis)
    for fixo_id in jogadores_fixos:
        idx = df_jogadores.index[df_jogadores['atleta_id'] == fixo_id].tolist()
        if idx:
            prob += jogadores_vars[idx[0]] == 1, f"Fixo_{fixo_id}"
            
    # Excluir jogadores (Banidos)
    for excluido_id in jogadores_excluidos:
        idx = df_jogadores.index[df_jogadores['atleta_id'] == excluido_id].tolist()
        if idx:
            prob += jogadores_vars[idx[0]] == 0, f"Excluido_{excluido_id}"

    # 5. Resolver o problema
    try:
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    except:
        try:
            status = prob.solve(pulp.getSolver('PULP_CBC_CMD', msg=False))
        except:
            status = prob.solve()
    
    if status != 1: # 1 = Optimal
        logger.error(f"Erro: Solver retornou status {status} (Não Otimizado).")
        return pd.DataFrame()

    # 6. Extrair os resultados
    escalacao_indices = [i for i in df_jogadores.index if jogadores_vars[i].varValue == 1]
    escalacao_ideal = df_jogadores.loc[escalacao_indices].copy()
    
    if 'atleta_id' in escalacao_ideal.columns:
        duplicados_resultado = escalacao_ideal.duplicated(subset=['atleta_id'], keep=False)
        if duplicados_resultado.any():
            print(f"⚠️ ERRO CRÍTICO: {duplicados_resultado.sum()} duplicatas de atleta_id encontradas no time escalado!")
            escalacao_ideal = escalacao_ideal.drop_duplicates(subset=['atleta_id'], keep='first')
    
    posicao_ordem = ["Goleiro", "Lateral", "Zagueiro", "Meia", "Atacante", "Técnico"]
    escalacao_ideal['posicao'] = pd.Categorical(escalacao_ideal['posicao'], categories=posicao_ordem, ordered=True)
    escalacao_ideal.sort_values('posicao', inplace=True)

    return escalacao_ideal

def definir_capitao(time_titular, coluna_pontos='pontuacao_prevista'):
    """
    Escolhe o capitão baseado na maior pontuação prevista.
    """
    if time_titular.empty:
        return None
    
    jogadores_linha = time_titular[time_titular['posicao'] != 'Técnico']
    
    if jogadores_linha.empty:
        return None
        
    idx_capitao = jogadores_linha[coluna_pontos].idxmax()
    return time_titular.loc[idx_capitao]

def definir_banco_reservas(df_todos, time_titular, coluna_pontos='pontuacao_prevista', coluna_preco='preco_num'):
    """
    Seleciona os reservas seguindo a regra: Preço Reserva < Menor Preço Titular da Posição.
    """
    reservas = []
    posicoes_com_reserva = ["Goleiro", "Lateral", "Zagueiro", "Meia", "Atacante"]
    
    ids_titulares = time_titular['atleta_id'].tolist()
    
    for posicao in posicoes_com_reserva:
        titulares_pos = time_titular[time_titular['posicao'] == posicao]
        
        if titulares_pos.empty:
            continue
            
        teto_orcamento = titulares_pos[coluna_preco].min()
        
        candidatos = df_todos[
            (df_todos['posicao'] == posicao) &
            (df_todos[coluna_preco] < teto_orcamento) &
            (~df_todos['atleta_id'].isin(ids_titulares))
        ].copy()
        
        if not candidatos.empty:
            melhor_reserva = candidatos.loc[candidatos[coluna_pontos].idxmax()]
            reservas.append(melhor_reserva)
            
    if reservas:
        df_reservas = pd.DataFrame(reservas)
        cols_finais = ['nome', 'clube', 'posicao', 'preco_num', 'pontuacao_prevista']
        cols_existentes = [col for col in cols_finais if col in df_reservas.columns]
        return df_reservas[cols_existentes]
    else:
        return pd.DataFrame()
