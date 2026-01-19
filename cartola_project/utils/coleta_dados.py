import requests
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.config import config, logger
from utils.validacao import validar_dados_rodada, validar_partidas

# --- MAPEAMENTO DE NOMES DE TIMES ---
# Mapeia nomes da The Odds API para os nomes da API do Cartola FC
TEAM_NAME_MAP = {
    "Flamengo RJ": "Flamengo",
    "Vasco da Gama": "Vasco",
    "Botafogo RJ": "Botafogo",
    "Sao Paulo": "São Paulo",
    "Atletico Mineiro": "Atlético-MG",
    "Athletico Paranaense": "Athletico-PR",
    "Red Bull Bragantino": "Bragantino",
    "Bragantino-SP": "Bragantino",
    "Atletico Goianiense": "Atlético-GO",
    "Vitoria": "Vitória",
    "Ceara": "Ceará",
    "Fluminense": "Fluminense",
    "Palmeiras": "Palmeiras",
    "Corinthians": "Corinthians",
    "Santos": "Santos",
    "Cruzeiro": "Cruzeiro",
    "Grêmio": "Grêmio",
    "Internacional": "Internacional",
    "Coritiba": "Coritiba",
    "Bahia": "Bahia",
    "Fortaleza": "Fortaleza",
    "Goiás": "Goiás",
    "Cuiabá": "Cuiabá",
    "Juventude": "Juventude",
    "Criciúma": "Criciúma",
    "Mirassol": "Mirassol", 
    "Sport": "Sport"
}


# --- CAMINHOS E URLs ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual.csv")
CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")
MATCHES_DATA_PATH = os.path.join(DATA_DIR, "partidas_rodada.csv")
HISTORICAL_MATCHES_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")
ODDS_DATA_PATH = os.path.join(DATA_DIR, "odds_rodada.csv")
ODDS_HISTORY_PATH = os.path.join(DATA_DIR, "historico_odds.csv")

API_URL_MERCADO = "https://api.cartolafc.globo.com/atletas/mercado"
API_URL_PARTIDAS = "https://api.cartolafc.globo.com/partidas"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato/odds"
GITHUB_BASE_URL = "https://raw.githubusercontent.com/henriquepgomide/caRtola/master/data/{ano}/{arquivo}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def coletar_dados_rodada_atual():
    """
    Coleta os dados dos jogadores do mercado e o mapa de clubes.
    Salva 'rodada_atual.csv' e 'clubes.json'.
    """
    try:
        logger.info(f"Iniciando coleta de dados do mercado: {config.API_URL_MERCADO}")
        response = requests.get(config.API_URL_MERCADO, timeout=30)
        response.raise_for_status()
        dados = response.json()

        # Salva o mapa de clubes
        clubes_map = {clube['id']: clube for clube in dados['clubes'].values()}
        with open(config.CLUBS_DATA_PATH, 'w', encoding='utf8') as f:
            json.dump(clubes_map, f, ensure_ascii=False, indent=4)
        logger.info(f"Mapa de clubes salvo em '{config.CLUBS_DATA_PATH}'")
        
        # Processa e salva dados dos atletas
        atletas = dados['atletas']
        posicoes = {pos['id']: pos for pos in dados['posicoes'].values()}
        status = {s['id']: s['nome'] for s in dados['status'].values()}

        dados_atletas = []
        for atleta in atletas:
            clube = clubes_map.get(atleta['clube_id'], {})
            posicao = posicoes.get(atleta['posicao_id'], {})
            
            item = {
                'atleta_id': atleta['atleta_id'],
                'nome': atleta['apelido'],
                'clube': clube.get('nome', 'Sem Clube'),
                'clube_id': atleta['clube_id'],
                'posicao': posicao.get('nome', 'N/A'),
                'posicao_id': atleta['posicao_id'],
                'status': status.get(atleta['status_id'], 'N/A'),
                'pontos_num': atleta['pontos_num'],
                'preco_num': atleta['preco_num'],
                'variacao_num': atleta['variacao_num'],
                'media_num': atleta['media_num'],
                'jogos_num': atleta['jogos_num'],
            }
            
            # Adiciona os scouts ao dicionário do atleta
            scouts = atleta.get('scout', {})
            if scouts:
                item.update(scouts)
            
            dados_atletas.append(item)

        df = pd.DataFrame(dados_atletas)
        
        if not validar_dados_rodada(df):
            logger.error("Dados coletados não passaram na validação de schema.")
            return None

        # Garante que todas as colunas de scouts existam
        colunas_scouts = ['G', 'A', 'FT', 'FD', 'FF', 'FS', 'PP', 'I', 'DP', 'CV', 'CA', 'GC', 'SG', 'DE', 'DS', 'GS', 'FC', 'PC']
        for col in colunas_scouts:
            if col not in df.columns:
                df[col] = 0
            df[col] = df[col].fillna(0)

        df.to_csv(config.RAW_DATA_PATH, index=False, encoding='utf-8-sig')
        logger.info(f"Dados da rodada atual coletados e salvos em '{config.RAW_DATA_PATH}'")
        return df

    except Exception as e:
        logger.error(f"Erro em 'coletar_dados_rodada_atual': {e}", exc_info=True)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def coletar_partidas_rodada():
    """Coleta os dados das partidas da rodada atual. Salva 'partidas_rodada.csv'."""
    try:
        logger.info(f"Iniciando coleta de partidas da rodada: {config.API_URL_PARTIDAS}")
        response = requests.get(config.API_URL_PARTIDAS, timeout=30)
        response.raise_for_status()
        dados = response.json()
        
        rodada_id = dados.get('rodada', 0)
        partidas = dados['partidas']
        
        for p in partidas:
            p['rodada_id'] = rodada_id

        df_partidas = pd.DataFrame(partidas)
        if not validar_partidas(df_partidas):
            logger.error("Partidas coletadas não passaram na validação de schema.")
            return None
            
        df_partidas.to_csv(config.MATCHES_DATA_PATH, index=False, encoding='utf-8-sig')
        
        logger.info(f"Dados das partidas salvos em '{config.MATCHES_DATA_PATH}'")
        return df_partidas
        
    except Exception as e:
        logger.error(f"Erro em 'coletar_partidas_rodada': {e}", exc_info=True)
        raise

def coletar_historico_partidas():
    """
    Baixa histórico de partidas do repositório 'adaoduque/Brasileirao_Dataset'.
    Adapta para o formato esperado pelo sistema (ID Cartola, etc.).
    """
    url = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/campeonato-brasileiro-full.csv"
    logger.info(f"Baixando histórico de partidas de: {url}")
    
    try:
        df_raw = pd.read_csv(url)
        
        # Mapa manual baseado nos nomes comuns desse dataset
        mapa_nomes = {
            'Flamengo': 'Flamengo', 'Vasco': 'Vasco', 'Botafogo': 'Botafogo', 'Fluminense': 'Fluminense',
            'São Paulo': 'São Paulo', 'Palmeiras': 'Palmeiras', 'Corinthians': 'Corinthians', 'Santos': 'Santos',
            'Bragantino': 'Bragantino', 'Red Bull Bragantino': 'Bragantino',
            'Atlético-MG': 'Atlético-MG', 'Atlético Mineiro': 'Atlético-MG', 
            'Cruzeiro': 'Cruzeiro', 'América-MG': 'América-MG',
            'Grêmio': 'Grêmio', 'Internacional': 'Internacional', 'Juventude': 'Juventude',
            'Athletico-PR': 'Athletico-PR', 'Athletico Paranaense': 'Athletico-PR', 'Atlético-PR': 'Athletico-PR', 'Coritiba': 'Coritiba',
            'Bahia': 'Bahia', 'Vitória': 'Vitória',
            'Fortaleza': 'Fortaleza', 'Ceará': 'Ceará',
            'Goiás': 'Goiás', 'Atlético-GO': 'Atlético-GO',
            'Cuiabá': 'Cuiabá',
            'Sport': 'Sport',
            'Criciúma': 'Criciúma',
            'Mirassol': 'Mirassol',
            'Avaí': 'Avaí', 'Chapecoense': 'Chapecoense'
        }

        # Carrega IDs oficiais do Cartola
        if os.path.exists(config.CLUBS_DATA_PATH):
            with open(config.CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                clubes_cartola = json.load(f)
                
            nome_para_id = {}
            for cid, dados in clubes_cartola.items():
                nome_para_id[dados['nome_fantasia']] = int(cid)
                nome_para_id[dados['nome']] = int(cid)
                nome_para_id[dados['apelido']] = int(cid)
                nome_para_id[dados['slug']] = int(cid)
        else:
            logger.warning(f"'{config.CLUBS_DATA_PATH}' não encontrado. IDs podem ficar incorretos.")
            nome_para_id = {}

        def get_cartola_id(nome_dataset):
            nome_norm = mapa_nomes.get(nome_dataset, nome_dataset)
            if nome_norm in nome_para_id:
                return nome_para_id[nome_norm]
            
            for nome_c, id_c in nome_para_id.items():
                if nome_norm.lower() in nome_c.lower() or nome_c.lower() in nome_norm.lower():
                    return id_c
            return None

        df_raw['mandante_id'] = df_raw['mandante'].apply(get_cartola_id)
        df_raw['visitante_id'] = df_raw['visitante'].apply(get_cartola_id)
        
        df_clean = df_raw.dropna(subset=['mandante_id', 'visitante_id']).copy()
        df_clean['ano'] = df_clean['data'].apply(lambda x: int(x.split('/')[2]) if isinstance(x, str) and len(x.split('/')) == 3 else 0)
        df_clean = df_clean[df_clean['ano'] >= 2021]
        
        df_clean.rename(columns={
            'rodata': 'rodada',
            'mandante_Placar': 'placar_mandante',
            'visitante_Placar': 'placar_visitante'
        }, inplace=True)
        
        cols_final = ['ano', 'rodada', 'mandante_id', 'visitante_id', 'placar_mandante', 'placar_visitante']
        df_final = df_clean[cols_final]
        
        df_final['mandante_id'] = df_final['mandante_id'].astype(int)
        df_final['visitante_id'] = df_final['visitante_id'].astype(int)
        
        df_final.to_csv(config.HISTORICAL_MATCHES_PATH, index=False)
        logger.info(f"Histórico de partidas salvo em: {config.HISTORICAL_MATCHES_PATH} ({len(df_final)} jogos)")
        
        atualizar_partidas_ge(config.CURRENT_YEAR)
        return df_final

    except Exception as e:
        logger.error(f"Erro ao coletar histórico de partidas: {e}", exc_info=True)
        return None


def coletar_odds_partidas(api_key, force_update=False, cache_duration_hours=3):
    """Coleta as odds apenas para as partidas da rodada atual do Cartola FC."""
    if not force_update and os.path.exists(config.ODDS_DATA_PATH):
        file_mod_time = os.path.getmtime(config.ODDS_DATA_PATH)
        cache_age = datetime.now() - datetime.fromtimestamp(file_mod_time)
        if cache_age < timedelta(hours=cache_duration_hours):
            logger.info("Usando dados de odds em cache.")
            try:
                return pd.read_csv(config.ODDS_DATA_PATH)
            except Exception as e:
                logger.error(f"Erro ao ler o arquivo de cache de odds: {e}")

    if not api_key or api_key == "COLE_SUA_CHAVE_API_AQUI":
        return None
        
    try:
        if not all([os.path.exists(config.MATCHES_DATA_PATH), os.path.exists(config.CLUBS_DATA_PATH)]):
            logger.warning("Arquivos de partidas ou clubes não encontrados para coleta de odds.")
            return None
        
        df_partidas = pd.read_csv(config.MATCHES_DATA_PATH)
        with open(config.CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
            clubes_map = {int(k): v for k, v in json.load(f).items()}
        
        confrontos_validos = set()
        for _, row in df_partidas.iterrows():
            time_casa = clubes_map.get(row['clube_casa_id'], {}).get('nome_fantasia', '')
            time_visitante = clubes_map.get(row['clube_visitante_id'], {}).get('nome_fantasia', '')
            if time_casa and time_visitante:
                confrontos_validos.add(tuple(sorted((time_casa, time_visitante))))
        
        params = {
            'apiKey': api_key,
            'regions': 'eu', 
            'markets': 'h2h', 
            'oddsFormat': 'decimal'
        }
        logger.info(f"Coletando odds da API: {config.ODDS_API_URL}")
        response = requests.get(config.ODDS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        dados_odds = response.json()
        partidas_data = []
        for partida in dados_odds:
            time_casa_raw = partida['home_team']
            time_visitante_raw = partida['away_team']
            time_casa_norm = TEAM_NAME_MAP.get(time_casa_raw, time_casa_raw)
            time_visitante_norm = TEAM_NAME_MAP.get(time_visitante_raw, time_visitante_raw)

            if tuple(sorted((time_casa_norm, time_visitante_norm))) not in confrontos_validos:
                continue

            bookmaker = partida['bookmakers'][0]
            odds = bookmaker['markets'][0]['outcomes']
            
            partidas_data.append({
                'time_casa': time_casa_norm,
                'time_visitante': time_visitante_norm,
                'odd_casa': odds[0]['price'],
                'odd_empate': odds[1]['price'],
                'odd_visitante': odds[2]['price'],
            })

        if not partidas_data:
            logger.warning("Nenhuma odd encontrada para os confrontos da rodada.")
            return None

        df_odds = pd.DataFrame(partidas_data)
        
        try:
            rodada_atual = df_partidas['rodada_id'].iloc[0] if 'rodada_id' in df_partidas.columns else 0
            ano_atual = datetime.now().year
            
            df_odds['rodada_id'] = rodada_atual
            df_odds['ano'] = ano_atual
            
            df_odds.to_csv(config.ODDS_DATA_PATH, index=False, encoding='utf-8-sig')
            
            if os.path.exists(config.ODDS_HISTORY_PATH):
                df_hist = pd.read_csv(config.ODDS_HISTORY_PATH)
                df_hist = df_hist[~((df_hist['rodada_id'] == rodada_atual) & (df_hist['ano'] == ano_atual))]
                df_final = pd.concat([df_hist, df_odds], ignore_index=True)
            else:
                df_final = df_odds
            
            df_final.to_csv(config.ODDS_HISTORY_PATH, index=False, encoding='utf-8-sig')
            logger.info("Odds e histórico de odds atualizados.")
            
        except Exception as e_hist:
            logger.error(f"Erro ao atualizar histórico de odds: {e_hist}")
            df_odds.to_csv(config.ODDS_DATA_PATH, index=False, encoding='utf-8-sig')

        return df_odds

    except Exception as e:
        logger.error(f"Erro em 'coletar_odds_partidas': {e}", exc_info=True)
        return None

def get_club_id(club_name, clubes_data):
    for club_id, details in clubes_data.items():
        if details['nome_fantasia'] == club_name:
            return club_id
    return None

def atualizar_partidas_ge(ano=None):
    """
    Busca os dados de partidas de um determinado ano da API do Globo Esporte e anexa ao histórico.
    """
    if ano is None:
        ano = config.CURRENT_YEAR
        
    logger.info(f"Iniciando a atualização das partidas de {ano} via GE...")
    
    if not os.path.exists(config.CLUBS_DATA_PATH):
        logger.error(f"Arquivo de clubes não encontrado em '{config.CLUBS_DATA_PATH}'.")
        return
        
    with open(config.CLUBS_DATA_PATH, 'r', encoding='utf-8') as f:
        clubes_data = json.load(f)

    if os.path.exists(config.HISTORICAL_MATCHES_PATH):
        df_historico = pd.read_csv(config.HISTORICAL_MATCHES_PATH)
    else:
        df_historico = pd.DataFrame(columns=['ano', 'rodada', 'mandante_id', 'visitante_id', 'placar_mandante', 'placar_visitante'])

    # Remove dados do ano atual para atualizar com os mais recentes
    df_historico = df_historico[df_historico['ano'] != ano]

    # Configuração da API do GE
    # Nota: ID_CAMPEONATO pode mudar em 2026, mas geralmente é estável. 
    # SLUG_FASE segue o padrão 'fase-unica-campeonato-brasileiro-YYYY'
    ID_CAMPEONATO = "d1a37fa4-e948-43a6-ba53-ab24ab3a45b1"
    SLUG_FASE = f"fase-unica-campeonato-brasileiro-{ano}"
    
    new_data = []

    for rodada in range(1, 39):
        url = f"https://api.globoesporte.globo.com/tabela/{ID_CAMPEONATO}/fase/{SLUG_FASE}/rodada/{rodada}/jogos"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 404:
                # Se der 404, provavelmente a rodada ou a fase ainda não existem (início de campeonato)
                continue
            response.raise_for_status()
            jogos = response.json()

            if isinstance(jogos, list):
                for jogo in jogos:
                    mandante_info = jogo.get('equipes', {}).get('mandante', {})
                    visitante_info = jogo.get('equipes', {}).get('visitante', {})
                    
                    mandante_id = mandante_info.get('id')
                    visitante_id = visitante_info.get('id')
                    
                    placar_m = jogo.get('placar_oficial_mandante')
                    placar_v = jogo.get('placar_oficial_visitante')
                    
                    if placar_m is None or placar_v is None:
                        continue

                    new_data.append({
                        'ano': ano,
                        'rodada': rodada,
                        'mandante_id': mandante_id,
                        'visitante_id': visitante_id,
                        'placar_mandante': int(placar_m),
                        'placar_visitante': int(placar_v)
                    })
            else:
                 logger.warning(f"Estrutura inesperada para a rodada {rodada}.")

        except Exception as e:
            # Em início de temporada, erros aqui são comuns pois a tabela ainda não foi criada na API
            logger.debug(f"Aviso: Não foi possível buscar dados da rodada {rodada} (Campeonato pode não ter começado): {e}")
        
        time.sleep(0.1)

    if new_data:
        df_new = pd.DataFrame(new_data)
        df_final = pd.concat([df_historico, df_new], ignore_index=True)
        df_final.drop_duplicates(subset=['ano', 'rodada', 'mandante_id', 'visitante_id'], keep='last', inplace=True)
        df_final.to_csv(config.HISTORICAL_MATCHES_PATH, index=False)
        logger.info(f"Histórico de partidas atualizado com {len(df_new)} novos jogos de {ano}. Total: {len(df_final)} jogos.")
    else:
        logger.info(f"Nenhum dado novo de partidas de {ano} foi encontrado via GE.")


if __name__ == "__main__":
    coletar_dados_rodada_atual()
    coletar_partidas_rodada()
    atualizar_partidas_ge(config.CURRENT_YEAR)
