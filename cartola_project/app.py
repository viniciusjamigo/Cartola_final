import streamlit as st
import pandas as pd
import os
import json
import warnings
import sys
from utils.config import config, logger
import utils.simulacao
import utils.analise_performance
import utils.modelagem
import utils.coleta_historico
import utils.dashboard

# Importa as funções dos nossos módulos
from utils.modelagem import treinar_modelo, prever_pontuacao, verificar_features_modelo
from utils.simulacao import simular_melhor_risco, simular_desempenho_recente
from utils.analise_performance import gerar_dados_comparativos
from utils.coleta_historico import coletar_dados_historicos

# Silencia avisos do Pandas
warnings.filterwarnings('ignore')

# Importa as funções dos nossos módulos
from utils.coleta_dados import (
    coletar_dados_rodada_atual,
    coletar_partidas_rodada,
    coletar_odds_partidas,
    coletar_historico_partidas, # Nova função importada
    atualizar_partidas_ge,    # Função generalizada
    HISTORICAL_MATCHES_PATH # Constante importada
)
from utils.consolidar_tudo import consolidar
from utils.analise_times import gerar_estatisticas_times # Importando gerador de estatísticas
from utils.analise_estatisticas import (
    analise_times,
    analise_goleiros,
    analise_atacantes,
    analise_recorrencia,
    analise_participacoes,
    analise_participacoes_detalhada,
    analise_combinada_cartola_fbref,
    carregar_clubes
)

from utils.preprocessamento import preprocessar_dados_rodada
from utils.otimizador import otimizar_escalacao, definir_banco_reservas, definir_capitao
from utils.visualizacao import desenhar_campo

# Define os caminhos dos arquivos de dados
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

RAW_DATA_PATH = config.RAW_DATA_PATH
PROCESSED_DATA_PATH = config.PROCESSED_DATA_PATH
MODEL_PATH = os.path.join(config.MODEL_DIR, "modelo_previsao.pkl")
METRICS_PATH = config.METRICS_PATH

# --- Configuração da Página ---
st.set_page_config(
    page_title="Cartola FC Pro - Otimizador de Escalação",
    page_icon="⚽",
    layout="wide"
)

# --- Inicialização de Dados Essenciais ---
# Verifica se o histórico de partidas existe. Se não, baixa automaticamente.
if not os.path.exists(config.HISTORICAL_MATCHES_PATH):
    with st.spinner(f"Inicializando sistema: Baixando histórico de partidas (2022-{config.CURRENT_YEAR})..."):
        coletar_historico_partidas()

# --- Funções de Cache ---
@st.cache_data
def carregar_dados(caminho_arquivo):
    """Carrega um arquivo CSV e o armazena em cache."""
    if os.path.exists(caminho_arquivo):
        return pd.read_csv(caminho_arquivo)
    return None

def obter_analise_estatistica(func_analise, nome_cache, ano, clubes_filtro=None, forcar_atualizacao=False, **kwargs):
    """
    Carrega uma análise do cache em disco ou a executa se necessário.
    """
    cache_path = os.path.join(config.CACHE_DIR_PATH, f"{nome_cache}_{ano}.csv")
    
    if not forcar_atualizacao and os.path.exists(cache_path):
        df = pd.read_csv(cache_path)
        # Aplica filtro de clubes no resultado carregado do cache
        if clubes_filtro and 'Clube' in df.columns:
            df = df[df['Clube'].isin(clubes_filtro)]
        elif clubes_filtro and 'CLUBE' in df.columns:
            df = df[df['CLUBE'].isin(clubes_filtro)]
        return df, None

    # Se não houver cache ou for forçada a atualização, executa a função sem filtro de clubes para cachear tudo
    df_resultado, erro = func_analise(ano=ano, clubes_filtro=None, **kwargs)
    
    if df_resultado is not None and not df_resultado.empty:
        df_resultado.to_csv(cache_path, index=False)
        # Após salvar, aplica o filtro para exibição
        if clubes_filtro and 'Clube' in df_resultado.columns:
            df_resultado = df_resultado[df_resultado['Clube'].isin(clubes_filtro)]
        elif clubes_filtro and 'CLUBE' in df_resultado.columns:
            df_resultado = df_resultado[df_resultado['CLUBE'].isin(clubes_filtro)]
            
    return df_resultado, erro

# --- Interface Principal (UI) ---
st.title("⚽ Cartola FC Pro - Otimizador de Escalação")

# Verifica modelos
modelos_ok, msg_modelos = verificar_features_modelo()
if not modelos_ok and os.path.exists(MODEL_PATH): # Só avisa se já existir algum modelo
    st.warning(
        f"⚠️ **Atenção:** Seus modelos preditivos estão desatualizados e não estão usando as novas funcionalidades "
        f"(Mando de Campo, Força do Adversário, Fase). \n\n"
        f"👉 **Recomendação:** Vá na barra lateral e clique em 'Treinar Novo Modelo Preditivo' para atualizar a IA."
    )

# Criação de abas para separar as funcionalidades
tab_escalacao, tab_analise, tab_estatisticas, tab_dashboard = st.tabs([
    "📋 Escalar Time", 
    "📊 Análise de Performance",
    "📈 Análises Estatísticas",
    "📉 Dashboard Analítico"
])

# ==============================================================================
# ABA 1: ESCALAR TIME (Funcionalidade Original)
# ==============================================================================
with tab_escalacao:
    st.markdown("""
        Use este painel para montar seu time para a próxima rodada usando Inteligência Artificial.
    """)

    # --- Sidebar (Movida para dentro do contexto lógico, mas visualmente fica na esquerda) ---
    # Streamlit sidebar é global, então definimos os inputs aqui e usamos onde precisar
    with st.sidebar:
        st.header("Painel de Controle")
        
        if st.button("🧹 Limpar Cache do Sistema"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache limpo! A página será recarregada.")
            st.rerun()

        with st.expander("🛠️ Ferramentas Avançadas"):
            st.markdown("#### 🎓 Treinamento do Modelo")
            limit_ano = st.number_input("Ano Limite para Treino", min_value=2022, max_value=2026, value=config.CURRENT_YEAR)
            limit_rodada = st.number_input("Rodada Limite para Treino", min_value=1, max_value=38, value=38, help="Define até qual rodada o modelo 'enxerga' os dados.")
            
            if st.button("Treinar Novo Modelo Preditivo (XGBoost)"):
                with st.spinner(f"Treinando modelo até Rodada {limit_rodada}/{limit_ano}..."):
                    modelo = treinar_modelo(ano_limite=limit_ano, rodada_limite=limit_rodada)
                    if modelo:
                        st.cache_data.clear() # Limpa o cache para forçar recarga dos dados e previsões
                        st.success("Modelo treinado com sucesso! Cache limpo.")
                    else:
                        st.error("Erro no treinamento.")
            
            st.divider()
            
            if st.button("Atualizar Histórico de Partidas"):
                with st.spinner("Baixando histórico atualizado..."):
                    coletar_historico_partidas()
                    st.cache_data.clear()
                    st.success("Histórico de partidas atualizado!")

            st.markdown("---")
            st.write("🔍 **Diagnóstico da IA**")
            if st.button("Ver Importância das Features"):
                import joblib
                import plotly.express as px
                
                # Caminho dos modelos (ajustado para a estrutura do projeto)
                model_dir = os.path.join(DATA_DIR, "modelos")
                modelo_path = os.path.join(model_dir, "modelo_ata.pkl") # Padrão: Atacantes
                
                if os.path.exists(modelo_path):
                    try:
                        modelo = joblib.load(modelo_path)
                        
                        # Tenta obter nomes das features
                        if hasattr(modelo, 'feature_names_in_'):
                            features = modelo.feature_names_in_
                        else:
                            try:
                                features = modelo.get_booster().feature_names
                            except:
                                features = [f"Feature {i}" for i in range(len(modelo.feature_importances_))]
                        
                        importances = modelo.feature_importances_
                        
                        # Cria DataFrame para plotar
                        df_imp = pd.DataFrame({
                            'Feature': features,
                            'Importância': importances
                        }).sort_values('Importância', ascending=True)
                        
                        # Filtra para mostrar as mais relevantes e destaca as novas
                        df_imp['Cor'] = df_imp['Feature'].apply(
                            lambda x: 'Nova (Foco)' if x in ['fl_mandante', 'adv_media_gols_sofridos', 'adv_media_gols_feitos'] else 'Padrão'
                        )
                        
                        st.markdown("### 🧠 O que a IA aprendeu (Atacantes)?")
                        st.info("Barras maiores indicam que a variável tem mais peso na decisão do modelo.")
                        
                        fig = px.bar(
                            df_imp.tail(15), 
                            x='Importância', 
                            y='Feature', 
                            orientation='h',
                            color='Cor',
                            color_discrete_map={'Nova (Foco)': '#00C853', 'Padrão': '#1E88E5'},
                            title="Top 15 Fatores Decisivos para Atacantes"
                        )
                        st.plotly_chart(fig)
                        
                        # Feedback específico sobre as novas features
                        row_casa = df_imp[df_imp['Feature'] == 'fl_mandante']
                        if not row_casa.empty:
                            val = row_casa.iloc[0]['Importância']
                            st.write(f"**Impacto do Mando de Campo:** {val:.4f} " + ("(✅ O modelo está usando!)" if val > 0 else "(⚠️ O modelo ignorou)"))
                            
                    except Exception as e:
                        st.error(f"Erro ao ler modelo: {e}")
                else:
                    st.warning("Modelo de Atacantes não encontrado. Treine a IA primeiro.")

        st.header("Opções da Rodada")
        
        # Campo para inserir a chave da API
        api_key = st.text_input(
            "Sua Chave da The Odds API", 
            type="password",
            placeholder="Cole sua chave aqui",
            help="Obtenha uma chave gratuita em https://the-odds-api.com/"
        )
        
        # Configuração de Virada de Rodada
        with st.expander("🔄 Virada de Rodada (Consolidação)", expanded=False):
            is_virada = st.checkbox(
                "Esta é uma Virada de Rodada?", 
                help="Marque se uma rodada ACABOU DE FINALIZAR. Isso fará o sistema baixar os resultados reais da rodada anterior e atualizar o histórico.",
                value=False
            )
            rodada_ant = st.number_input("Qual rodada FINALIZOU?", min_value=1, max_value=38, value=34)

        # Checkbox para forçar a atualização das odds
        force_update = st.checkbox(
            "Forçar atualização das odds",
            help="Marque esta opção para ignorar o cache e buscar as odds mais recentes da API."
        )
        
        # Botão para atualizar os dados
        if st.button("1. Atualizar Dados da Rodada"):
            with st.status("Atualizando dados da rodada...") as status:
                try:
                    msgs = []
                    
                    # 1. Se for virada de rodada, atualiza histórico
                    if is_virada:
                        status.update(label=f"🚀 Iniciando atualização histórica da Rodada {rodada_ant}...", state="running")
                        
                        st.write("Baixando resultados dos jogos (GE)...")
                        atualizar_partidas_ge(config.CURRENT_YEAR)
                        
                        st.write(f"Baixando pontuações dos jogadores (Rodada {rodada_ant})...")
                        coletar_dados_historicos(ano=config.CURRENT_YEAR, rodada_especifica=rodada_ant)
                        
                        st.write("Consolidando banco de dados...")
                        consolidar()
                        
                        st.write(f"Atualizando estatísticas agregadas dos times ({config.PREVIOUS_YEAR}-{config.CURRENT_YEAR})...")
                        gerar_estatisticas_times()
                        msgs.append(f"Histórico e estatísticas atualizados com a rodada {rodada_ant}!")

                    # 2. Coleta dados do mercado atual
                    st.write("Coletando mercado atual (Próxima Rodada)...")
                    coletar_dados_rodada_atual()
                    coletar_partidas_rodada()
                    
                    # 3. Coleta Odds
                    st.write("Coletando odds...")
                    if api_key:
                        coletar_odds_partidas(api_key, force_update=force_update)
                    else:
                        st.warning("Chave de Odds não informada.")
                    
                    # 4. Reprocessamento automático
                    st.write("Gerando arquivo pré-processado...")
                    preprocessar_dados_rodada()

                    status.update(label="✅ Atualização concluída com sucesso!", state="complete")
                    if msgs:
                        for m in msgs: st.success(m)
                        
                    # Limpa cache para recarregar dados novos
                    st.cache_data.clear()
                    
                except Exception as e:
                    logger.error(f"Erro durante a atualização: {e}", exc_info=True)
                    status.update(label=f"❌ Erro durante a atualização: {e}", state="error")


        st.divider()
        
        st.subheader("Configuração do Time")
        # Seleção de orçamento
        orcamento = st.slider("Orçamento (C$)", min_value=80.0, max_value=200.0, value=140.0, step=0.5)

        # Seleção de formação tática
        formacao = st.selectbox(
            "Esquema Tático",
            ("4-3-3", "4-4-2", "3-5-2", "3-4-3")
        )
        
        st.subheader("Modelo de Decisão")
        tipo_modelo = st.radio(
            "Qual inteligência usar?",
            ("IA Avançada (XGBoost)", "Clássico (Média + Odds)"),
            help="A IA usa histórico de 160 mil jogos. O Clássico usa média atual ajustada pelo favoritismo."
        )

        if tipo_modelo == "Clássico (Média + Odds)":
            alpha = st.slider("Influência das Odds", 0.0, 1.0, 0.2, 0.05)
            fator_risco = 0.0
        else:
            alpha = 0.0 
            st.info("O modelo IA considera automaticamente preço, médias e posição.")
            
            fator_risco = st.slider(
                "Apetite ao Risco (Volatilidade)",
                0.0, 2.0, 0.0, 0.1,
                help="0.0 = Conservador. Valores altos priorizam jogadores '8 ou 80'."
            )
            
            st.markdown("---")
            if st.button("🤖 Simular Melhor Risco (Backtest)"):
                with st.spinner("Simulando últimas 10 rodadas..."):
                    resultados, melhor_risco = simular_melhor_risco(window=10)
                    if resultados:
                        st.success(f"Melhor risco histórico: {melhor_risco}")
                        df_res = pd.DataFrame(list(resultados.items()), columns=['Risco', 'Pontos Totais'])
                        st.bar_chart(df_res.set_index('Risco'))
                    else:
                        st.error(melhor_risco)

        # --- Travas e Exclusões (Copiloto) ---
        st.divider()
        st.subheader("Copiloto (Manual)")
        
        df_copiloto = carregar_dados(RAW_DATA_PATH)
        jogadores_opcoes = {}
        if df_copiloto is not None:
            df_copiloto.sort_values('nome', inplace=True)
            jogadores_opcoes = {f"{row['nome']} ({row['clube']})": row['atleta_id'] for _, row in df_copiloto.iterrows()}
        
        travas_nomes = st.multiselect(
            "🔒 Jogadores Intocáveis (Obrigatórios)",
            options=list(jogadores_opcoes.keys()),
            help="Estes jogadores SERÃO escalados."
        )
        
        exclusoes_nomes = st.multiselect(
            "🚫 Jogadores Banidos (Proibidos)",
            options=list(jogadores_opcoes.keys()),
            help="Estes jogadores NÃO SERÃO escalados."
        )
        
        travas_ids = [jogadores_opcoes[nome] for nome in travas_nomes]
        exclusoes_ids = [jogadores_opcoes[nome] for nome in exclusoes_nomes]

    # --- Área de Resultados da Escalação ---
    if 'time_ideal' not in st.session_state:
        st.session_state.time_ideal = None

    if st.button("2. Gerar Time Ideal", type="primary"):
        with st.status("Iniciando pipeline de geração de time...") as status:
            st.write("Pré-processando dados...")
            df_processado = preprocessar_dados_rodada(alpha=alpha if tipo_modelo == "Clássico (Média + Odds)" else 0)
            
            if df_processado is not None:
                # ... Diagnóstico de Dados ...
                if tipo_modelo == "IA Avançada (XGBoost)":
                    st.write("Aplicando Inteligência Artificial (XGBoost)...")
                    df_processado = prever_pontuacao(df_processado)
                else:
                    st.write("Aplicando Regra de Negócios (Clássico)...")
                
                st.write("Otimizando a escalação...")
                time_ideal = otimizar_escalacao(
                    df_processado, 
                    coluna_pontos='pontuacao_prevista',
                    orcamento_total=orcamento,
                    formacao_t_str=formacao,
                    fator_risco=fator_risco,
                    jogadores_fixos=travas_ids,
                    jogadores_excluidos=exclusoes_ids
                )
                st.session_state.time_ideal = time_ideal
                st.session_state.capitao = definir_capitao(time_ideal, 'pontuacao_prevista')
                st.session_state.reservas = definir_banco_reservas(df_processado, time_ideal, 'pontuacao_prevista', 'preco_num')
                
                status.update(label="✅ Time ideal gerado!", state="complete")
            else:
                status.update(label="❌ Falha no pré-processamento.", state="error")

    if st.session_state.time_ideal is not None:
        st.subheader(f"Escalação Ideal ({tipo_modelo} - {formacao})")
        
        time = st.session_state.time_ideal.copy()
        capitao_id = st.session_state.capitao['atleta_id'] if st.session_state.capitao is not None else None
        time['C'] = time['atleta_id'].apply(lambda x: "©️" if x == capitao_id else "")
        
        # VALIDAÇÃO: Verifica duplicatas de atleta_id no time escalado
        if 'atleta_id' in time.columns:
            duplicados = time.duplicated(subset=['atleta_id'], keep=False)
            if duplicados.any():
                st.error(f"⚠️ ERRO: {duplicados.sum()} jogadores duplicados encontrados no time! Isso não deveria acontecer.")
                st.dataframe(time[duplicados][['atleta_id', 'nome', 'posicao', 'clube']])
                # Remove duplicatas para exibição
                time = time.drop_duplicates(subset=['atleta_id'], keep='first')
        
        pontuacao_total = time['pontuacao_prevista'].sum()
        custo_total = time['preco_num'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Pontuação Prevista", f"{pontuacao_total:.2f}")
        col2.metric("Custo do Time", f"C$ {custo_total:.2f}")
        col3.metric("Orçamento Restante", f"C$ {orcamento - custo_total:.2f}")
        
        # Define as colunas com atleta_id como primeira
        colunas_exibicao = ['C', 'atleta_id', 'nome', 'posicao', 'clube', 'adversario', 'preco_num', 'media_num', 'pontuacao_prevista']
        # Garante que apenas colunas existentes sejam incluídas
        colunas_exibicao = [c for c in colunas_exibicao if c in time.columns]
        
        st.dataframe(
            time[colunas_exibicao],
            width=1200, 
            hide_index=True,
            column_config={
                "C": st.column_config.TextColumn("Cap", width="small"),
                "atleta_id": st.column_config.NumberColumn("ID", width="small"),
                "adversario": st.column_config.TextColumn("Adversário"),
                "preco_num": st.column_config.NumberColumn("Preço", format="%.2f"),
                "media_num": st.column_config.NumberColumn("Média", format="%.2f"),
                "pontuacao_prevista": st.column_config.NumberColumn("Previsto", format="%.2f"),
            }
        )
        
        st.divider()
        if st.checkbox("🏟️ Ver Campinho", value=True):
            fig_campo = desenhar_campo(time, formacao)
            st.pyplot(fig_campo)
        
        if 'reservas' in st.session_state and not st.session_state.reservas.empty:
            with st.expander("🏦 Banco de Reservas de Luxo"):
                st.dataframe(st.session_state.reservas[['nome', 'clube', 'posicao', 'preco_num', 'pontuacao_prevista']], hide_index=True)
                
        st.divider()
        with st.expander("📅 Desempenho Recente (Simulação)", expanded=True):
            # Força o uso da IA Nova com Risco 0 para a simulação de desempenho recente
            resultados_simulacao = simular_desempenho_recente(
                window=3,
                orcamento=orcamento,
                formacao=formacao,
                risco=0.0,
                modelo_tipo="IA Avançada (XGBoost)",
                alpha=alpha
            )
            
            if resultados_simulacao:
                cols_sim = st.columns(len(resultados_simulacao))
                for i, (rodada, pontos) in enumerate(resultados_simulacao.items()):
                    with cols_sim[i]: st.metric(f"Rodada {rodada}", f"{pontos:.2f} pts")


# ==============================================================================
# ABA 2: ANÁLISE DE PERFORMANCE (Nova Funcionalidade)
# ==============================================================================
with tab_analise:
    st.header("📈 Comparativo de Performance: Batalha de Modelos")
    st.markdown("""
        Esta análise compara o **seu desempenho (Vini)** contra diferentes estratégias de IA treinadas do zero e o "Time Perfeito".
        
        *   **IA Conservadora**: Aposta na média simples.
        *   **IA Ousadia (Random Forest)**: Treinada para buscar "mitadas" (>8 pts), ignorando regularidade.
        *   **IA Retranca (Linear)**: Treinada para consistência e defesa, penalizando riscos.
    """)
    
    if st.button("Gerar Gráfico Comparativo"):
        # LIMPEZA DE CACHE: Garante que os novos modelos e a nova lógica sejam usados
        st.cache_data.clear()
        
        # Força reload explícito do módulo no momento do clique para garantir atualização
        import sys
        if 'utils.analise_performance' in sys.modules:
            importlib.reload(sys.modules['utils.analise_performance'])
        
        with st.spinner("Gerando análise comparativa... (Isso pode levar um minuto)"):
            # Usa chamada direta do módulo para garantir que a versão reload seja usada
            try:
                retorno = utils.analise_performance.gerar_dados_comparativos(ano=config.PREVIOUS_YEAR)
                times_detalhados = None
                
                if len(retorno) == 4:
                    df_comparativo, erro, rmse_scores, times_detalhados = retorno
                elif len(retorno) == 3:
                    # Fallback para caso o reload falhe parcialmente
                    df_comparativo, erro, rmse_scores = retorno
                    st.warning("Aviso: Versão intermediária do módulo. Detalhes dos times não disponíveis.")
                else:
                    # Fallback extremo
                    df_comparativo, erro = retorno
                    rmse_scores = {}
            except Exception as e:
                 st.error(f"Erro interno na execução: {e}")
                 df_comparativo, erro, rmse_scores = None, str(e), None
        
            if erro:
                st.error(erro)
            elif df_comparativo is not None and not df_comparativo.empty:
                
                # Exibe o RMSE primeiro
                if rmse_scores: # Simplificado check
                    st.subheader("📊 Precisão dos Modelos (RMSE)")
                    st.markdown("O RMSE (Raiz do Erro Quadrático Médio) mede o erro das previsões. **Quanto menor, melhor.**")
                    
                    col1, col2 = st.columns(2)
                    
                    # Calcula o delta para a métrica
                    rmse_nova = rmse_scores.get('nova', 0)
                    rmse_legado = rmse_scores.get('legado', 0)
                    
                    if rmse_nova > 0 and rmse_legado > 0:
                        delta_rmse = rmse_nova - rmse_legado
                        
                        col1.metric(
                            "IA Nova (Com Mando)", 
                            f"{rmse_nova:.4f}", 
                            delta=f"{delta_rmse:.4f}", 
                            delta_color="inverse",
                            help="Um delta negativo (verde) significa que o erro da IA Nova é menor (melhor) que o da IA Legado."
                        )
                        col2.metric(
                            "IA Legado (Sem Mando)", 
                            f"{rmse_legado:.4f}"
                        )
                    else:
                        st.warning("Dados insuficientes para calcular RMSE comparativo (Necessário histórico com pontuações reais).")
                    st.divider()

                cols_presentes = [c for c in df_comparativo.columns if c != 'Rodada']
                
                # MAPEAMENTO DE CORES ATUALIZADO
                color_map = {
                    "Vini (Você)": "#00C853",              # Verde
                    "Máximo Possível": "#FFC107",          # Amarelo
                    "IA Legado (Sem Mando)": "#FF4B4B",    # Vermelho (Modelo Antigo)
                    "IA Nova (Com Mando)": "#1E88E5"       # Azul (Modelo Novo)
                }
                
                final_colors = []
                for col in cols_presentes:
                    final_colors.append(color_map.get(col, "#888888"))
                
                # Renderiza o gráfico
                st.subheader("Gráfico de Evolução (Rodada a Rodada)")
                st.line_chart(
                    df_comparativo.set_index('Rodada')[cols_presentes],
                    color=final_colors
                )
                
                # --- BOTÃO DE EXPORTAÇÃO CSV ---
                if times_detalhados and len(times_detalhados) > 0:
                    st.divider()
                    st.subheader("📥 Exportar Dados Detalhados")
                    
                    # Função para consolidar todos os times em um único DataFrame
                    def consolidar_times_para_csv(times_detalhados_dict):
                        """Consolida todos os times detalhados em um único DataFrame para exportação CSV"""
                        lista_times = []
                        
                        for rodada in sorted(times_detalhados_dict.keys()):
                            df_time = times_detalhados_dict[rodada].copy()
                            
                            # Garante que as colunas necessárias existam
                            colunas_necessarias = ['atleta_id', 'capitao', 'posicao', 'apelido', 'clube', 'ia_nova', 'pontuacao']
                            for col in colunas_necessarias:
                                if col not in df_time.columns:
                                    if col == 'capitao':
                                        df_time[col] = False
                                    elif col in ['ia_nova', 'pontuacao']:
                                        df_time[col] = 0.0
                                    else:
                                        df_time[col] = ''
                            
                            df_time['atleta_id'] = pd.to_numeric(df_time['atleta_id'], errors='coerce').fillna(0).astype(int)
                            
                            def converter_para_string_seguro(serie):
                                """Converte série para string de forma segura, tratando valores nulos"""
                                serie_str = serie.astype(str)
                                serie_str = serie_str.replace(['nan', 'None', 'NaN', '<NA>', 'NaT'], '')
                                return serie_str
                            
                            posicao_str = converter_para_string_seguro(df_time['posicao']) if 'posicao' in df_time.columns else pd.Series([''] * len(df_time))
                            apelido_str = converter_para_string_seguro(df_time['apelido']) if 'apelido' in df_time.columns else pd.Series([''] * len(df_time))
                            clube_str = converter_para_string_seguro(df_time['clube']) if 'clube' in df_time.columns else pd.Series([''] * len(df_time))
                            
                            df_export = pd.DataFrame({
                                'Rodada': rodada,
                                'atleta_id': df_time['atleta_id'].values,
                                'C': df_time['capitao'].apply(lambda x: 'C' if x else '').values,
                                'posicao': posicao_str.values,
                                'apelido': apelido_str.values,
                                'clube': clube_str.values,
                                'Previsto (IA)': pd.to_numeric(df_time['ia_nova'], errors='coerce').fillna(0.0).round(2),
                                'Real (Oficial)': pd.to_numeric(df_time['pontuacao'], errors='coerce').fillna(0.0).round(2)
                            })
                            
                            lista_times.append(df_export)
                        
                        if not lista_times:
                            return None
                        
                        df_final = pd.concat(lista_times, ignore_index=True)
                        return df_final
                    
                    df_exportar = consolidar_times_para_csv(times_detalhados)
                    
                    if df_exportar is not None and not df_exportar.empty:
                        colunas_finais = ['Rodada', 'atleta_id', 'C', 'posicao', 'apelido', 'clube', 'Previsto (IA)', 'Real (Oficial)']
                        df_exportar_final = df_exportar[colunas_finais].copy()
                        
                        df_exportar_final['Previsto (IA)'] = df_exportar_final['Previsto (IA)'].apply(
                            lambda x: f"{float(x):.2f}".replace('.', ',') if pd.notna(x) else '0,00'
                        )
                        df_exportar_final['Real (Oficial)'] = df_exportar_final['Real (Oficial)'].apply(
                            lambda x: f"{float(x):.2f}".replace('.', ',') if pd.notna(x) else '0,00'
                        )
                        
                        csv_string = df_exportar_final.to_csv(index=False, sep=';', encoding='utf-8-sig')
                        
                        st.download_button(
                            label="📥 Baixar CSV com Times Detalhados da IA Nova",
                            data=csv_string,
                            file_name=f"times_ia_nova_rodadas_{df_comparativo['Rodada'].min()}_{df_comparativo['Rodada'].max()}.csv",
                            mime="text/csv",
                            help="Exporta todos os times selecionados pelo modelo IA Nova para cada rodada do gráfico"
                        )
                        
                        st.caption(f"✅ O arquivo contém {len(df_exportar)} jogadores de {len(times_detalhados)} rodadas.")
                
                # Tabela
                st.subheader("Tabela Detalhada")
                st.dataframe(
                    df_comparativo.style.highlight_max(axis=1, color='lightgreen', subset=cols_presentes),
                    width=1200
                )
                
                # --- Métricas Gerais (Placar Final) ---
                st.subheader("🏆 Placar Final (Média de Pontos)")
                
                medias = df_comparativo.mean().drop("Rodada").sort_values(ascending=False)
                
                cols = st.columns(len(medias))
                
                for i, (nome, media) in enumerate(medias.items()):
                    delta = None
                    if nome != "Vini (Você)" and "Vini (Você)" in df_comparativo.columns:
                        diff = media - df_comparativo["Vini (Você)"].mean()
                        delta = f"{diff:+.1f} vs Você"
                    
                    cor_texto = color_map.get(nome, "#000000")
                    
                    with cols[i]:
                        st.markdown(f"<h4 style='color: {cor_texto}'>{nome}</h4>", unsafe_allow_html=True)
                        st.metric("Média", f"{media:.1f} pts", delta=delta)
                
                if len(medias) > 1:
                    melhor_modelo = medias.index[1]
                    if melhor_modelo == "Vini (Você)":
                        st.success("🎉 Parabéns! Você está superando todas as estratégias automáticas da IA!")
                    else:
                        st.info(f"💡 Dica: A estratégia **'{melhor_modelo}'** está performando melhor. Talvez valha a pena considerá-la na próxima escalação.")
                
                # --- DETALHAMENTO DOS TIMES (IA NOVA) ---
                if times_detalhados:
                    st.divider()
                    st.subheader("🕵️ Detalhes: Escalações da IA Nova (Últimas 3 Rodadas)")
                    st.markdown("Abaixo, você vê exatamente quem a IA escalou e a comparação entre a expectativa (Previsto) e a realidade (Real).")
                    
                    for rodada in sorted(times_detalhados.keys(), reverse=True):
                        df_time = times_detalhados[rodada]
                        
                        soma_real = df_time['pontuacao'].sum()
                        capitao_row = df_time[df_time['capitao'] == True]
                        bonus_real = (capitao_row.iloc[0]['pontuacao'] * 0.5) if not capitao_row.empty else 0
                        total_real_final = soma_real + bonus_real
                        
                        soma_previsto = df_time['ia_nova'].sum()
                        cap_prev_row = df_time[df_time['capitao'] == True]
                        bonus_previsto = (cap_prev_row.iloc[0]['ia_nova'] * 0.5) if not cap_prev_row.empty else 0
                        total_previsto_final = soma_previsto + bonus_previsto
                        
                        with st.expander(f"Rodada {rodada} | Real: {total_real_final:.2f} pts  (A IA previa: {total_previsto_final:.2f})", expanded=False):
                            if 'atleta_id' in df_time.columns:
                                duplicados = df_time.duplicated(subset=['atleta_id'], keep=False)
                                if duplicados.any():
                                    st.error(f"⚠️ ATENÇÃO: {duplicados.sum()} jogadores duplicados encontrados na rodada {rodada}!")
                            
                            colunas_exibicao = ['capitao', 'atleta_id', 'posicao', 'apelido', 'clube', 'ia_nova', 'pontuacao']
                            colunas_exibicao = [c for c in colunas_exibicao if c in df_time.columns]
                            
                            df_exibir = df_time[colunas_exibicao].rename(columns={
                                'capitao': 'C',
                                'atleta_id': 'ID',
                                'ia_nova': 'Previsto (IA)',
                                'pontuacao': 'Real (Oficial)'
                            }).sort_values('posicao')
                            
                            st.dataframe(
                                df_exibir.style.format({
                                    'Previsto (IA)': '{:.2f}',
                                    'Real (Oficial)': '{:.2f}'
                                }).applymap(lambda x: 'background-color: #ffffcc' if x is True else '', subset=['C']),
                                use_container_width=True
                            )
                            st.caption(f"✅ O gráfico acima já está usando essa pontuação Real ({total_real_final:.2f}). A coluna 'Previsto' é apenas para você ver o que a IA esperava.")

            else:
                st.warning("Nenhum dado encontrado.")


# ==============================================================================
# ABA 3: ANÁLISES ESTATÍSTICAS (Similar à BIA)
# ==============================================================================
with tab_estatisticas:
    st.header("📈 Análises Estatísticas - Estilo BIA")
    st.markdown("""
        Análises estatísticas avançadas similares à plataforma BIA Score.
        Os dados são carregados automaticamente. Use o botão abaixo para forçar uma atualização se houver dados novos.
    """)
    
    # Botão de atualização global da aba
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        forcar_update = st.button("🔄 Atualizar Análises", help="Força o recálculo de todas as estatísticas para o ano selecionado.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        anos_disponiveis = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]
        ano_selecionado = st.selectbox(
            "Ano",
            options=anos_disponiveis,
            index=0,  # 2026 como default
            help="Selecione o ano para análise"
        )
    
    with col2:
        clubes_map = carregar_clubes()
        clubes_lista = sorted(list(clubes_map.values()))
        clubes_selecionados = st.multiselect(
            "Filtrar por Clubes (opcional)",
            options=clubes_lista,
            help="Deixe vazio para mostrar todos os clubes"
        )
        clubes_filtro = clubes_selecionados if clubes_selecionados else None
    
    st.divider()
    
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
        "🏆 Análise de Times",
        "🥅 Goleiros",
        "⚽ Atacantes",
        "📊 Recorrência",
        "👥 Participações",
        "🔗 Cartola + FBref"
    ])
    
    with sub_tab1:
        st.subheader("Análise de Times")
        df_resultado, erro = obter_analise_estatistica(
            analise_times, "analise_times", ano_selecionado, clubes_filtro, forcar_atualizacao=forcar_update
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            st.dataframe(
                df_resultado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Probabilidade de Vitória (%)": st.column_config.NumberColumn("Prob. Vitória (%)", format="%.1f"),
                    "Gols Sofridos (Média)": st.column_config.NumberColumn("Gols Sofridos", format="%.2f"),
                    "SG's Conquistados (%)": st.column_config.NumberColumn("SG's Conq. (%)", format="%.1f"),
                    "Gols Marcados - Adversário (Média)": st.column_config.NumberColumn("Gols Adv. (Média)", format="%.2f"),
                    "SG's Cedidos - Adversário (%)": st.column_config.NumberColumn("SG's Ced. Adv. (%)", format="%.1f"),
                }
            )
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    with sub_tab2:
        st.subheader("Análise de Goleiros")
        df_resultado, erro = obter_analise_estatistica(
            analise_goleiros, "analise_goleiros", ano_selecionado, clubes_filtro, forcar_atualizacao=forcar_update
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            st.dataframe(
                df_resultado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Média": st.column_config.NumberColumn(format="%.2f"),
                    "M. Básica": st.column_config.NumberColumn(format="%.2f"),
                    "Prob. de SG (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Prob. Vitória (%)": st.column_config.NumberColumn(format="%.1f"),
                }
            )
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    with sub_tab3:
        st.subheader("Análise de Atacantes")
        df_resultado, erro = obter_analise_estatistica(
            analise_atacantes, "analise_atacantes", ano_selecionado, clubes_filtro, forcar_atualizacao=forcar_update
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            st.dataframe(
                df_resultado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Média": st.column_config.NumberColumn(format="%.2f"),
                    "M. Básica": st.column_config.NumberColumn(format="%.2f"),
                    "Prob. Ataque (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Prob. Vitória (%)": st.column_config.NumberColumn(format="%.1f"),
                }
            )
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    with sub_tab4:
        st.subheader("Análise de Recorrência")
        posicao_filtro = st.selectbox(
            "Filtrar por Posição (opcional)",
            options=[None, 1, 2, 3, 4, 5, 6],
            format_func=lambda x: {
                None: "Todas", 1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"
            }.get(x, "Todas"),
            key="pos_recorrencia"
        )
        
        df_resultado, erro = obter_analise_estatistica(
            analise_recorrencia, "analise_recorrencia", ano_selecionado, clubes_filtro, forcar_atualizacao=forcar_update, posicao_filtro=posicao_filtro
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            st.dataframe(
                df_resultado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "3 Jogos": st.column_config.NumberColumn(format="%.2f"),
                    "5 Jogos": st.column_config.NumberColumn(format="%.2f"),
                    "Últimos 3 Jogos (%)": st.column_config.NumberColumn(format="%.2f"),
                    "% D": st.column_config.NumberColumn(format="%.1f"),
                }
            )
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    with sub_tab5:
        st.subheader("Análise de Participações - Estilo BIA Score")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            posicao_f = st.selectbox(
                "Posição", options=[None, 1, 2, 3, 4, 5, 6],
                format_func=lambda x: {None: "Todas", 1: "GOL", 2: "LAT", 3: "ZAG", 4: "MEI", 5: "ATA", 6: "TEC"}.get(x, "Todas"),
                key="pos_part"
            )
        with col_f2:
            status_f = st.multiselect("Status", options=["Provável", "Dúvida", "Suspenso", "Contundido", "Nulo"], key="status_part")
        with col_f3:
            min_j = st.slider("Jogos ≥", 0, 50, 5, key="min_j_part")
        
        busca_n = st.text_input("Buscar por nome...", key="busca_n_part")
        
        df_resultado, erro = obter_analise_estatistica(
            analise_participacoes_detalhada, "analise_participacoes", ano_selecionado, clubes_filtro, 
            forcar_atualizacao=forcar_update, posicao_filtro=posicao_f, status_filtro=status_f if status_f else None, min_jogos=min_j
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            if busca_n:
                df_resultado = df_resultado[df_resultado['Nome'].str.contains(busca_n, case=False, na=False)]
            
            st.dataframe(
                df_resultado,
                use_container_width=True, hide_index=True,
                column_config={
                    "Jogos": st.column_config.NumberColumn(format="%d"),
                    "Média": st.column_config.NumberColumn(format="%.2f"),
                    "M. Básica": st.column_config.NumberColumn(format="%.2f"),
                    "Escanteios/Jogo": st.column_config.NumberColumn(format="%.2f"),
                    "XA/Jogo": st.column_config.NumberColumn(format="%.2f"),
                    "XG/Jogo": st.column_config.NumberColumn(format="%.2f"),
                    "Assistências": st.column_config.NumberColumn(format="%d"),
                    "Gols": st.column_config.NumberColumn(format="%d"),
                    "G + A": st.column_config.NumberColumn(format="%d"),
                }
            )
    
    with sub_tab6:
        st.subheader("Análise Combinada: Cartola FC + FBref")
        c1, c2, c3 = st.columns(3)
        with c1:
            pos_comb = st.selectbox("Posição", options=['Todos', 'GOL', 'LAT', 'ZAG', 'MEI', 'ATA'], index=0, key='pos_c')
            pos_comb = None if pos_comb == 'Todos' else pos_comb
        with c2:
            min_j_comb = st.slider("Jogos ≥", 0, 50, 5, key='min_j_c')
        with c3:
            busca_n_comb = st.text_input("Buscar por nome...", key='busca_n_c')
        
        df_resultado, erro = obter_analise_estatistica(
            analise_combinada_cartola_fbref, "analise_combinada", ano_selecionado, clubes_filtro, 
            forcar_atualizacao=forcar_update, posicao_filtro=pos_comb, status_filtro=None, min_jogos=min_j_comb
        )
        
        if erro:
            st.error(erro)
        elif df_resultado is not None and not df_resultado.empty:
            if busca_n_comb:
                df_resultado = df_resultado[df_resultado['NOME'].str.contains(busca_n_comb, case=False, na=False)]
            
            st.info(f"📊 **{len(df_resultado)} jogadores** encontrados.")
            st.dataframe(
                df_resultado,
                use_container_width=True, hide_index=True,
                column_config={
                    "JOGOS": st.column_config.NumberColumn(format="%d"),
                    "MÉDIA": st.column_config.NumberColumn(format="%.2f"),
                    "M. BÁSICA": st.column_config.NumberColumn(format="%.2f"),
                    "XA/JOGO": st.column_config.NumberColumn(format="%.3f"),
                    "XG/JOGO": st.column_config.NumberColumn(format="%.3f"),
                }
            )

# ==============================================================================
# ABA 4: DASHBOARD ANALÍTICO (Nova Funcionalidade)
# ==============================================================================
with tab_dashboard:
    utils.dashboard.render_dashboard()
