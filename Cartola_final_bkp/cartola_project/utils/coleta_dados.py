import requests
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta

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


def coletar_dados_rodada_atual():
    """
    Coleta os dados dos jogadores do mercado e o mapa de clubes.
    Salva 'rodada_atual.csv' e 'clubes.json'.
    """
    try:
        response = requests.get(API_URL_MERCADO)
        response.raise_for_status()
        dados = response.json()

        # Salva o mapa de clubes
        clubes_map = {clube['id']: clube for clube in dados['clubes'].values()}
        with open(CLUBS_DATA_PATH, 'w', encoding='utf8') as f:
            json.dump(clubes_map, f, ensure_ascii=False, indent=4)
        print(f"Mapa de clubes salvo em '{CLUBS_DATA_PATH}'")
        
        # Processa e salva dados dos atletas
        atletas = dados['atletas']
        posicoes = {pos['id']: pos for pos in dados['posicoes'].values()}
        status = {s['id']: s['nome'] for s in dados['status'].values()}

        dados_atletas = []
        for atleta in atletas:
            clube = clubes_map.get(atleta['clube_id'], {})
            posicao = posicoes.get(atleta['posicao_id'], {})
            
            dados_atletas.append({
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
            })
            
            # Adiciona os scouts ao dicionário do atleta
            scouts = atleta.get('scout', {})
            if scouts:
                for scout_nome, scout_valor in scouts.items():
                    dados_atletas[-1][scout_nome] = scout_valor

        df = pd.DataFrame(dados_atletas)
        
        # Garante que todas as colunas de scouts existam
        colunas_scouts = ['G', 'A', 'FT', 'FD', 'FF', 'FS', 'PP', 'I', 'DP', 'CV', 'CA', 'GC', 'SG', 'DE', 'DS', 'GS', 'FC', 'PC']
        for col in colunas_scouts:
            if col not in df.columns:
                df[col] = 0
            df[col] = df[col].fillna(0)

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        df.to_csv(RAW_DATA_PATH, index=False, encoding='utf-8-sig')
        print(f"Dados da rodada atual coletados e salvos em '{RAW_DATA_PATH}'")
        return df

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API do Cartola FC (Mercado): {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado em 'coletar_dados_rodada_atual': {e}")
        return None

def coletar_partidas_rodada():
    """Coleta os dados das partidas da rodada atual. Salva 'partidas_rodada.csv'."""
    try:
        response = requests.get(API_URL_PARTIDAS)
        response.raise_for_status()
        dados = response.json()
        
        rodada_id = dados.get('rodada', 0)
        partidas = dados['partidas']
        
        for p in partidas:
            p['rodada_id'] = rodada_id

        df_partidas = pd.DataFrame(partidas)
        df_partidas.to_csv(MATCHES_DATA_PATH, index=False, encoding='utf-8-sig')
        
        print(f"Dados das partidas salvos em '{MATCHES_DATA_PATH}'")
        return df_partidas
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API do Cartola FC (Partidas): {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado em 'coletar_partidas_rodada': {e}")
        return None

def coletar_historico_partidas():
    """
    Baixa histórico de partidas do repositório 'adaoduque/Brasileirao_Dataset'.
    Adapta para o formato esperado pelo sistema (ID Cartola, etc.).
    """
    url = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/campeonato-brasileiro-full.csv"
    print(f"Baixando histórico de partidas de: {url}")
    
    try:
        df_raw = pd.read_csv(url)
        
        # Carrega mapa de clubes (Nome Fantasia -> ID)
        # Precisamos mapear os nomes desse dataset para os IDs do Cartola.
        # Os nomes no dataset podem ser diferentes (ex: 'Flamengo' vs 'Flamengo-RJ' ou 'Athletico Paranaense')
        # Vamos construir um mapa base e refinar.
        
        # Lista de nomes no dataset (para debug se precisar)
        # print(df_raw['mandante'].unique())
        
        # Mapa manual baseado nos nomes comuns desse dataset
        # Ajuste conforme necessário ao ver os dados reais
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
            'Mirassol': 'Mirassol', # Novo na Serie A 2025?
            'Avaí': 'Avaí', 'Chapecoense': 'Chapecoense'
        }

        # Carrega IDs oficiais do Cartola
        if os.path.exists(CLUBS_DATA_PATH):
            with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
                clubes_cartola = json.load(f)
                
            # Cria mapa: Nome Cartola -> ID Cartola
            # E também Nome Fantasia -> ID
            nome_para_id = {}
            for cid, dados in clubes_cartola.items():
                nome_para_id[dados['nome_fantasia']] = int(cid)
                nome_para_id[dados['nome']] = int(cid)
                nome_para_id[dados['apelido']] = int(cid)
                nome_para_id[dados['slug']] = int(cid)
                
            # Adiciona IDs manuais se faltar algo no JSON (ex: times rebaixados antigos)
            # Mas focamos nos times atuais para o modelo 2025
            
        else:
            print("Aviso: 'clubes.json' não encontrado. IDs podem ficar incorretos.")
            nome_para_id = {}

        # Função auxiliar de mapeamento
        def get_cartola_id(nome_dataset):
            nome_norm = mapa_nomes.get(nome_dataset, nome_dataset)
            # Tenta match exato
            if nome_norm in nome_para_id:
                return nome_para_id[nome_norm]
            
            # Tenta match parcial/fuzzy simples
            for nome_c, id_c in nome_para_id.items():
                if nome_norm.lower() in nome_c.lower() or nome_c.lower() in nome_norm.lower():
                    return id_c
            
            return None # Não encontrado (time antigo ou fora do escopo)

        df_raw['mandante_id'] = df_raw['mandante'].apply(get_cartola_id)
        df_raw['visitante_id'] = df_raw['visitante'].apply(get_cartola_id)
        
        # Filtra jogos onde conseguimos identificar ambos os times (relevantes para o modelo atual)
        df_clean = df_raw.dropna(subset=['mandante_id', 'visitante_id']).copy()
        
        # Formata colunas
        df_clean['ano'] = df_clean['data'].apply(lambda x: int(x.split('/')[2]) if isinstance(x, str) and len(x.split('/')) == 3 else 0)
        
        # Filtra anos recentes (ex: 2021 em diante) para relevância
        df_clean = df_clean[df_clean['ano'] >= 2021]
        
        # Renomeia e seleciona colunas
        df_clean.rename(columns={
            'rodata': 'rodada',
            'mandante_Placar': 'placar_mandante',
            'visitante_Placar': 'placar_visitante'
        }, inplace=True)
        
        cols_final = ['ano', 'rodada', 'mandante_id', 'visitante_id', 'placar_mandante', 'placar_visitante']
        df_final = df_clean[cols_final]
        
        # Converte IDs para int
        df_final['mandante_id'] = df_final['mandante_id'].astype(int)
        df_final['visitante_id'] = df_final['visitante_id'].astype(int)
        
        df_final.to_csv(HISTORICAL_MATCHES_PATH, index=False)
        print(f"Histórico de partidas salvo em: {HISTORICAL_MATCHES_PATH} ({len(df_final)} jogos)")
        
        # Chama a atualização de 2025 para garantir que os dados novos sejam reaplicados
        # caso o histórico antigo tenha sobrescrito o arquivo.
        atualizar_partidas_2025()
        
        return df_final

    except Exception as e:
        print(f"Erro ao coletar histórico de partidas: {e}")
        return None


def coletar_odds_partidas(api_key, force_update=False, cache_duration_hours=3):
    """Coleta as odds apenas para as partidas da rodada atual do Cartola FC."""
    if not force_update and os.path.exists(ODDS_DATA_PATH):
        file_mod_time = os.path.getmtime(ODDS_DATA_PATH)
        cache_age = datetime.now() - datetime.fromtimestamp(file_mod_time)
        if cache_age < timedelta(hours=cache_duration_hours):
            print(f"Usando dados de odds em cache.")
            try:
                return pd.read_csv(ODDS_DATA_PATH)
            except Exception as e:
                print(f"Erro ao ler o arquivo de cache de odds: {e}")

    if not api_key or api_key == "COLE_SUA_CHAVE_API_AQUI":
        return None
        
    try:
        if not all([os.path.exists(MATCHES_DATA_PATH), os.path.exists(CLUBS_DATA_PATH)]):
            return None
        
        df_partidas = pd.read_csv(MATCHES_DATA_PATH)
        with open(CLUBS_DATA_PATH, 'r', encoding='utf8') as f:
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
        response = requests.get(ODDS_API_URL, params=params)
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
            return None

        df_odds = pd.DataFrame(partidas_data)
        
        try:
            rodada_atual = df_partidas['rodada_id'].iloc[0] if 'rodada_id' in df_partidas.columns else 0
            ano_atual = datetime.now().year
            
            df_odds['rodada_id'] = rodada_atual
            df_odds['ano'] = ano_atual
            
            df_odds.to_csv(ODDS_DATA_PATH, index=False, encoding='utf-8-sig')
            
            if os.path.exists(ODDS_HISTORY_PATH):
                df_hist = pd.read_csv(ODDS_HISTORY_PATH)
                df_hist = df_hist[~((df_hist['rodada_id'] == rodada_atual) & (df_hist['ano'] == ano_atual))]
                df_final = pd.concat([df_hist, df_odds], ignore_index=True)
            else:
                df_final = df_odds
            
            df_final.to_csv(ODDS_HISTORY_PATH, index=False, encoding='utf-8-sig')
            
        except Exception as e_hist:
            df_odds.to_csv(ODDS_DATA_PATH, index=False, encoding='utf-8-sig')

        return df_odds

    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao acessar a The Odds API: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Erro inesperado em 'coletar_odds_partidas': {e}")
        return None

def get_club_id(club_name, clubes_data):
    for club_id, details in clubes_data.items():
        if details['nome_fantasia'] == club_name:
            return club_id
    return None

def atualizar_partidas_2025():
    """
    Busca os dados de partidas de 2025 da API do Globo Esporte e anexa ao histórico.
    """
    print("Iniciando a atualização das partidas de 2025 via GE...")
    
    # Carrega o mapeamento de clubes existente
    if not os.path.exists(CLUBS_DATA_PATH):
        print("Arquivo de clubes não encontrado. Execute 'coletar_dados_rodada_atual' primeiro.")
        return
        
    with open(CLUBS_DATA_PATH, 'r', encoding='utf-8') as f:
        clubes_data = json.load(f)

    # Carrega o histórico de partidas existente
    if os.path.exists(HISTORICAL_MATCHES_PATH):
        df_historico = pd.read_csv(HISTORICAL_MATCHES_PATH)
    else:
        df_historico = pd.DataFrame(columns=['ano', 'rodada', 'mandante_id', 'visitante_id', 'placar_mandante', 'placar_visitante'])

    # Filtra para garantir que não haja dados de 2025 duplicados (vamos recriar 2025)
    df_historico = df_historico[df_historico['ano'] != 2025]

    # Configuração da API do GE
    ID_CAMPEONATO = "d1a37fa4-e948-43a6-ba53-ab24ab3a45b1"
    SLUG_FASE = "fase-unica-campeonato-brasileiro-2025"
    
    new_data = []

    # Loop para buscar dados da rodada 1 até a 38
    for rodada in range(1, 39):
        url = f"https://api.globoesporte.globo.com/tabela/{ID_CAMPEONATO}/fase/{SLUG_FASE}/rodada/{rodada}/jogos"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            jogos = response.json()

            if isinstance(jogos, list):
                for jogo in jogos:
                    # Extrai dados
                    mandante_info = jogo.get('equipes', {}).get('mandante', {})
                    visitante_info = jogo.get('equipes', {}).get('visitante', {})
                    
                    # O GE já usa IDs que parecem compatíveis, mas vamos confirmar pelo nome se falhar ou usar direto
                    # No teste, São Paulo id 276 (GE) bate com 276 (Cartola).
                    # Vamos confiar no ID do GE se possível, ou fazer um fallback pelo nome.
                    
                    mandante_id = mandante_info.get('id')
                    visitante_id = visitante_info.get('id')
                    
                    placar_m = jogo.get('placar_oficial_mandante')
                    placar_v = jogo.get('placar_oficial_visitante')
                    
                    # Se o jogo não aconteceu (placar null), podemos ignorar ou colocar NaN.
                    # O histórico de partidas geralmente só tem jogos realizados.
                    if placar_m is None or placar_v is None:
                        continue

                    new_data.append({
                        'ano': 2025,
                        'rodada': rodada,
                        'mandante_id': mandante_id,
                        'visitante_id': visitante_id,
                        'placar_mandante': int(placar_m),
                        'placar_visitante': int(placar_v)
                    })
            else:
                 print(f"Estrutura inesperada para a rodada {rodada}.")

        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar dados da rodada {rodada}: {e}")
        
        # Pausa curta
        time.sleep(0.5)

    if new_data:
        df_new = pd.DataFrame(new_data)
        
        # Concatena
        df_final = pd.concat([df_historico, df_new], ignore_index=True)
        
        # Remove duplicatas
        df_final.drop_duplicates(subset=['ano', 'rodada', 'mandante_id', 'visitante_id'], keep='last', inplace=True)
        
        # Salva
        df_final.to_csv(HISTORICAL_MATCHES_PATH, index=False)
        print(f"Histórico de partidas atualizado com {len(df_new)} novos jogos de 2025 via GE. Total: {len(df_final)} jogos.")
    else:
        print("Nenhum dado novo de partidas de 2025 foi encontrado via GE.")


if __name__ == "__main__":
    coletar_dados_rodada_atual()
    coletar_partidas_rodada()
    atualizar_partidas_2025()
