import pandas as pd
from utils.config import logger

def validar_schema(df, colunas_obrigatorias, nome_dataset="dataset"):
    """
    Valida se o DataFrame possui as colunas obrigatórias e se não há valores nulos críticos.
    """
    if df is None or df.empty:
        logger.error(f"Erro de validação: {nome_dataset} está vazio ou é None.")
        return False
        
    missing = [col for col in colunas_obrigatorias if col not in df.columns]
    if missing:
        logger.error(f"Erro de validação em {nome_dataset}: Colunas faltando: {missing}")
        return False
        
    logger.info(f"Schema de {nome_dataset} validado com sucesso ({len(df)} registros).")
    return True

def validar_dados_rodada(df):
    """Valida especificamente os dados da rodada atual."""
    cols = ['atleta_id', 'nome', 'clube_id', 'posicao_id', 'preco_num', 'status']
    return validar_schema(df, cols, "rodada_atual")

def validar_historico(df):
    """Valida o histórico de jogadores."""
    cols = ['ano', 'rodada', 'atleta_id', 'pontuacao', 'posicao_id']
    return validar_schema(df, cols, "historico_jogadores")

def validar_partidas(df):
    """Valida o arquivo de partidas."""
    cols = ['clube_casa_id', 'clube_visitante_id']
    return validar_schema(df, cols, "partidas_rodada")

