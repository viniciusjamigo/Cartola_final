"""
Script para coletar dados do FBref usando a biblioteca soccerdata.

Este script coleta:
- Dados dos clubes da Série A do Brasileirão
- Dados dos jogadores desses clubes
- Estatísticas avançadas (xG, xA, escanteios, etc.)

Requisitos:
    pip install soccerdata

Nota: O FBref tem rate limiting (1 requisição a cada 6 segundos).
Este script respeita essa limitação automaticamente.
"""

import os
import sys
import pandas as pd
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Tenta importar cloudscraper para contornar proteção anti-bot
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

# Tenta importar Selenium como alternativa
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Adiciona o diretório do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Tenta importar soccerdata
try:
    from soccerdata import FBref
    SOCCERDATA_AVAILABLE = True
except ImportError:
    SOCCERDATA_AVAILABLE = False
    print("AVISO: Biblioteca 'soccerdata' nao encontrada.")
    print("Instale com: pip install soccerdata")

# --- CAMINHOS ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FBREF_DIR = os.path.join(DATA_DIR, "fbref")
os.makedirs(FBREF_DIR, exist_ok=True)

# Caminhos dos arquivos de saída
CLUBES_FBREF_PATH = os.path.join(FBREF_DIR, "fbref_clubes_serie_a.csv")
JOGADORES_FBREF_PATH = os.path.join(FBREF_DIR, "fbref_jogadores_serie_a.csv")
ESTATISTICAS_TIMES_PATH = os.path.join(FBREF_DIR, "fbref_estatisticas_times.csv")


def mapear_ano_para_temporada(ano):
    """
    Mapeia o ano para o formato de temporada do FBref.
    Exemplo: 2025 -> '2024-2025' ou '2025'
    """
    # FBref geralmente usa formato '2024-2025' para temporadas
    # Mas também aceita apenas o ano
    return str(ano)


def coletar_dados_fbref_selenium(ano=2025, tipo='times'):
    """
    Coleta dados do FBref usando Selenium (contorna proteção anti-bot).
    
    Args:
        ano: Ano da temporada
        tipo: 'times' ou 'jogadores'
    
    Returns:
        DataFrame com os dados coletados ou None
    """
    if not SELENIUM_AVAILABLE:
        print("AVISO: Selenium nao esta disponivel. Instale com: pip install selenium")
        return None
    
    try:
        print(f"\nTentando coleta com Selenium...")
        
        # Configura opções do Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Executa em background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # URLs possíveis
        urls_tentativas = [
            "https://fbref.com/en/comps/24",
            f"https://fbref.com/en/comps/24/{ano}-Serie-A-Stats",
            "https://fbref.com/en/comps/24/Serie-A-Stats"
        ]
        
        driver = None
        for url in urls_tentativas:
            try:
                print(f"Tentando URL com Selenium: {url}")
                
                # Cria driver (usa ChromeDriver que deve estar no PATH)
                driver = webdriver.Chrome(options=chrome_options)
                driver.get(url)
                
                # Aguarda a página carregar
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                # Obtém o HTML da página
                html = driver.page_source
                
                # Parse com BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Procura tabelas
                tabelas = soup.find_all('table', class_='stats_table')
                
                if tabelas:
                    print(f"SUCESSO: Encontradas {len(tabelas)} tabelas")
                    
                    # Extrai dados da primeira tabela
                    if tipo == 'times' and len(tabelas) > 0:
                        df = pd.read_html(str(tabelas[0]))[0]
                        print(f"SUCESSO: Extraidos {len(df)} registros de times")
                        driver.quit()
                        return df
                    elif tipo == 'jogadores':
                        # Procura tabela de jogadores (pode ter várias)
                        # Geralmente a primeira tabela grande com muitos registros é a de jogadores
                        dfs_jogadores = []
                        for i, tabela in enumerate(tabelas):
                            try:
                                df_temp = pd.read_html(str(tabela))[0]
                                # Verifica se parece ser uma tabela de jogadores
                                colunas_lower = [str(col).lower() for col in df_temp.columns]
                                if any(keyword in ' '.join(colunas_lower) for keyword in ['player', 'name', 'jogador', 'squad', 'team']):
                                    if len(df_temp) > 5:  # Tabela com muitos registros
                                        print(f"Tabela {i+1}: {len(df_temp)} registros encontrados")
                                        dfs_jogadores.append(df_temp)
                            except Exception as e:
                                print(f"AVISO: Erro ao processar tabela {i+1}: {e}")
                                continue
                        
                        if dfs_jogadores:
                            # Combina todas as tabelas de jogadores encontradas
                            df_final = pd.concat(dfs_jogadores, ignore_index=True)
                            print(f"SUCESSO: Extraidos {len(df_final)} registros de jogadores (de {len(dfs_jogadores)} tabelas)")
                            driver.quit()
                            return df_final
                        else:
                            # Se não encontrou, tenta a primeira tabela grande
                            if len(tabelas) > 1:
                                df_temp = pd.read_html(str(tabelas[1]))[0]
                                if len(df_temp) > 10:
                                    print(f"SUCESSO: Extraidos {len(df_temp)} registros de jogadores (tabela alternativa)")
                                    driver.quit()
                                    return df_temp
                
                driver.quit()
                break
                
            except Exception as e:
                print(f"AVISO: Erro ao acessar {url} com Selenium: {e}")
                if driver:
                    driver.quit()
                continue
        
        print("ERRO: Nao foi possivel coletar dados com Selenium")
        return None
        
    except Exception as e:
        print(f"ERRO ao usar Selenium: {e}")
        if driver:
            driver.quit()
        import traceback
        traceback.print_exc()
        return None


def coletar_dados_fbref_direto(ano=2025, tipo='times'):
    """
    Coleta dados diretamente do FBref usando scraping.
    URL base: https://fbref.com/en/comps/24/Serie-A-Stats
    
    Args:
        ano: Ano da temporada
        tipo: 'times' ou 'jogadores'
    
    Returns:
        DataFrame com os dados coletados ou None
    """
    try:
        # URLs possíveis do FBref para Série A do Brasil
        # URL confirmada: https://fbref.com/en/comps/24
        urls_tentativas = [
            "https://fbref.com/en/comps/24",  # URL base confirmada
            f"https://fbref.com/en/comps/24/{ano}-Serie-A-Stats",
            "https://fbref.com/en/comps/24/Serie-A-Stats"
        ]
        
        print(f"\nTentando coleta direta do FBref via scraping...")
        
        response = None
        base_url = None
        
        # Tenta cada URL até uma funcionar
        for url in urls_tentativas:
            try:
                print(f"Tentando URL: {url}")
                if CLOUDSCRAPER_AVAILABLE:
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, timeout=30)
                else:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                base_url = url
                print(f"SUCESSO: Conseguiu acessar {url}")
                break
            except Exception as e:
                print(f"AVISO: Falha ao acessar {url}: {e}")
                continue
        
        if response is None or base_url is None:
            # Se cloudscraper falhar, tenta Selenium
            print("\nTentando com Selenium como alternativa...")
            return coletar_dados_fbref_selenium(ano=ano, tipo=tipo)
        
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Procura por tabelas de estatísticas
        # O FBref usa tabelas com classe 'stats_table'
        tabelas = soup.find_all('table', class_='stats_table')
        
        if not tabelas:
            print("AVISO: Nenhuma tabela encontrada na página")
            return None
        
        print(f"Encontradas {len(tabelas)} tabelas na página")
        
        # Tenta extrair dados da primeira tabela (geralmente é a de times)
        if tipo == 'times' and len(tabelas) > 0:
            # Extrai a tabela de times
            df = pd.read_html(str(tabelas[0]))[0]
            print(f"SUCESSO: Extraídos {len(df)} registros de times")
            return df
        elif tipo == 'jogadores' and len(tabelas) > 1:
            # Tenta encontrar tabela de jogadores
            for tabela in tabelas:
                df = pd.read_html(str(tabela))[0]
                # Verifica se parece ser uma tabela de jogadores (tem coluna 'Player')
                if 'Player' in df.columns or 'player' in df.columns:
                    print(f"SUCESSO: Extraídos {len(df)} registros de jogadores")
                    return df
        
        print("AVISO: Não foi possível identificar a tabela correta")
        return None
        
    except Exception as e:
        print(f"ERRO ao fazer scraping direto: {e}")
        import traceback
        traceback.print_exc()
        return None


def coletar_dados_clubes_serie_a(ano=2025):
    """
    Coleta dados dos clubes da Série A do Brasileirão.
    
    Returns:
        DataFrame com dados dos clubes ou None se houver erro
    """
    if not SOCCERDATA_AVAILABLE:
        print("ERRO: soccerdata nao esta disponivel. Instale com: pip install soccerdata")
        return None
    
    try:
        print(f"\n{'='*60}")
        print(f"Coletando dados dos CLUBES da Série A - {ano}")
        print(f"{'='*60}")
        
        # Código da liga no FBref para Série A do Brasil
        # Baseado na URL: https://fbref.com/en/comps/24/Serie-A-Stats
        # Nota: O código 24 é da Série A italiana, o código 37 pode ser do Brasileirão
        # Tentativas com diferentes códigos possíveis
        codigos_liga = ['37', '24', 'BRA-SerieA', 'BRA1', 'BRA-Serie-A', 'Serie-A-Stats']
        temporada = mapear_ano_para_temporada(ano)
        
        print(f"Temporada: {temporada}")
        print("Aguarde... (respeitando rate limiting do FBref)")
        
        df_times = None
        codigo_liga_usado = None
        
        # Tenta diferentes códigos de liga
        for codigo in codigos_liga:
            try:
                print(f"\nTentando código de liga: {codigo}")
                # Cria instância do FBref
                # O soccerdata automaticamente respeita rate limiting
                fbref = FBref(
                    leagues=[codigo],
                    seasons=[temporada]
                )
                
                # Coleta estatísticas dos times
                print("Coletando estatísticas dos times...")
                df_times = fbref.read_team_stats()
                
                if df_times is not None and not df_times.empty:
                    codigo_liga_usado = codigo
                    print(f"SUCESSO com codigo: {codigo}")
                    break
                else:
                    print(f"AVISO: Nenhum dado encontrado com codigo: {codigo}")
                    time.sleep(7)  # Rate limiting antes de tentar próximo
                    
            except Exception as e:
                print(f"AVISO: Erro com codigo {codigo}: {e}")
                time.sleep(7)  # Rate limiting antes de tentar próximo
                continue
        
        if df_times is not None and not df_times.empty:
            print(f"SUCESSO: {len(df_times)} times encontrados")
            print(f"\nColunas disponíveis: {list(df_times.columns)}")
            
            # Salva dados dos times
            df_times.to_csv(ESTATISTICAS_TIMES_PATH, index=False, encoding='utf-8-sig')
            print(f"SUCESSO: Dados salvos em: {ESTATISTICAS_TIMES_PATH}")
            
            return df_times, codigo_liga_usado
        else:
            print("\nAVISO: Nenhum dado de times encontrado com soccerdata")
            print("Tentando coleta direta via scraping...")
            time.sleep(7)  # Rate limiting
            
            # Tenta coleta direta como fallback
            df_times = coletar_dados_fbref_direto(ano=ano, tipo='times')
            if df_times is not None and not df_times.empty:
                print(f"SUCESSO: {len(df_times)} times encontrados via scraping")
                df_times.to_csv(ESTATISTICAS_TIMES_PATH, index=False, encoding='utf-8-sig')
                print(f"SUCESSO: Dados salvos em: {ESTATISTICAS_TIMES_PATH}")
                return df_times, 'scraping_direto'
            else:
                print("ERRO: Falha na coleta direta também")
                return None, None
            
    except Exception as e:
        print(f"ERRO ao coletar dados dos clubes: {e}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None, None


def coletar_urls_clubes_serie_a(ano=2025):
    """
    Coleta as URLs de todos os clubes da Série A acessando a página principal.
    
    Returns:
        Lista de dicionários com 'nome' e 'url' de cada clube
    """
    if not SELENIUM_AVAILABLE:
        print("ERRO: Selenium nao esta disponivel")
        return []
    
    try:
        print(f"\n{'='*60}")
        print(f"Coletando URLs dos CLUBES da Série A - {ano}")
        print(f"{'='*60}")
        
        # URL principal do Brasileirão
        url_principal = "https://fbref.com/en/comps/24"
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url_principal)
        
        # Aguarda a tabela carregar
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        # Obtém o HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Procura a tabela principal de times
        tabela_principal = soup.find('table', {'id': 'results'}) or soup.find('table', class_='stats_table')
        
        if not tabela_principal:
            print("AVISO: Tabela principal nao encontrada")
            driver.quit()
            return []
        
        # Procura todos os links de times na tabela
        # Os links geralmente estão na coluna "Squad"
        links_clubes = []
        linhas = tabela_principal.find_all('tr')
        
        for linha in linhas:
            # Procura link na célula do time
            link_tag = linha.find('a', href=True)
            if link_tag and '/squads/' in link_tag['href']:
                nome_time = link_tag.get_text(strip=True)
                url_time = link_tag['href']
                
                # Converte URL relativa para absoluta
                if url_time.startswith('/'):
                    url_time = f"https://fbref.com{url_time}"
                
                if nome_time and url_time:
                    links_clubes.append({
                        'nome': nome_time,
                        'url': url_time
                    })
        
        driver.quit()
        
        # Remove duplicatas mantendo a primeira ocorrência
        seen = set()
        links_unicos = []
        for clube in links_clubes:
            if clube['url'] not in seen:
                seen.add(clube['url'])
                links_unicos.append(clube)
        
        print(f"SUCESSO: Encontradas {len(links_unicos)} URLs de clubes")
        for clube in links_unicos:
            print(f"  - {clube['nome']}: {clube['url']}")
        
        return links_unicos
        
    except Exception as e:
        print(f"ERRO ao coletar URLs dos clubes: {e}")
        import traceback
        traceback.print_exc()
        if 'driver' in locals():
            driver.quit()
        return []


def coletar_jogadores_de_clube(url_clube, nome_clube):
    """
    Coleta dados dos jogadores de um clube específico.
    
    Args:
        url_clube: URL da página do clube
        nome_clube: Nome do clube
    
    Returns:
        DataFrame com dados dos jogadores ou None
    """
    if not SELENIUM_AVAILABLE:
        return None
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url_clube)
        
        # Aguarda a página carregar
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        # Aguarda um pouco mais para garantir que tudo carregou
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Procura tabelas de jogadores
        # Geralmente há uma tabela com id específico ou classe 'stats_table'
        tabelas = soup.find_all('table', class_='stats_table')
        
        # Procura especificamente a tabela de jogadores (não de times)
        df_jogadores = None
        
        for tabela in tabelas:
            try:
                # Tenta ler a tabela
                df_temp = pd.read_html(str(tabela))[0]
                
                # Verifica se parece ser uma tabela de jogadores individuais
                # Deve ter colunas como Player, Name, ou muitas linhas (jogadores)
                colunas_lower = [str(col).lower() for col in df_temp.columns]
                tem_player = any('player' in str(col).lower() or 'name' in str(col).lower() for col in df_temp.columns)
                tem_muitas_linhas = len(df_temp) > 5
                
                # Se tem coluna de jogador e muitas linhas, provavelmente é a tabela certa
                if tem_player and tem_muitas_linhas:
                    # Remove linhas que são cabeçalhos duplicados
                    # Verifica se a primeira coluna é "Player" (cabeçalho)
                    primeira_col = df_temp.columns[0] if len(df_temp.columns) > 0 else None
                    if primeira_col and 'Player' in str(primeira_col):
                        # Remove linhas onde a primeira coluna é "Player" (cabeçalho duplicado)
                        df_temp = df_temp[df_temp.iloc[:, 0].astype(str) != 'Player'].copy()
                    
                    # Remove linhas onde a primeira coluna começa com vírgulas (sub-cabeçalhos)
                    if len(df_temp) > 0:
                        primeira_col_valores = df_temp.iloc[:, 0].astype(str)
                        df_temp = df_temp[~primeira_col_valores.str.startswith(',')].copy()
                    
                    # Remove linhas vazias
                    df_temp = df_temp.dropna(subset=[df_temp.columns[0]]).copy()
                    
                    if len(df_temp) == 0:
                        continue
                    
                    # Adiciona coluna com nome do clube
                    df_temp['Clube'] = nome_clube
                    df_temp['URL_Clube'] = url_clube
                    
                    if df_jogadores is None:
                        df_jogadores = df_temp
                    else:
                        # Combina com dados anteriores (sem incluir cabeçalho novamente)
                        df_jogadores = pd.concat([df_jogadores, df_temp], ignore_index=True)
                    
                    print(f"  Encontrados {len(df_temp)} jogadores de {nome_clube}")
                    break
                    
            except Exception as e:
                continue
        
        driver.quit()
        
        if df_jogadores is None or df_jogadores.empty:
            print(f"  AVISO: Nenhum jogador encontrado para {nome_clube}")
            return None
        
        return df_jogadores
        
    except Exception as e:
        print(f"  ERRO ao coletar jogadores de {nome_clube}: {e}")
        if 'driver' in locals():
            driver.quit()
        return None


def coletar_dados_jogadores_serie_a(ano=2025, codigo_liga=None):
    """
    Coleta dados dos jogadores da Série A do Brasileirão.
    
    Args:
        ano: Ano da temporada
        codigo_liga: Código da liga que funcionou (opcional, tenta vários se None)
    
    Returns:
        DataFrame com dados dos jogadores ou None se houver erro
    """
    if not SOCCERDATA_AVAILABLE:
        print("ERRO: soccerdata nao esta disponivel. Instale com: pip install soccerdata")
        return None
    
    try:
        print(f"\n{'='*60}")
        print(f"Coletando dados dos JOGADORES da Série A - {ano}")
        print(f"{'='*60}")
        
        temporada = mapear_ano_para_temporada(ano)
        
        print(f"Temporada: {temporada}")
        print("Aguarde... (respeitando rate limiting do FBref)")
        
        # Tenta diferentes códigos de liga (ou usa o que foi passado)
        if codigo_liga:
            codigos_liga = [codigo_liga]
        else:
            # Baseado na URL: https://fbref.com/en/comps/24/Serie-A-Stats
            # Nota: O código 24 é da Série A italiana, o código 37 pode ser do Brasileirão
            codigos_liga = ['37', '24', 'BRA-SerieA', 'BRA1', 'BRA-Serie-A', 'Serie-A-Stats']
        
        df_jogadores = None
        codigo_liga_usado = None
        
        for codigo in codigos_liga:
            try:
                print(f"\nTentando código de liga: {codigo}")
                # Cria instância do FBref
                fbref = FBref(
                    leagues=[codigo],
                    seasons=[temporada]
                )
                
                # Coleta estatísticas dos jogadores
                print("Coletando estatísticas dos jogadores...")
                df_jogadores = fbref.read_player_season_stats(stat_type='standard')
                
                if df_jogadores is not None and not df_jogadores.empty:
                    codigo_liga_usado = codigo
                    print(f"SUCESSO com codigo: {codigo}")
                    break
                else:
                    print(f"AVISO: Nenhum dado encontrado com codigo: {codigo}")
                    time.sleep(7)  # Rate limiting
                    
            except Exception as e:
                print(f"AVISO: Erro com codigo {codigo}: {e}")
                time.sleep(7)  # Rate limiting
                continue
        
        if df_jogadores is None or df_jogadores.empty:
            print("\nAVISO: Nao foi possivel coletar dados com nenhum codigo de liga testado")
            print("Tentando coleta clube por clube...")
            time.sleep(7)  # Rate limiting
            
            # Coleta URLs dos clubes
            links_clubes = coletar_urls_clubes_serie_a(ano=ano)
            
            if not links_clubes:
                print("ERRO: Nao foi possivel coletar URLs dos clubes")
                return None
            
            # Coleta jogadores de cada clube
            print(f"\nColetando jogadores de {len(links_clubes)} clubes...")
            dfs_jogadores = []
            
            for i, clube in enumerate(links_clubes, 1):
                print(f"\n[{i}/{len(links_clubes)}] Coletando jogadores de {clube['nome']}...")
                df_clube = coletar_jogadores_de_clube(clube['url'], clube['nome'])
                
                if df_clube is not None and not df_clube.empty:
                    dfs_jogadores.append(df_clube)
                
                # Rate limiting entre requisições
                if i < len(links_clubes):
                    time.sleep(5)  # Aguarda 5 segundos entre clubes
            
            # Consolida todos os dados
            if dfs_jogadores:
                # IMPORTANTE: Primeiro, identifica qual DataFrame tem o cabeçalho correto
                # O primeiro DataFrame deve ter o cabeçalho, os demais não devem ter
                df_final = None
                
                for idx, df_temp in enumerate(dfs_jogadores):
                    # Remove cabeçalhos duplicados de cada DataFrame
                    if 'Player' in df_temp.columns:
                        # Remove linhas onde Player é "Player" (cabeçalho duplicado)
                        df_temp = df_temp[df_temp['Player'].astype(str) != 'Player'].copy()
                        # Remove linhas onde Player começa com vírgulas (sub-cabeçalhos)
                        df_temp = df_temp[~df_temp['Player'].astype(str).str.startswith(',')].copy()
                        # Remove linhas vazias
                        df_temp = df_temp[df_temp['Player'].notna()].copy()
                        df_temp = df_temp[df_temp['Player'] != ''].copy()
                    
                    if df_final is None:
                        # Primeiro DataFrame: mantém cabeçalho (já está nas colunas)
                        df_final = df_temp.copy()
                    else:
                        # Demais DataFrames: concatena apenas os dados (sem cabeçalho)
                        df_final = pd.concat([df_final, df_temp], ignore_index=True)
                
                df_jogadores = df_final
                
                # Garante que a coluna Clube está preenchida
                if 'Clube' in df_jogadores.columns:
                    df_jogadores['Clube'] = df_jogadores['Clube'].fillna(method='ffill')
                    df_jogadores['Clube'] = df_jogadores['Clube'].fillna(method='bfill')
                
                # Remove duplicatas finais
                df_jogadores = df_jogadores.drop_duplicates(subset=['Player', 'Clube'] if 'Clube' in df_jogadores.columns else ['Player']).copy()
                
                print(f"\nSUCESSO: Total de {len(df_jogadores)} registros de jogadores coletados")
                print(f"  - Cabeçalho único: Sim")
                print(f"  - Coluna Clube preenchida: {'Sim' if 'Clube' in df_jogadores.columns and not df_jogadores['Clube'].isna().all() else 'Não'}")
            else:
                print("ERRO: Nenhum jogador foi coletado")
                return None
        
        if df_jogadores is not None and not df_jogadores.empty:
            print(f"SUCESSO: {len(df_jogadores)} registros de jogadores encontrados")
            print(f"\nColunas disponíveis: {list(df_jogadores.columns)}")
            
            # Tenta coletar estatísticas avançadas também
            print("\n2. Coletando estatísticas avançadas (xG, xA)...")
            time.sleep(7)  # Rate limiting
            
            try:
                df_avancado = fbref.read_player_season_stats(stat_type='shooting')
                if df_avancado is not None and not df_avancado.empty:
                    print(f"SUCESSO: {len(df_avancado)} registros de estatisticas avancadas")
                    # Merge com dados principais
                    df_jogadores = pd.merge(
                        df_jogadores, 
                        df_avancado, 
                        on=['player', 'team', 'season'], 
                        how='left',
                        suffixes=('', '_shooting')
                    )
            except Exception as e:
                print(f"AVISO: Nao foi possivel coletar estatisticas avancadas: {e}")
            
            # Tenta coletar estatísticas de passes (para xA)
            print("\n3. Coletando estatísticas de passes (xA)...")
            time.sleep(7)  # Rate limiting
            
            try:
                df_passes = fbref.read_player_season_stats(stat_type='passing')
                if df_passes is not None and not df_passes.empty:
                    print(f"SUCESSO: {len(df_passes)} registros de passes")
                    # Merge com dados principais
                    df_jogadores = pd.merge(
                        df_jogadores, 
                        df_passes, 
                        on=['player', 'team', 'season'], 
                        how='left',
                        suffixes=('', '_passing')
                    )
            except Exception as e:
                print(f"AVISO: Nao foi possivel coletar estatisticas de passes: {e}")
            
            # Salva dados dos jogadores
            # Garante que não há cabeçalhos duplicados antes de salvar
            if 'Player' in df_jogadores.columns:
                df_jogadores = df_jogadores[df_jogadores['Player'].astype(str) != 'Player'].copy()
                df_jogadores = df_jogadores[~df_jogadores['Player'].astype(str).str.startswith(',')].copy()
            
            df_jogadores.to_csv(JOGADORES_FBREF_PATH, index=False, encoding='utf-8-sig')
            print(f"\nSUCESSO: Dados salvos em: {JOGADORES_FBREF_PATH}")
            print(f"  - Arquivo limpo: Sem cabeçalhos duplicados")
            print(f"  - Coluna Clube: {'Presente' if 'Clube' in df_jogadores.columns else 'Ausente'}")
            
            return df_jogadores
        else:
            print("AVISO: Nenhum dado de jogadores encontrado")
            return None
            
    except Exception as e:
        print(f"ERRO ao coletar dados dos jogadores: {e}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None


def coletar_dados_completos(ano=2025):
    """
    Coleta todos os dados do FBref (clubes e jogadores).
    
    Args:
        ano: Ano da temporada (default: 2025)
    
    Returns:
        Tupla (df_clubes, df_jogadores) ou (None, None) se houver erro
    """
    print(f"\n{'='*70}")
    print(f"COLETA DE DADOS DO FBREF - SÉRIE A DO BRASILEIRÃO {ano}")
    print(f"{'='*70}")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nATENCAO: O FBref tem rate limiting de 1 requisicao a cada 6 segundos.")
    print(f"Este processo pode levar vários minutos. Por favor, seja paciente.\n")
    
    if not SOCCERDATA_AVAILABLE:
        print("ERRO: Instale a biblioteca primeiro:")
        print("   pip install soccerdata")
        return None, None
    
    # Coleta dados dos clubes e captura o código de liga que funcionou
    df_clubes, codigo_liga_usado = coletar_dados_clubes_serie_a(ano=ano)
    
    # Aguarda antes de coletar dados dos jogadores (rate limiting)
    if df_clubes is not None:
        print("\nAguardando 7 segundos antes de coletar dados dos jogadores...")
        time.sleep(7)
    
    # Coleta dados dos jogadores (usa mesmo código de liga que funcionou)
    df_jogadores = coletar_dados_jogadores_serie_a(ano=ano, codigo_liga=codigo_liga_usado)
    
    # Resumo
    print(f"\n{'='*70}")
    print("RESUMO DA COLETA")
    print(f"{'='*70}")
    
    if df_clubes is not None:
        print(f"SUCESSO - Clubes: {len(df_clubes)} times coletados")
        print(f"   Arquivo: {ESTATISTICAS_TIMES_PATH}")
    else:
        print("ERRO - Clubes: Falha na coleta")
    
    if df_jogadores is not None:
        print(f"SUCESSO - Jogadores: {len(df_jogadores)} registros coletados")
        print(f"   Arquivo: {JOGADORES_FBREF_PATH}")
    else:
        print("ERRO - Jogadores: Falha na coleta")
    
    print(f"\n{'='*70}")
    
    return df_clubes, df_jogadores


def main():
    """Função principal para execução do script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Coleta dados do FBref para Série A do Brasileirão'
    )
    parser.add_argument(
        '--ano',
        type=int,
        default=2025,
        help='Ano da temporada (default: 2025)'
    )
    parser.add_argument(
        '--apenas-clubes',
        action='store_true',
        help='Coleta apenas dados dos clubes'
    )
    parser.add_argument(
        '--apenas-jogadores',
        action='store_true',
        help='Coleta apenas dados dos jogadores'
    )
    
    args = parser.parse_args()
    
    if args.apenas_clubes:
        df_clubes, codigo = coletar_dados_clubes_serie_a(ano=args.ano)
        if df_clubes is not None:
            print(f"\nSUCESSO: Coleta de clubes concluida! {len(df_clubes)} times coletados.")
    elif args.apenas_jogadores:
        df_jogadores = coletar_dados_jogadores_serie_a(ano=args.ano)
        if df_jogadores is not None:
            print(f"\nSUCESSO: Coleta de jogadores concluida! {len(df_jogadores)} registros coletados.")
    else:
        coletar_dados_completos(ano=args.ano)


if __name__ == "__main__":
    main()

