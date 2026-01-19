import os
import sys
import argparse
from datetime import datetime

# Garante que conseguimos importar dos subdiretórios
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'cartola_project', 'utils')))

# Imports das funções dos módulos existentes
try:
    from coleta_dados import coletar_dados_rodada_atual, coletar_partidas_rodada, coletar_odds_partidas, atualizar_partidas_2025
    from coleta_historico import coletar_dados_historicos
    from consolidar_tudo import consolidar
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique se a estrutura de diretórios está correta.")
    sys.exit(1)

def atualizar_tudo(rodada_finalizada, odds_api_key=None):
    """
    Orquestra a atualização completa do sistema.
    
    Args:
        rodada_finalizada (int): O número da rodada que acabou de acontecer (ex: 34).
                                 Os dados históricos serão atualizados até esta rodada.
        odds_api_key (str): Chave da API de Odds (opcional).
    """
    print(f"\n=== INICIANDO ATUALIZAÇÃO DO SISTEMA ===")
    print(f"Rodada Finalizada (alvo da coleta histórica): {rodada_finalizada}")
    print(f"Próxima Rodada (alvo da coleta de mercado/odds): {rodada_finalizada + 1}")
    
    # 1. Atualizar Histórico de Partidas
    # Busca placares do GE para ter os resultados reais da rodada que acabou
    print("\n" + "="*50)
    print("1. ATUALIZANDO HISTÓRICO DE PARTIDAS (GE)")
    print("="*50)
    try:
        atualizar_partidas_2025()
    except Exception as e:
        print(f"Erro ao atualizar partidas: {e}")

    # 2. Atualizar Histórico de Jogadores
    # Baixa pontuações de todos os jogadores até a rodada finalizada
    print("\n" + "="*50)
    print(f"2. ATUALIZANDO HISTÓRICO DE JOGADORES (Até rodada {rodada_finalizada})")
    print("="*50)
    try:
        # Salva em historico_2025.csv (conforme alteração feita no coleta_historico.py)
        coletar_dados_historicos(ano=2025, total_rodadas=rodada_finalizada)
    except Exception as e:
        print(f"Erro ao coletar histórico de jogadores: {e}")

    # 3. Consolidar Dados
    # Junta o histórico antigo (2018-2024) com o novo (2025)
    print("\n" + "="*50)
    print("3. CONSOLIDANDO BASES DE DADOS")
    print("="*50)
    try:
        consolidar()
    except Exception as e:
        print(f"Erro ao consolidar dados: {e}")

    # 4. Coletar Dados da Rodada Atual (Mercado)
    # Pega os dados do mercado aberto para a PRÓXIMA rodada
    print("\n" + "="*50)
    print("4. COLETANDO DADOS DO MERCADO (Próxima Rodada)")
    print("="*50)
    try:
        coletar_dados_rodada_atual() # Salva rodada_atual.csv
        coletar_partidas_rodada()    # Salva partidas_rodada.csv (jogos da próxima rodada)
    except Exception as e:
        print(f"Erro ao coletar dados do mercado: {e}")

    # 5. Coletar Odds
    # Pega as odds para a próxima rodada
    print("\n" + "="*50)
    print("5. COLETANDO ODDS")
    print("="*50)
    if odds_api_key:
        try:
            coletar_odds_partidas(api_key=odds_api_key, force_update=True)
        except Exception as e:
            print(f"Erro ao coletar odds: {e}")
    else:
        print("Pulo: Nenhuma chave de API de Odds fornecida.")

    print("\n" + "="*50)
    print("=== ATUALIZAÇÃO CONCLUÍDA ===")
    print("="*50)
    print(f"Agora você pode rodar o script de previsão ou retreinamento.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza os dados do Cartola FC para a virada de rodada.")
    parser.add_argument("--rodada", type=int, required=True, help="Número da última rodada FINALIZADA (ex: 34 se vamos para a 35)")
    parser.add_argument("--odds_key", type=str, help="Chave da The Odds API (opcional)")
    
    args = parser.parse_args()
    
    atualizar_tudo(args.rodada, args.odds_key)

