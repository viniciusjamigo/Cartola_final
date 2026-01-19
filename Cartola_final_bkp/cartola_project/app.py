import streamlit as st
import pandas as pd
import os
import json
import warnings
import importlib
import sys
import utils.simulacao
import utils.analise_performance
import utils.modelagem
import utils.coleta_historico

# Força recarregamento dos módulos para garantir atualização
if 'utils.modelagem' in sys.modules:
    importlib.reload(sys.modules['utils.modelagem'])
if 'utils.simulacao' in sys.modules:
    importlib.reload(sys.modules['utils.simulacao'])
if 'utils.analise_performance' in sys.modules:
    importlib.reload(sys.modules['utils.analise_performance'])
if 'utils.coleta_historico' in sys.modules:
    importlib.reload(sys.modules['utils.coleta_historico'])

# Re-importa as funções após o reload para atualizar as referências locais
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
    atualizar_partidas_2025,    # GE Matches
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
from utils.modelagem import treinar_modelo, prever_pontuacao, verificar_features_modelo
from utils.simulacao import simular_melhor_risco, simular_desempenho_recente
from utils.visualizacao import desenhar_campo
from utils.analise_performance import gerar_dados_comparativos

# Define os caminhos dos arquivos de dados
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

RAW_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual.csv")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "rodada_atual_processada.csv")
MODEL_PATH = os.path.join(DATA_DIR, "modelos", "modelo_previsao.pkl")
METRICS_PATH = os.path.join(DATA_DIR, "modelos", "metricas.json")

# --- Configuração da Página ---
st.set_page_config(
    page_title="Cartola FC Pro - Otimizador de Escalação",
    page_icon="⚽",
    layout="wide"
)

# --- Inicialização de Dados Essenciais ---
# Verifica se o histórico de partidas existe. Se não, baixa automaticamente.
if not os.path.exists(HISTORICAL_MATCHES_PATH):
    with st.spinner("Inicializando sistema: Baixando histórico de partidas (2022-2025)..."):
        coletar_historico_partidas()

# --- Funções de Cache ---
@st.cache_data
def carregar_dados(caminho_arquivo):
    """Carrega um arquivo CSV e o armazena em cache."""
    if os.path.exists(caminho_arquivo):
        return pd.read_csv(caminho_arquivo)
    return None

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
tab_escalacao, tab_analise, tab_estatisticas = st.tabs([
    "📋 Escalar Time", 
    "📊 Análise de Performance",
    "📈 Análises Estatísticas"
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
            limit_ano = st.number_input("Ano Limite para Treino", min_value=2022, max_value=2026, value=2025)
            limit_rodada = st.number_input("Rodada Limite para Treino", min_value=1, max_value=38, value=33, help="Define até qual rodada o modelo 'enxerga' os dados. Útil para evitar rodadas com dados incompletos (ex: R34).")
            
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
            with st.spinner("Processando..."):
                try:
                    msgs = []
                    
                    # 1. Se for virada de rodada, atualiza histórico
                    if is_virada:
                        st.info(f"🚀 Iniciando atualização histórica da Rodada {rodada_ant}...")
                        
                        st.write("1/6 - Baixando resultados dos jogos (GE)...")
                        atualizar_partidas_2025()
                        
                        st.write(f"2/6 - Baixando pontuações dos jogadores (Rodada {rodada_ant})...")
                        # Baixa SOMENTE a rodada especifica
                        coletar_dados_historicos(ano=2025, rodada_especifica=rodada_ant)
                        
                        st.write("3/6 - Consolidando banco de dados...")
                        consolidar()
                        
                        st.write("4/6 - Atualizando estatísticas agregadas dos times (2024-2025)...")
                        gerar_estatisticas_times()
                        msgs.append(f"Histórico e estatísticas atualizados com a rodada {rodada_ant}!")

                    # 2. Coleta dados do mercado atual (independente de ser virada ou não)
                    st.write("5/6 - Coletando mercado atual (Próxima Rodada)...")
                    coletar_dados_rodada_atual()
                    coletar_partidas_rodada()
                    
                    # 3. Coleta Odds
                    st.write("6/6 - Coletando odds...")
                    if api_key:
                        coletar_odds_partidas(api_key, force_update=force_update)
                    else:
                        st.warning("Chave de Odds não informada. As odds não foram atualizadas.")
                    
                    # 4. Reprocessamento automático
                    st.write("🔄 Gerando arquivo pré-processado com novos dados...")
                    preprocessar_dados_rodada()

                    st.success("✅ Atualização concluída com sucesso!")
                    if msgs:
                        for m in msgs: st.success(m)
                        
                    # Limpa cache para recarregar dados novos
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"Erro durante a atualização: {e}")


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
        with st.spinner("Iniciando pipeline..."):
            st.write("1/3 - Pré-processando dados...")
            df_processado = preprocessar_dados_rodada(alpha=alpha if tipo_modelo == "Clássico (Média + Odds)" else 0)
            
            if df_processado is not None:
                # Diagnóstico de Dados
                if 'fator_casa' in df_processado.columns and df_processado['fator_casa'].abs().sum() == 0:
                    st.warning("⚠️ AVISO: Não foi possível identificar quem joga em casa (Mando de Campo zerado). Verifique se os dados da rodada estão atualizados.")
                
                # --- DEBUG VISUAL PARA O USUÁRIO ---
                if 'fator_casa' in df_processado.columns:
                    n_casa = (df_processado['fator_casa'] == 1).sum()
                    n_fora = (df_processado['fator_casa'] == -1).sum()
                    
                    if n_casa > 0:
                        st.success(f"✅ Mando de Campo Identificado! ({n_casa} Jogadores em Casa)")
                    else:
                        st.error("❌ ERRO CRÍTICO: Nenhum jogador identificado em casa. O modelo não funcionará corretamente.")

                    with st.expander("🕵️ Raio-X dos Dados (Clique para abrir)", expanded=True):
                        st.markdown("### Verifique se as colunas abaixo estão preenchidas:")
                        cols_debug = [c for c in ['nome', 'clube', 'fator_casa', 'adversario', 'pontuacao_prevista'] if c in df_processado.columns]
                        
                        # Formata para ficar mais bonito
                        df_show = df_processado[cols_debug].head(10).copy()
                        df_show['fator_casa'] = df_show['fator_casa'].map({1: '🏠 Casa', -1: '✈️ Fora', 0: '❓ N/A'})
                        
                        st.dataframe(df_show, use_container_width=True)
                        st.info("Legenda: 🏠 = Joga em Casa (+Bônus) | ✈️ = Joga Fora (-Penalidade)")

                if tipo_modelo == "IA Avançada (XGBoost)":
                    st.write("2/3 - Aplicando Inteligência Artificial (XGBoost)...")
                    df_processado = prever_pontuacao(df_processado)
                else:
                    st.write("2/3 - Aplicando Regra de Negócios (Clássico)...")
                
                st.write("3/3 - Otimizando a escalação...")
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
                
                st.success("Time ideal gerado.")
            else:
                st.error("Falha no pré-processamento.")

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
        colunas_exibicao = ['C', 'atleta_id', 'nome', 'posicao', 'clube', 'preco_num', 'media_num', 'pontuacao_prevista']
        # Garante que apenas colunas existentes sejam incluídas
        colunas_exibicao = [c for c in colunas_exibicao if c in time.columns]
        
        st.dataframe(
            time[colunas_exibicao],
            width=1200, # Use um valor fixo ou 'stretch' se preferir
            hide_index=True,
            column_config={
                "C": st.column_config.TextColumn("Cap", width="small"),
                "atleta_id": st.column_config.NumberColumn("ID", width="small"),
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
                retorno = utils.analise_performance.gerar_dados_comparativos(ano=2025)
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
                    
                    # Debug visual se as chaves estiverem faltando
                    # st.write(rmse_scores) 
                    
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
                    # Se a coluna não estiver no mapa (ex: nome antigo), usa cinza
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
                            
                            # Prepara o DataFrame para exportação
                            # Converte atleta_id para int, garantindo que não seja NaN
                            df_time['atleta_id'] = pd.to_numeric(df_time['atleta_id'], errors='coerce').fillna(0).astype(int)
                            
                            # Converte colunas categóricas para string, tratando valores nulos corretamente
                            def converter_para_string_seguro(serie):
                                """Converte série para string de forma segura, tratando valores nulos"""
                                # Se já for string, retorna como está (após tratamento de nulos)
                                serie_str = serie.astype(str)
                                # Substitui representações de NaN/None por string vazia
                                serie_str = serie_str.replace(['nan', 'None', 'NaN', '<NA>', 'NaT'], '')
                                return serie_str
                            
                            # Prepara as colunas de texto de forma segura
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
                        # Reordena as colunas conforme solicitado pelo usuário (incluindo Rodada)
                        colunas_finais = ['Rodada', 'atleta_id', 'C', 'posicao', 'apelido', 'clube', 'Previsto (IA)', 'Real (Oficial)']
                        df_exportar_final = df_exportar[colunas_finais].copy()
                        
                        # Formata os números com vírgula como separador decimal (2 casas decimais)
                        df_exportar_final['Previsto (IA)'] = df_exportar_final['Previsto (IA)'].apply(
                            lambda x: f"{float(x):.2f}".replace('.', ',') if pd.notna(x) else '0,00'
                        )
                        df_exportar_final['Real (Oficial)'] = df_exportar_final['Real (Oficial)'].apply(
                            lambda x: f"{float(x):.2f}".replace('.', ',') if pd.notna(x) else '0,00'
                        )
                        
                        # Converte para CSV com separador ; e decimais com ,
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
                    # Se a coluna Vini existir, compara com ela
                    if nome != "Vini (Você)" and "Vini (Você)" in df_comparativo.columns:
                        diff = media - df_comparativo["Vini (Você)"].mean()
                        delta = f"{diff:+.1f} vs Você"
                    
                    # Cores nas métricas (opcional, usando markdown)
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
                        
                        # Cálculo correto dos totais (base + capitão)
                        # O dataframe tem 12 linhas (11 titulares + 1 técnico).
                        # Capitão ganha bônus.
                        
                        # Total Real
                        soma_real = df_time['pontuacao'].sum()
                        capitao_row = df_time[df_time['capitao'] == True]
                        # O bônus do capitão é 50% da pontuação (já que a soma total já inclui 100%)
                        # Regra: Pontos Totais = Soma de Todos + (0.5 * Pontos Capitão)
                        bonus_real = (capitao_row.iloc[0]['pontuacao'] * 0.5) if not capitao_row.empty else 0
                        total_real_final = soma_real + bonus_real
                        
                        # Total Previsto
                        soma_previsto = df_time['ia_nova'].sum()
                        # Se a IA previu o capitão, o bônus de previsão também deve ser ajustado,
                        # mas aqui geralmente já vem calculado ou não afeta o 'Real'. 
                        # Vamos manter coerente: Soma + 0.5 * Capitão
                        cap_prev_row = df_time[df_time['capitao'] == True]
                        bonus_previsto = (cap_prev_row.iloc[0]['ia_nova'] * 0.5) if not cap_prev_row.empty else 0
                        total_previsto_final = soma_previsto + bonus_previsto
                        
                        pts_grafico = df_comparativo[df_comparativo['Rodada'] == rodada]['IA Nova (Com Mando)'].iloc[0]
                        
                        # O pts_grafico DEVE ser igual ao total_real_final
                        # Mostramos isso claramente no cabeçalho
                        
                        with st.expander(f"Rodada {rodada} | Real: {total_real_final:.2f} pts  (A IA previa: {total_previsto_final:.2f})", expanded=False):
                            # Verifica se há duplicatas antes de exibir
                            if 'atleta_id' in df_time.columns:
                                duplicados = df_time.duplicated(subset=['atleta_id'], keep=False)
                                if duplicados.any():
                                    st.error(f"⚠️ ATENÇÃO: {duplicados.sum()} jogadores duplicados encontrados na rodada {rodada}!")
                            
                            # Define colunas incluindo atleta_id como primeira
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
        Use os filtros abaixo para personalizar as análises.
    """)
    
    # Filtros comuns
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro de ano
        anos_disponiveis = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]
        ano_selecionado = st.selectbox(
            "Ano",
            options=anos_disponiveis,
            index=0,  # 2025 como default
            help="Selecione o ano para análise"
        )
    
    with col2:
        # Filtro de clubes
        clubes_map = carregar_clubes()
        clubes_lista = sorted(list(clubes_map.values()))
        clubes_selecionados = st.multiselect(
            "Filtrar por Clubes (opcional)",
            options=clubes_lista,
            help="Deixe vazio para mostrar todos os clubes"
        )
        clubes_filtro = clubes_selecionados if clubes_selecionados else None
    
    st.divider()
    
    # Sub-abas para diferentes análises
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
        "🏆 Análise de Times",
        "🥅 Goleiros",
        "⚽ Atacantes",
        "📊 Recorrência",
        "👥 Participações",
        "🔗 Cartola + FBref"
    ])
    
    # ===== ANÁLISE DE TIMES =====
    with sub_tab1:
        st.subheader("Análise de Times")
        st.markdown("""
            Estatísticas consolidadas dos times incluindo:
            - Probabilidade de Vitória
            - Probabilidade de Clean Sheet (SG)
            - Gols sofridos e marcados
            - Performance defensiva e ofensiva
        """)
        
        if st.button("Gerar Análise de Times", key="btn_times"):
            with st.spinner("Calculando estatísticas dos times..."):
                df_resultado, erro = analise_times(ano=ano_selecionado, clubes_filtro=clubes_filtro)
                
                if erro:
                    st.error(erro)
                elif df_resultado is not None and not df_resultado.empty:
                    st.dataframe(
                        df_resultado,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Probabilidade de Vitória (%)": st.column_config.NumberColumn(
                                "Prob. Vitória (%)",
                                format="%.1f"
                            ),
                            "Gols Sofridos (Média)": st.column_config.NumberColumn(
                                "Gols Sofridos",
                                format="%.2f"
                            ),
                            "SG's Conquistados (%)": st.column_config.NumberColumn(
                                "SG's Conq. (%)",
                                format="%.1f"
                            ),
                            "Gols Marcados - Adversário (Média)": st.column_config.NumberColumn(
                                "Gols Adv. (Média)",
                                format="%.2f"
                            ),
                            "SG's Cedidos - Adversário (%)": st.column_config.NumberColumn(
                                "SG's Ced. Adv. (%)",
                                format="%.1f"
                            ),
                        }
                    )
                else:
                    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    # ===== ANÁLISE DE GOLEIROS =====
    with sub_tab2:
        st.subheader("Análise de Goleiros")
        st.markdown("""
            Estatísticas detalhadas dos goleiros incluindo:
            - Médias de pontuação
            - Probabilidade de Clean Sheet
            - Defesas por 90 minutos
            - Probabilidade de vitória do time
        """)
        
        if st.button("Gerar Análise de Goleiros", key="btn_goleiros"):
            with st.spinner("Calculando estatísticas dos goleiros..."):
                df_resultado, erro = analise_goleiros(ano=ano_selecionado, clubes_filtro=clubes_filtro)
                
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
    
    # ===== ANÁLISE DE ATACANTES =====
    with sub_tab3:
        st.subheader("Análise de Atacantes")
        st.markdown("""
            Estatísticas detalhadas dos atacantes incluindo:
            - Médias de pontuação
            - Expected Goals (XG) e Expected Assists (XA) por 90 min
            - Probabilidade de ataque
            - Desarmes cedidos
        """)
        st.info("ℹ️ Nota: XG e XA são aproximações baseadas em gols, assistências e finalizações.")
        
        if st.button("Gerar Análise de Atacantes", key="btn_atacantes"):
            with st.spinner("Calculando estatísticas dos atacantes..."):
                df_resultado, erro = analise_atacantes(ano=ano_selecionado, clubes_filtro=clubes_filtro)
                
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
    
    # ===== ANÁLISE DE RECORRÊNCIA =====
    with sub_tab4:
        st.subheader("Análise de Recorrência")
        st.markdown("""
            Análise de recorrência e consistência dos jogadores:
            - Média nos últimos 3 e 5 jogos
            - Percentual de jogos disputados
            - Frequência de participação
        """)
        
        # Filtro adicional de posição para recorrência
        posicao_filtro = st.selectbox(
            "Filtrar por Posição (opcional)",
            options=[None, 1, 2, 3, 4, 5, 6],
            format_func=lambda x: {
                None: "Todas",
                1: "Goleiro",
                2: "Lateral",
                3: "Zagueiro",
                4: "Meia",
                5: "Atacante",
                6: "Técnico"
            }.get(x, "Todas"),
            help="Filtre por posição específica"
        )
        
        if st.button("Gerar Análise de Recorrência", key="btn_recorrencia"):
            with st.spinner("Calculando análise de recorrência..."):
                df_resultado, erro = analise_recorrencia(
                    ano=ano_selecionado, 
                    clubes_filtro=clubes_filtro,
                    posicao_filtro=posicao_filtro
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
    
    # ===== ANÁLISE DE PARTICIPAÇÕES =====
    with sub_tab5:
        st.subheader("Análise de Participações - Estilo BIA Score")
        st.markdown("""
            Análise detalhada de participações dos jogadores incluindo:
            - Jogos disputados, Média e Média Básica
            - Expected Goals (XG) e Expected Assists (XA) por jogo
            - Gols, Assistências e G + A
            - Escanteios por jogo (quando disponível)
        """)
        st.info("ℹ️ Nota: XG e XA são aproximações baseadas em gols, assistências e finalizações. Escanteios não estão disponíveis no Cartola FC.")
        
        # Filtros adicionais para participações
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            posicao_filtro_part = st.selectbox(
                "Filtrar por Posição (opcional)",
                options=[None, 1, 2, 3, 4, 5, 6],
                format_func=lambda x: {
                    None: "Todas",
                    1: "Goleiro",
                    2: "Lateral",
                    3: "Zagueiro",
                    4: "Meia",
                    5: "Atacante",
                    6: "Técnico"
                }.get(x, "Todas"),
                help="Filtre por posição específica",
                key="pos_filtro_part"
            )
        
        with col_filtro2:
            status_opcoes = ["Provável", "Dúvida", "Suspenso", "Contundido", "Nulo"]
            status_selecionados = st.multiselect(
                "Filtrar por Status (opcional)",
                options=status_opcoes,
                default=[],
                help="Deixe vazio para mostrar todos os status",
                key="status_filtro_part"
            )
            status_filtro = status_selecionados if status_selecionados else None
        
        with col_filtro3:
            min_jogos = st.slider(
                "Jogos ≥",
                min_value=0,
                max_value=50,
                value=5,
                help="Filtra jogadores com mínimo de jogos disputados",
                key="min_jogos_part"
            )
        
        # Busca por nome
        busca_nome = st.text_input(
            "Buscar por nome...",
            value="",
            help="Digite o nome do jogador para filtrar",
            key="busca_nome_part"
        )
        
        if st.button("Gerar Análise de Participações Detalhada", key="btn_participacoes"):
            with st.spinner("Calculando análise de participações detalhada..."):
                df_resultado, erro = analise_participacoes_detalhada(
                    ano=ano_selecionado, 
                    clubes_filtro=clubes_filtro,
                    posicao_filtro=posicao_filtro_part,
                    status_filtro=status_filtro,
                    min_jogos=min_jogos
                )
                
                if erro:
                    st.error(erro)
                elif df_resultado is not None and not df_resultado.empty:
                    # Aplica filtro de busca por nome se especificado
                    if busca_nome:
                        mask_nome = df_resultado['Nome'].str.contains(busca_nome, case=False, na=False)
                        df_resultado = df_resultado[mask_nome].copy()
                    
                    if not df_resultado.empty:
                        st.dataframe(
                            df_resultado,
                            use_container_width=True,
                            hide_index=True,
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
                    else:
                        st.warning("Nenhum jogador encontrado com o nome especificado.")
                else:
                    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    # ===== ANÁLISE COMBINADA CARTOLA + FBREF =====
    with sub_tab6:
        st.subheader("Análise Combinada: Cartola FC + FBref")
        st.markdown("""
            Esta análise combina dados do Cartola FC com estatísticas avançadas do FBref:
            - **JOGOS, MÉDIA, M. BÁSICA**: Dados do Cartola FC
            - **XA/JOGO, XG/JOGO**: Expected Assists e Expected Goals do FBref
            - **ASSISTÊNCIAS, GOLS, G + A**: Estatísticas reais do FBref
            - **ESCANTEIOS/JOGO**: Aproximação baseada em scouts do Cartola
            
            Os dados são combinados através de matching inteligente por nome e clube.
        """)
        
        # Filtros específicos para esta análise
        col1, col2, col3 = st.columns(3)
        
        with col1:
            posicao_filtro_combinada = st.selectbox(
                "Posição",
                options=['Todos', 'GOL', 'LAT', 'ZAG', 'MEI', 'ATA'],
                index=0,
                key='pos_combinada'
            )
            posicao_filtro_combinada = None if posicao_filtro_combinada == 'Todos' else posicao_filtro_combinada
        
        with col2:
            min_jogos_combinada = st.slider(
                "Jogos ≥",
                min_value=0,
                max_value=50,
                value=5,
                key='min_jogos_combinada'
            )
        
        with col3:
            busca_nome_combinada = st.text_input(
                "Buscar por nome...",
                key='busca_nome_combinada'
            )
        
        if st.button("Gerar Análise Combinada", key="btn_combinada"):
            with st.spinner("Combinando dados do Cartola e FBref..."):
                df_resultado, erro = analise_combinada_cartola_fbref(
                    ano=ano_selecionado,
                    clubes_filtro=clubes_filtro,
                    posicao_filtro=posicao_filtro_combinada,
                    status_filtro=None,
                    min_jogos=min_jogos_combinada
                )
                
                if erro:
                    st.error(erro)
                elif df_resultado is not None and not df_resultado.empty:
                    # Aplica filtro de busca por nome se especificado
                    if busca_nome_combinada:
                        mask_nome = df_resultado['NOME'].str.contains(busca_nome_combinada, case=False, na=False)
                        df_resultado = df_resultado[mask_nome].copy()
                    
                    if not df_resultado.empty:
                        st.info(f"📊 **{len(df_resultado)} jogadores** encontrados com dados combinados.")
                        
                        st.dataframe(
                            df_resultado,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "CLUBE": st.column_config.TextColumn("CLUBE"),
                                "POS": st.column_config.TextColumn("POS"),
                                "NOME": st.column_config.TextColumn("NOME"),
                                "JOGOS": st.column_config.NumberColumn("JOGOS", format="%d"),
                                "MÉDIA": st.column_config.NumberColumn("MÉDIA", format="%.2f"),
                                "M. BÁSICA": st.column_config.NumberColumn("M. BÁSICA", format="%.2f"),
                                "ESCANTEIOS/JOGO": st.column_config.NumberColumn("ESCANTEIOS/JOGO", format="%.2f"),
                                "XA/JOGO": st.column_config.NumberColumn("XA/JOGO", format="%.3f"),
                                "XG/JOGO": st.column_config.NumberColumn("XG/JOGO", format="%.3f"),
                                "ASSISTÊNCIAS": st.column_config.NumberColumn("ASSISTÊNCIAS", format="%d"),
                                "GOLS": st.column_config.NumberColumn("GOLS", format="%d"),
                                "G + A": st.column_config.NumberColumn("G + A", format="%d"),
                            }
                        )
                    else:
                        st.warning("Nenhum jogador encontrado com o nome especificado.")
                else:
                    st.warning("Nenhum dado encontrado para os filtros selecionados.")
