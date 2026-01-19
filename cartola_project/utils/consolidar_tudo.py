import pandas as pd
import os
from utils.config import config

FILE_OLD = config.HISTORICAL_DATA_PATH
FILE_FINAL = os.path.join(os.path.dirname(config.RAW_DATA_PATH), "historico_completo.csv")

def consolidar():
    print("Carregando arquivos...")
    
    dfs = []
    
    if os.path.exists(FILE_OLD):
        df_old = pd.read_csv(FILE_OLD)
        print(f"Histórico principal: {len(df_old)} registros")
        dfs.append(df_old)
    
    # Procura por arquivos de anos específicos que podem ter sido coletados separadamente
    for ano in range(2024, config.CURRENT_YEAR + 1):
        file_ano = os.path.join(os.path.dirname(config.RAW_DATA_PATH), f"historico_{ano}.csv")
        if os.path.exists(file_ano):
            df_ano = pd.read_csv(file_ano)
            print(f"Histórico {ano}: {len(df_ano)} registros")
            dfs.append(df_ano)
        
    if not dfs:
        return
        
    # Concatenação
    print("Consolidando...")
    df_final = pd.concat(dfs, ignore_index=True)
    
    # Remove duplicatas (caso existam por algum motivo)
    # Duplicata = mesmo ano, rodada, atleta_id
    tamanho_antes = len(df_final)
    df_final = df_final.drop_duplicates(subset=['ano', 'rodada', 'atleta_id'], keep='last')
    tamanho_depois = len(df_final)
    if tamanho_antes != tamanho_depois:
        print(f"  > Removidas {tamanho_antes - tamanho_depois} duplicatas.")
    
    # Padronização final de nulos
    df_final.fillna(0, inplace=True)
    
    # Salvando
    # Tenta salvar o arquivo final
    try:
        df_final.to_csv(FILE_FINAL, index=False)
    except PermissionError as e:
        print(f"\n❌ ERRO DE PERMISSÃO ao salvar {FILE_FINAL}")
        print(f"   O arquivo pode estar aberto em outro programa (Excel, editor de texto, etc.)")
        print(f"   Por favor, feche o arquivo e tente novamente.")
        raise
    
    # Sobrescrever o arquivo principal que o modelo lê? 
    # O modelo lê 'historico_jogadores.csv'. Vamos renomear o final para esse nome.
    # Mas antes fazer backup.
    
    if os.path.exists(FILE_OLD):
        backup_name = os.path.join(config.DATA_DIR, "historico_jogadores_bkp.csv")
        if not os.path.exists(backup_name): # Só faz backup se não existir
            try:
                os.rename(FILE_OLD, backup_name)
                print(f"Backup criado: {backup_name}")
            except PermissionError:
                print(f"⚠️ Aviso: Não foi possível criar backup (arquivo pode estar aberto). Continuando...")
    
    try:
        df_final.to_csv(FILE_OLD, index=False)
        print(f"\n✅ SUCESSO! Base completa salva em: {FILE_OLD}")
        print(f"Total de registros: {len(df_final)}")
        print(f"Anos presentes: {sorted(df_final['ano'].unique())}")
    except PermissionError as e:
        print(f"\n❌ ERRO DE PERMISSÃO ao salvar {FILE_OLD}")
        print(f"   O arquivo 'historico_jogadores.csv' pode estar aberto em outro programa.")
        print(f"   Por favor, feche o arquivo e tente novamente.")
        raise

if __name__ == "__main__":
    consolidar()

