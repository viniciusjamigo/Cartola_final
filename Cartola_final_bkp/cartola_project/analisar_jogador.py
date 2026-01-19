"""
Script para analisar por que um jogador específico foi escolhido pela IA Nova.
"""
import pandas as pd
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual_processada.csv")

def analisar_jogador(atleta_id, nome_jogador=None):
    """
    Analisa por que um jogador foi escolhido pela IA Nova.
    
    Args:
        atleta_id: ID do atleta
        nome_jogador: Nome do jogador (opcional, para validação)
    """
    if not os.path.exists(PROCESSED_DATA_PATH):
        print(f"❌ Arquivo não encontrado: {PROCESSED_DATA_PATH}")
        return
    
    df = pd.read_csv(PROCESSED_DATA_PATH)
    
    # Busca o jogador
    jogador = df[df['atleta_id'] == atleta_id]
    
    if jogador.empty:
        print(f"❌ Jogador com ID {atleta_id} não encontrado.")
        return
    
    jogador = jogador.iloc[0]
    
    print("=" * 80)
    print(f"ANÁLISE DO JOGADOR: {jogador['nome']}")
    print("=" * 80)
    print()
    
    # Dados Básicos
    print("📊 DADOS BÁSICOS:")
    print(f"  • ID: {jogador['atleta_id']}")
    print(f"  • Posição: {jogador['posicao']}")
    print(f"  • Clube: {jogador['clube']}")
    print(f"  • Preço: C$ {jogador['preco_num']:.2f}")
    print(f"  • Média Temporada: {jogador['media_num']:.2f} pontos")
    print(f"  • Pontos na Última Rodada: {jogador.get('pontos_num', 'N/A')}")
    print()
    
    # Contexto do Jogo
    print("⚽ CONTEXTO DO JOGO:")
    fator_casa = jogador.get('fator_casa', 0)
    if fator_casa == 1:
        print(f"  • Mando: 🏠 Joga EM CASA")
        bonus_casa = 0.08
    elif fator_casa == -1:
        print(f"  • Mando: ✈️ Joga FORA")
        bonus_casa = -0.03
    else:
        print(f"  • Mando: ❓ Não identificado")
        bonus_casa = 0
    
    adversario = jogador.get('adversario', 'N/A')
    print(f"  • Adversário: {adversario}")
    
    # Estatísticas do Adversário
    adv_gols_sofridos = jogador.get('adv_media_gols_sofridos', None)
    adv_gols_feitos = jogador.get('adv_media_gols_feitos', None)
    
    if adv_gols_sofridos is not None:
        print(f"  • Adversário toma {adv_gols_sofridos:.2f} gols/jogo em média")
    if adv_gols_feitos is not None:
        print(f"  • Adversário faz {adv_gols_feitos:.2f} gols/jogo em média")
    print()
    
    # Previsão do Modelo
    print("🤖 PREVISÃO DO MODELO:")
    pontuacao_base = jogador.get('pontuacao_prevista_base', None)
    pontuacao_prevista = jogador.get('pontuacao_prevista', None)
    
    if pontuacao_base is not None:
        print(f"  • Previsão Base (XGBoost): {pontuacao_base:.2f} pontos")
    
    if pontuacao_prevista is not None:
        print(f"  • Previsão Final (com Bônus): {pontuacao_prevista:.2f} pontos")
        
        if pontuacao_base is not None:
            multiplicador = pontuacao_prevista / pontuacao_base if pontuacao_base > 0 else 1.0
            print(f"  • Multiplicador Aplicado: {multiplicador:.2f}x ({((multiplicador-1)*100):+.1f}%)")
    print()
    
    # Análise de Custo-Benefício
    print("💰 ANÁLISE DE CUSTO-BENEFÍCIO:")
    if pontuacao_prevista is not None and jogador['preco_num'] > 0:
        custo_beneficio = pontuacao_prevista / jogador['preco_num']
        print(f"  • Pontos por Cartoleta: {custo_beneficio:.3f}")
        print(f"  • Isso significa: {pontuacao_prevista:.2f} pontos por C$ {jogador['preco_num']:.2f}")
    
    # Comparação com Outros da Posição
    print()
    print("📈 COMPARAÇÃO COM OUTROS JOGADORES DA MESMA POSIÇÃO:")
    mesma_posicao = df[df['posicao'] == jogador['posicao']].copy()
    
    if pontuacao_prevista is not None:
        # Ordena por pontuação prevista
        mesma_posicao_sorted = mesma_posicao.sort_values('pontuacao_prevista', ascending=False)
        rank = (mesma_posicao_sorted['pontuacao_prevista'] > pontuacao_prevista).sum() + 1
        total = len(mesma_posicao_sorted)
        
        print(f"  • Posição no Ranking de Previsão: {rank}º de {total} jogadores")
        
        # Top 5
        print(f"  • Top 5 {jogador['posicao']}s por Pontuação Prevista:")
        top5 = mesma_posicao_sorted.head(5)
        for i, (_, row) in enumerate(top5.iterrows(), 1):
            marca = " ← VOCÊ" if row['atleta_id'] == atleta_id else ""
            print(f"    {i}. {row['nome']} ({row['clube']}) - {row.get('pontuacao_prevista', 0):.2f} pts - C$ {row['preco_num']:.2f}{marca}")
        
        # Análise de Custo-Benefício
        mesma_posicao['custo_beneficio'] = mesma_posicao['pontuacao_prevista'] / mesma_posicao['preco_num']
        mesma_posicao_cb = mesma_posicao.sort_values('custo_beneficio', ascending=False)
        rank_cb = (mesma_posicao_cb['custo_beneficio'] > custo_beneficio).sum() + 1
        
        print()
        print(f"  • Posição no Ranking de Custo-Benefício: {rank_cb}º de {total} jogadores")
        
        # Top 5 custo-benefício
        print(f"  • Top 5 {jogador['posicao']}s por Custo-Benefício:")
        top5_cb = mesma_posicao_cb.head(5)
        for i, (_, row) in enumerate(top5_cb.iterrows(), 1):
            marca = " ← VOCÊ" if row['atleta_id'] == atleta_id else ""
            cb = row.get('custo_beneficio', 0)
            print(f"    {i}. {row['nome']} ({row['clube']}) - {cb:.3f} pts/cartoleta - C$ {row['preco_num']:.2f}{marca}")
    
    print()
    print("=" * 80)
    print("💡 CONCLUSÃO:")
    print("=" * 80)
    
    if rank is not None and rank_cb is not None:
        if rank_cb <= 5:
            print(f"✅ O jogador foi escolhido porque tem EXCELENTE custo-benefício ({rank_cb}º melhor)!")
            print("   Mesmo que não tenha a maior pontuação prevista, ele oferece muito valor pelo preço.")
        elif rank <= 10:
            print(f"✅ O jogador foi escolhido porque tem boa pontuação prevista ({rank}º melhor).")
        else:
            print(f"⚠️ O jogador pode ter sido escolhido por:")
            print("   • Restrições de orçamento (jogadores melhores eram muito caros)")
            print("   • Restrições de clube (já havia 5 jogadores do mesmo clube)")
            print("   • O otimizador encontrou que ele maximiza a pontuação TOTAL do time")

if __name__ == "__main__":
    # Analisa o Luiz Gustavo do São Paulo (ID 71536)
    analisar_jogador(71536, "Luiz Gustavo")


