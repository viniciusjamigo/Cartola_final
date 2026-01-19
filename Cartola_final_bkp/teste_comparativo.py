import pandas as pd
import sys
import os

# Adiciona o diretório pai para permitir importação dos módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from cartola_project.utils.analise_performance import gerar_dados_comparativos

print("Iniciando teste direto de 'gerar_dados_comparativos'...")

try:
    df_comparativo, erro, rmse_scores = gerar_dados_comparativos(ano=2025)
    
    if erro:
        print(f"\n❌ ERRO RETORNADO: {erro}")
    else:
        print("\n✅ SUCESSO! Dados gerados.")
        print(f"Dimensoes do DataFrame: {df_comparativo.shape}")
        print("Head do Comparativo:")
        print(df_comparativo.head())
        
        print("\n📊 RMSE SCORES:")
        print(rmse_scores)
        
        if not rmse_scores:
            print("⚠️ ALERTA: RMSE vazio! O problema persiste.")
        else:
            print("✅ RMSE calculado com sucesso.")

except Exception as e:
    print(f"\n❌ EXCEÇÃO CRÍTICA: {e}")
    import traceback
    traceback.print_exc()

