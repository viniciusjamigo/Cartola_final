import requests
import pandas as pd
import os
import time
import json
from tqdm import tqdm
from utils.config import config

# --- CAMINHOS E URLs ---
DATA_DIR = os.path.dirname(config.RAW_DATA_PATH)
HISTORICAL_DATA_PATH = config.HISTORICO_ATUAL_PATH

API_PONTUADOS_URL = "https://api.cartolafc.globo.com/atletas/pontuados/{rodada}"

def coletar_dados_historicos(ano, total_rodadas=38, rodada_especifica=None):
    """
    Coleta os dados de scout e pontuação de todos os jogadores.
    
    Args:
        ano (int): O ano da temporada.
        total_rodadas (int): Limite de rodadas se coletar tudo.
        rodada_especifica (int, optional): Se informado, coleta APENAS essa rodada e atualiza o arquivo existente.
    """
    
    if rodada_especifica:
        intervalo = [rodada_especifica]
        print(f"Iniciando atualização INCREMENTAL para a rodada {rodada_especifica} de {ano}...")
    else:
        intervalo = range(1, total_rodadas + 1)
        print(f"Iniciando a coleta COMPLETA de dados históricos para a temporada de {ano}...")

    novos_dados = []

    for rodada in intervalo:
        try:
            url = API_PONTUADOS_URL.format(rodada=rodada)
            print(f"\n🔄 Coletando Rodada {rodada}...")
            response = requests.get(url)
            response.raise_for_status()
            
            dados_rodada = response.json()
            
            # Salva resposta da API para debug (apenas se for rodada específica)
            if rodada_especifica:
                debug_path = os.path.join(DATA_DIR, f"api_rodada{rodada_especifica}_debug.json")
                try:
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        json.dump(dados_rodada, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Resposta da API salva em: {debug_path}")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível salvar debug: {e}")
            
            # Verifica se a resposta é válida
            if not dados_rodada or not isinstance(dados_rodada, dict):
                print(f"⚠️ Resposta inválida da API para a rodada {rodada}. Tipo recebido: {type(dados_rodada)}. Pulando.")
                continue
            
            atletas = dados_rodada.get('atletas', {})
            
            # Verifica se atletas existe e não é None
            if atletas is None:
                print(f"⚠️ Rodada {rodada}: A API retornou 'atletas: null'. A rodada pode ainda não ter dados consolidados.")
                print(f"   URL testada: {url}")
                continue
            
            if not atletas:
                print(f"⚠️ Rodada {rodada}: Nenhum atleta encontrado na resposta da API. A rodada pode ainda não ter dados consolidados.")
                print(f"   URL testada: {url}")
                continue
            
            # Garante que atletas é um dicionário iterável
            if not isinstance(atletas, dict):
                print(f"⚠️ Rodada {rodada}: Formato inesperado de dados. Esperado dict, recebido {type(atletas)}. Pulando.")
                continue

            # Conta quantos atletas foram encontrados
            num_atletas = len(atletas)
            total_api = dados_rodada.get('total_atletas', num_atletas)
            print(f"✅ Rodada {rodada}: {num_atletas} atletas no dicionário (API reporta {total_api} total). Processando...")

            # Contadores para diagnóstico
            processados_ok = 0
            processados_erro = 0
            
            for atleta_id, dados_atleta in atletas.items():
                try:
                    # Verifica se dados_atleta é válido
                    if dados_atleta is None or not isinstance(dados_atleta, dict):
                        print(f"  ⚠️ Dados inválidos para atleta {atleta_id}. Pulando.")
                        processados_erro += 1
                        continue
                    
                    registro = {
                        'ano': ano,
                        'atleta_id': int(atleta_id),
                        'rodada': rodada,
                        'apelido': dados_atleta.get('apelido'),
                        'clube_id': dados_atleta.get('clube_id'),
                        'posicao_id': dados_atleta.get('posicao_id'),
                        'pontuacao': dados_atleta.get('pontuacao', 0),
                    }
                    
                    # Trata scout que pode ser None, {} ou um dict válido
                    scouts = dados_atleta.get('scout')
                    if scouts is None:
                        scouts = {}
                    elif not isinstance(scouts, dict):
                        scouts = {}
                    
                    # Só faz update se scouts for um dict válido
                    if isinstance(scouts, dict):
                        registro.update(scouts)
                    
                    novos_dados.append(registro)
                    processados_ok += 1
                except Exception as e:
                    processados_erro += 1
                    apelido = dados_atleta.get('apelido', 'N/A') if dados_atleta and isinstance(dados_atleta, dict) else 'N/A'
                    print(f"  ⚠️ Erro ao processar atleta {atleta_id} ({apelido}): {e}")
                    import traceback
                    print(f"     Traceback: {traceback.format_exc()}")
                    continue
            
            # Resumo do processamento
            print(f"   ✓ Processados com sucesso: {processados_ok}")
            if processados_erro > 0:
                print(f"   ✗ Erros: {processados_erro}")
            
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar dados da rodada {rodada}: {e}. Pulando.")
            import traceback
            print(f"   Detalhes: {traceback.format_exc()}")
            continue
        except Exception as e:
            print(f"❌ Erro inesperado na rodada {rodada}: {e}")
            import traceback
            print(f"   Detalhes: {traceback.format_exc()}")
            continue

    if not novos_dados:
        print("Nenhum dado coletado.")
        return None

    df_novos = pd.DataFrame(novos_dados)
    df_novos.fillna(0, inplace=True)
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # --- LÓGICA DE SALVAMENTO ---
    if rodada_especifica and os.path.exists(HISTORICAL_DATA_PATH):
        # Carrega arquivo existente
        df_existente = pd.read_csv(HISTORICAL_DATA_PATH)
        
        # Conta quantos registros existiam dessa rodada antes
        registros_antigos = len(df_existente[(df_existente['ano'] == ano) & (df_existente['rodada'] == rodada_especifica)])
        
        # Remove dados antigos dessa mesma rodada para não duplicar
        df_existente = df_existente[~((df_existente['ano'] == ano) & (df_existente['rodada'] == rodada_especifica))]
        
        # Concatena
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        df_final.sort_values(by=['rodada', 'atleta_id'], inplace=True)
        
        modo = "atualizado"
        registros_novos = len(df_novos)
        print(f"\n📊 Resumo da atualização da Rodada {rodada_especifica}:")
        print(f"   - Registros antigos removidos: {registros_antigos}")
        print(f"   - Registros novos adicionados: {registros_novos}")
        if registros_novos == 0:
            print(f"   ⚠️ ATENÇÃO: Nenhum dado novo foi coletado. A API pode ainda não ter os dados consolidados.")
    else:
        # Se for coleta completa ou arquivo não existir, sobrescreve/cria
        df_final = df_novos
        modo = "criado"
        
    df_final.to_csv(HISTORICAL_DATA_PATH, index=False, encoding='utf-8-sig')
    print(f"\n✅ Arquivo '{HISTORICAL_DATA_PATH}' {modo} com sucesso! Total: {len(df_final)} registros.")
    
    return df_final

if __name__ == "__main__":
    # Exemplo de uso manual
    coletar_dados_historicos(ano=config.CURRENT_YEAR, total_rodadas=38)
