import soccerdata as sd
import pandas as pd
import os

def testar_soccerdata():
    print("🚀 Iniciando diagnóstico do SoccerData...")
    
    # 1. Verifica quais ligas o FBref suporta na sua instalação
    try:
        # Pega a lista de ligas que a classe FBref conhece
        # Em versões recentes, isso fica no atributo leagues do objeto ou via classe
        leagues_dict = sd.FBref._all_leagues() if hasattr(sd.FBref, '_all_leagues') else {}
        if not leagues_dict:
            # Fallback para tentar listar via instância
            fb_temp = sd.FBref()
            leagues_dict = fb_temp.leagues
            
        print(f"📊 Ligas detectadas no sistema: {list(leagues_dict.keys())}")
        
        # Procura por algo que contenha 'Brazil' ou 'BRA'
        brazil_leagues = [l for l in leagues_dict.keys() if 'BRA' in l or 'Brazil' in l]
        print(f"🇧🇷 Ligas brasileiras encontradas: {brazil_leagues}")

        if not brazil_leagues:
            print("\n⚠️ O Brasileirão não foi encontrado na lista padrão.")
            print("Isso acontece porque o SoccerData as vezes precisa que você defina a liga.")
            print("Tentando forçar a carga da 'BRA-Serie A'...")
            target_league = 'BRA-Serie A'
        else:
            target_league = brazil_leagues[0]

        print(f"\n⏳ Tentando carregar a liga: {target_league}...")
        
        # 2. Tenta carregar a liga encontrada
        fbref = sd.FBref(leagues=target_league, seasons="2024")

        print("📈 Lendo estatísticas de 2024...")
        df_jogadores = fbref.read_player_season_stats(stat_type="standard")
        
        # Resetando o índice para facilitar a manipulação
        df_exemplo = df_jogadores.reset_index()

        # Filtrando colunas
        colunas_foco = ['player', 'team', 'performance_gls', 'expected_xg']
        colunas_presentes = [c for c in colunas_foco if c in df_exemplo.columns]
        
        print("\n🔥 SUCESSO! Dados carregados:")
        print(df_exemplo[colunas_presentes].sort_values(by='expected_xg', ascending=False).head(10).to_string(index=False))

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\n💡 Possível Solução:")
        print("Sua versão do soccerdata parece estar limitada às ligas europeias.")
        print("Tente rodar: pip install --upgrade soccerdata")

if __name__ == "__main__":
    testar_soccerdata()
