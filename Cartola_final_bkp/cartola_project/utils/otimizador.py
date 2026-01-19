import pandas as pd
import os
import pulp
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary

# Define os caminhos
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
INPUT_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual_processada.csv") 

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
    # Se houver múltiplas linhas com o mesmo atleta_id, mantém apenas a primeira
    if 'atleta_id' in df_jogadores.columns:
        duplicados_antes = df_jogadores.duplicated(subset=['atleta_id'], keep=False).sum()
        if duplicados_antes > 0:
            print(f"⚠️ AVISO: {duplicados_antes} duplicatas de atleta_id encontradas no DataFrame de entrada. Removendo duplicatas...")
            # Mantém a primeira ocorrência de cada atleta_id (prioriza a com maior pontuação prevista)
            df_jogadores = df_jogadores.sort_values(coluna_pontos, ascending=False).drop_duplicates(subset=['atleta_id'], keep='first')
            print(f"✅ {duplicados_antes} duplicatas removidas. DataFrame agora tem {len(df_jogadores)} jogadores únicos.")

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
    # Se o usuário quer risco, valorizamos a volatilidade (desvio padrão)
    # Se a coluna volatilidade não existir, usa 0
    
    tem_volatilidade = 'volatilidade' in df_jogadores.columns
    
    prob += lpSum(
        (df_jogadores.loc[i, coluna_pontos] + 
         (df_jogadores.loc[i, 'volatilidade'] * fator_risco if tem_volatilidade else 0)) 
        * jogadores_vars[i] 
        for i in df_jogadores.index
    ), "Total_Valor_Esperado"

    # 4. Adicionar as restrições
    # Restrição de orçamento
    prob += lpSum(
        df_jogadores.loc[i, coluna_preco] * jogadores_vars[i] for i in df_jogadores.index
    ) <= orcamento_total, "Total_Custo"

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

    # --- RESTRIÇÕES DE TRAVAS E EXCLUSÕES ---
    
    # Fixar jogadores (Intocáveis)
    for fixo_id in jogadores_fixos:
        # Encontra o índice do jogador no DataFrame
        idx = df_jogadores.index[df_jogadores['atleta_id'] == fixo_id].tolist()
        if idx:
            prob += jogadores_vars[idx[0]] == 1, f"Fixo_{fixo_id}"
            
    # Excluir jogadores (Banidos)
    for excluido_id in jogadores_excluidos:
        idx = df_jogadores.index[df_jogadores['atleta_id'] == excluido_id].tolist()
        if idx:
            prob += jogadores_vars[idx[0]] == 0, f"Excluido_{excluido_id}"

    # 5. Resolver o problema
    # Tenta usar solver silencioso, fallback para padrão se não tiver CBC instalado corretamente
    try:
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    except:
        try:
            status = prob.solve(pulp.getSolver('PULP_CBC_CMD', msg=False))
        except:
            status = prob.solve()
    
    # Verifica se o status é ótimo
    if status != 1: # 1 = Optimal no PuLP constants
        print(f"Atenção: Solver retornou status {status} (Não Otimizado). Verifique restrições.")
        return pd.DataFrame()

    # 6. Extrair os resultados
    escalacao_indices = [i for i in df_jogadores.index if jogadores_vars[i].varValue == 1]
    escalacao_ideal = df_jogadores.loc[escalacao_indices].copy()
    
    # VALIDAÇÃO FINAL: Verifica se há duplicatas de atleta_id no resultado
    if 'atleta_id' in escalacao_ideal.columns:
        duplicados_resultado = escalacao_ideal.duplicated(subset=['atleta_id'], keep=False)
        if duplicados_resultado.any():
            print(f"⚠️ ERRO CRÍTICO: {duplicados_resultado.sum()} duplicatas de atleta_id encontradas no time escalado!")
            print("Removendo duplicatas do resultado...")
            # Remove duplicatas mantendo a primeira ocorrência
            escalacao_ideal = escalacao_ideal.drop_duplicates(subset=['atleta_id'], keep='first')
            print(f"✅ Time final tem {len(escalacao_ideal)} jogadores únicos.")
    
    # Ordena por posição
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
    
    # O técnico não pode ser capitão
    jogadores_linha = time_titular[time_titular['posicao'] != 'Técnico']
    
    if jogadores_linha.empty:
        return None
        
    # Retorna o ID ou objeto do jogador com maior pontuação
    # idxmax retorna o índice do DataFrame original
    idx_capitao = jogadores_linha[coluna_pontos].idxmax()
    return time_titular.loc[idx_capitao]

def definir_banco_reservas(df_todos, time_titular, coluna_pontos='pontuacao_prevista', coluna_preco='preco_num'):
    """
    Seleciona os reservas seguindo a regra: Preço Reserva < Menor Preço Titular da Posição.
    Estratégia 'Reserva de Luxo': Escolhe o melhor possível dentro do limite.
    """
    reservas = []
    posicoes_com_reserva = ["Goleiro", "Lateral", "Zagueiro", "Meia", "Atacante"]
    
    # IDs dos titulares para excluir da busca
    ids_titulares = time_titular['atleta_id'].tolist()
    
    for posicao in posicoes_com_reserva:
        # 1. Encontrar o titular mais barato dessa posição
        titulares_pos = time_titular[time_titular['posicao'] == posicao]
        
        if titulares_pos.empty:
            continue
            
        teto_orcamento = titulares_pos[coluna_preco].min()
        
        # 2. Filtrar candidatos no mercado
        # - Mesma posição
        # - Preço menor que o titular mais barato
        # - Não estar no time titular
        # - Provável (se tiver status)
        
        candidatos = df_todos[
            (df_todos['posicao'] == posicao) &
            (df_todos[coluna_preco] < teto_orcamento) &
            (~df_todos['atleta_id'].isin(ids_titulares))
        ].copy()
        
        if 'status' in candidatos.columns:
             # Filtra apenas prováveis ou dúvidas (opcional, mas seguro)
             # Vamos assumir que o pré-processamento já filtrou os 'Nulos'
             pass

        # 3. Escolher o melhor ('Reserva de Luxo')
        if not candidatos.empty:
            melhor_reserva = candidatos.loc[candidatos[coluna_pontos].idxmax()]
            reservas.append(melhor_reserva)
            
    if reservas:
        df_reservas = pd.DataFrame(reservas)
        # Garante a ordem das colunas
        cols_finais = ['nome', 'clube', 'posicao', 'preco_num', 'pontuacao_prevista']
        # Filtra apenas as colunas que existem no dataframe para evitar erros
        cols_existentes = [col for col in cols_finais if col in df_reservas.columns]
        return df_reservas[cols_existentes]
    else:
        return pd.DataFrame() # Retorna vazio se não achar ninguém

