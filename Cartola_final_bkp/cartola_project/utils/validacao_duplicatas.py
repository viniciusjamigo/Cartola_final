"""
Função para validar e verificar duplicatas de atleta_id em rodadas.
"""
import pandas as pd
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORICO_2025_PATH = os.path.join(DATA_DIR, "historico_2025.csv")
HISTORICO_COMPLETO_PATH = os.path.join(DATA_DIR, "historico_completo.csv")

def verificar_duplicatas_rodada(ano=2025, rodada=None, historico_path=None):
    """
    Verifica duplicatas de atleta_id em uma rodada específica.
    
    Args:
        ano: Ano da rodada (padrão: 2025)
        rodada: Número da rodada (None para verificar todas)
        historico_path: Caminho do arquivo histórico (None para usar padrão)
    
    Returns:
        dict: Dicionário com informações sobre duplicatas encontradas
    """
    if historico_path is None:
        historico_path = HISTORICO_2025_PATH if ano == 2025 else HISTORICO_COMPLETO_PATH
    
    if not os.path.exists(historico_path):
        return {"erro": f"Arquivo histórico não encontrado: {historico_path}"}
    
    try:
        df = pd.read_csv(historico_path)
        
        # Filtra por ano
        if 'ano' in df.columns:
            df = df[df['ano'] == ano]
        else:
            print("⚠️ AVISO: Coluna 'ano' não encontrada no histórico.")
        
        # Filtra por rodada se especificada
        if rodada is not None and 'rodada' in df.columns:
            df = df[df['rodada'] == rodada]
            rodadas_verificar = [rodada]
        else:
            rodadas_verificar = sorted(df['rodada'].unique()) if 'rodada' in df.columns else []
        
        resultado = {
            "ano": ano,
            "rodadas_verificadas": rodadas_verificar,
            "duplicatas_encontradas": False,
            "rodadas_com_duplicatas": [],
            "total_duplicatas": 0
        }
        
        if 'atleta_id' not in df.columns:
            resultado["erro"] = "Coluna 'atleta_id' não encontrada no histórico."
            return resultado
        
        # Verifica duplicatas em cada rodada
        duplicatas_por_rodada = {}
        
        for r in rodadas_verificar:
            rodada_df = df[df['rodada'] == r] if rodada is None else df
            
            duplicados = rodada_df[rodada_df.duplicated(subset=['atleta_id'], keep=False)]
            
            if len(duplicados) > 0:
                resultado["duplicatas_encontradas"] = True
                resultado["rodadas_com_duplicatas"].append(r)
                resultado["total_duplicatas"] += len(duplicados)
                
                duplicatas_por_rodada[r] = {
                    "total": len(duplicados),
                    "atletas_unicos": duplicados['atleta_id'].nunique(),
                    "detalhes": duplicados[['atleta_id', 'apelido', 'rodada']].to_dict('records') if 'apelido' in duplicados.columns else []
                }
            
            # Para rodada específica, para após verificar
            if rodada is not None:
                break
        
        resultado["detalhes_por_rodada"] = duplicatas_por_rodada
        
        return resultado
        
    except Exception as e:
        return {"erro": f"Erro ao processar histórico: {e}"}

def validar_time_escalado(time_escalado):
    """
    Valida se um time escalado não tem duplicatas de atleta_id.
    
    Args:
        time_escalado: DataFrame com o time escalado (deve ter coluna 'atleta_id')
    
    Returns:
        dict: Dicionário com resultado da validação
    """
    if time_escalado is None or time_escalado.empty:
        return {"valido": False, "erro": "Time escalado está vazio ou None"}
    
    if 'atleta_id' not in time_escalado.columns:
        return {"valido": False, "erro": "Coluna 'atleta_id' não encontrada no time escalado"}
    
    duplicados = time_escalado.duplicated(subset=['atleta_id'], keep=False)
    
    resultado = {
        "valido": not duplicados.any(),
        "total_jogadores": len(time_escalado),
        "jogadores_unicos": time_escalado['atleta_id'].nunique(),
        "duplicatas_encontradas": duplicados.sum() if duplicados.any() else 0
    }
    
    if duplicados.any():
        resultado["atletas_duplicados"] = time_escalado[duplicados]['atleta_id'].unique().tolist()
        resultado["detalhes"] = time_escalado[duplicados][['atleta_id', 'nome' if 'nome' in time_escalado.columns else 'apelido', 'posicao', 'clube']].to_dict('records')
    else:
        resultado["mensagem"] = "✅ Time escalado não possui duplicatas."
    
    return resultado

if __name__ == "__main__":
    # Teste: Verifica rodada 34
    print("Verificando duplicatas na rodada 34...")
    resultado = verificar_duplicatas_rodada(ano=2025, rodada=34)
    print(f"\nResultado: {resultado}")

