import pandas as pd
import os

# URL do dataset do Adao Duque
URL = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/campeonato-brasileiro-full.csv"

def baixar():
    print("Baixando histórico de partidas...")
    try:
        df = pd.read_csv(URL)
        
        # Caminho de destino (assumindo execução na raiz do projeto ou perto)
        # Vamos varrer para achar a pasta cartola_project
        base_dir = os.getcwd()
        target_file = None
        
        for root, dirs, files in os.walk(base_dir):
            if "cartola_project" in dirs:
                target_file = os.path.join(root, "cartola_project", "data", "historico_partidas.csv")
                break
            if "data" in dirs and "cartola_project" in root: # Ja estamos dentro
                 target_file = os.path.join(root, "data", "historico_partidas.csv")
                 break
        
        if not target_file:
            # Fallback: cria localmente
            target_file = "historico_partidas_novo.csv"
            
        df.to_csv(target_file, index=False)
        print(f"Salvo em: {target_file}")
        print(f"Anos disponíveis: {df['data'].str[:4].unique()}")

        # Tentar chamar a atualização de 2025
        try:
            import sys
            # Adiciona o diretório atual ao path para tentar importar
            sys.path.append(os.getcwd())
            from cartola_project.utils.coleta_dados import atualizar_partidas_2025
            print("Executando atualização de 2025...")
            atualizar_partidas_2025()
        except ImportError:
            print("AVISO: Não foi possível importar 'cartola_project.utils.coleta_dados'. Os dados de 2025 não foram atualizados automaticamente.")
            print("Por favor, execute 'python cartola_project/utils/coleta_dados.py' para atualizar 2025.")
        except Exception as e:
             print(f"Erro ao atualizar 2025: {e}")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    baixar()

