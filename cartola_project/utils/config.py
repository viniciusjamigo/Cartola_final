import os
import logging
from logging.handlers import RotatingFileHandler

# --- DEFINIÇÃO DE CAMINHOS (Usando Strings puras para evitar conflitos de recursão) ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
MODEL_DIR = os.path.join(DATA_DIR, "modelos")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# Cria diretórios se não existirem
for directory in [DATA_DIR, LOG_DIR, MODEL_DIR, CACHE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

class Config:
    """Classe de configuração simplificada para evitar erros de recursão no Streamlit."""
    def __init__(self):
        # --- CONFIGURAÇÕES DE TEMPORADA ---
        self.CURRENT_YEAR = 2026
        self.PREVIOUS_YEAR = 2025

        # Diretórios
        self.DATA_DIR = DATA_DIR
        self.MODEL_DIR = MODEL_DIR
        self.CACHE_DIR = CACHE_DIR
        self.LOG_DIR = LOG_DIR

        # Arquivos de Dados
        self.RAW_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual.csv")
        self.PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual_processada.csv")
        self.CLUBS_DATA_PATH = os.path.join(DATA_DIR, "clubes.json")
        self.MATCHES_DATA_PATH = os.path.join(DATA_DIR, "partidas_rodada.csv")
        self.HISTORICAL_MATCHES_PATH = os.path.join(DATA_DIR, "historico_partidas.csv")
        self.ODDS_DATA_PATH = os.path.join(DATA_DIR, "odds_rodada.csv")
        self.ODDS_HISTORY_PATH = os.path.join(DATA_DIR, "historico_odds.csv")
        self.HISTORICO_ATUAL_PATH = os.path.join(DATA_DIR, f"historico_{self.CURRENT_YEAR}.csv")
        self.HISTORICO_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv")
        self.HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, "historico_jogadores.csv")
        self.ESTATISTICAS_TIMES_PATH = os.path.join(DATA_DIR, "estatisticas_times.csv")
        self.METRICS_PATH = os.path.join(MODEL_DIR, "metricas.json")
        self.CACHE_DIR_PATH = CACHE_DIR

        # Configurações do Otimizador
        self.ORCAMENTO_PADRAO = 140.0
        self.MAX_JOGADORES_POR_CLUBE = 5
        
        # Configurações de API
        self.API_URL_MERCADO = "https://api.cartolafc.globo.com/atletas/mercado"
        self.API_URL_PARTIDAS = "https://api.cartolafc.globo.com/partidas"
        self.ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato/odds"
        
        # Configurações de Treinamento
        self.ANO_MINIMO_TREINO = 2022
        self.TEST_SIZE = 0.2
        self.RANDOM_STATE = 42

def setup_logging():
    """Configura o sistema de logging estruturado."""
    log_file = os.path.join(LOG_DIR, "app.log")
    
    logger = logging.getLogger("cartola_pro")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

# Instâncias globais
logger = setup_logging()
config = Config()
