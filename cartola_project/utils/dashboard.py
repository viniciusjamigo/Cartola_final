import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from utils.config import config

def render_dashboard():
    st.header("📊 Dashboard Analítico (2024-2026)")
    st.markdown("""
        Bem-vindo ao Dashboard Analítico. Aqui você pode explorar o desempenho histórico de jogadores, 
        posições e times para tomar decisões baseadas em dados.
    """)

    # --- Carregamento de Dados ---
    @st.cache_data
    def carregar_dados_dashboard():
        if os.path.exists(config.HISTORICAL_DATA_PATH):
            df = pd.read_csv(config.HISTORICAL_DATA_PATH, low_memory=False)
            # Mapeamento de Posições
            mapa_posicoes = {
                1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 
                4: "Meia", 5: "Atacante", 6: "Técnico"
            }
            # Garante que posicao_id seja numérico para o mapeamento
            df['posicao_id'] = pd.to_numeric(df['posicao_id'], errors='coerce')
            df['Posicao'] = df['posicao_id'].map(mapa_posicoes).fillna("Desconhecido")
            
            # Carregar nomes dos clubes
            try:
                with open(config.CLUBS_DATA_PATH, 'r', encoding='utf-8') as f:
                    clubes_json = json.load(f)
                mapa_clubes = {int(k): v['nome'] for k, v in clubes_json.items()}
                df['clube_id'] = pd.to_numeric(df['clube_id'], errors='coerce')
                df['Clube'] = df['clube_id'].map(mapa_clubes).fillna("Outros")
            except:
                df['Clube'] = df['clube_id'].astype(str)

            return df
        return pd.DataFrame()

    df_hist = carregar_dados_dashboard()

    if df_hist.empty:
        st.error("Dados históricos não encontrados.")
        return

    # --- Filtros no Topo ---
    col1, col2, col3, col4 = st.columns(4)
    
    anos_disponiveis = sorted(df_hist['ano'].unique().tolist(), reverse=True)
    anos_selecionados = col1.multiselect("Anos", options=anos_disponiveis, default=[2024, 2025])
    
    posicoes_disponiveis = sorted(df_hist['Posicao'].unique().tolist())
    posicoes_selecionadas = col2.multiselect("Posições", options=posicoes_disponiveis, default=posicoes_disponiveis)
    
    times_disponiveis = sorted(df_hist['Clube'].unique().tolist())
    times_selecionados = col3.multiselect("Times", options=times_disponiveis)

    rodadas_disponiveis = sorted(df_hist[df_hist['ano'].isin(anos_selecionados)]['rodada'].unique().tolist())
    rodadas_selecionadas = col4.multiselect("Rodadas", options=rodadas_disponiveis, help="Deixe vazio para ver todas as rodadas")

    # Aplicação dos Filtros
    mask = df_hist['ano'].isin(anos_selecionados) & df_hist['Posicao'].isin(posicoes_selecionadas)
    
    if times_selecionados:
        mask = mask & df_hist['Clube'].isin(times_selecionados)
    
    if rodadas_selecionadas:
        mask = mask & df_hist['rodada'].isin(rodadas_selecionadas)
    
    df_filtrado = df_hist[mask]

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # --- Seção 1: Visão Geral por Posição ---
    st.divider()
    st.subheader("💡 Desempenho por Posição")
    
    # Agregação por Posição
    agg_posicao = df_filtrado.groupby('Posicao').agg({
        'pontuacao': ['mean', 'max', 'std'],
        'atleta_id': 'count'
    }).reset_index()
    agg_posicao.columns = ['Posicao', 'Média Pontos', 'Pontuação Máxima', 'Consistência (Desvio)', 'Qtd Registros']
    
    col_a, col_b = st.columns([1, 1])
    
    fig_pos = px.bar(
        agg_posicao, 
        x='Posicao', 
        y='Média Pontos', 
        color='Posicao',
        title="Média de Pontuação por Posição",
        text_auto='.2f'
    )
    col_a.plotly_chart(fig_pos, use_container_width=True)
    
    fig_max = px.box(
        df_filtrado, 
        x='Posicao', 
        y='pontuacao', 
        color='Posicao',
        title="Distribuição de Pontos por Posição"
    )
    col_b.plotly_chart(fig_max, use_container_width=True)

    # --- Seção 2: Top Jogadores ---
    st.divider()
    st.subheader("🏆 Melhores Jogadores no Período")
    
    # Ajusta o critério de mínimo de jogos baseado na quantidade de rodadas selecionadas
    qtd_rodadas = len(rodadas_selecionadas) if rodadas_selecionadas else len(rodadas_disponiveis)
    min_jogos_default = min(5, qtd_rodadas) if qtd_rodadas > 0 else 1
    
    min_jogos = st.slider("Mínimo de Jogos disputados", 1, max(38, qtd_rodadas), int(min_jogos_default))
    
    agg_jogador = df_filtrado.groupby(['apelido', 'Clube', 'Posicao']).agg({
        'pontuacao': ['mean', 'count', 'sum'],
        'G': 'sum',
        'A': 'sum',
        'DS': 'sum'
    }).reset_index()
    agg_jogador.columns = ['Jogador', 'Clube', 'Posicao', 'Média', 'Jogos', 'Total Pontos', 'Gols', 'Assists', 'Desarmes']
    
    # Filtro de mínimo de jogos dinâmico
    agg_jogador = agg_jogador[agg_jogador['Jogos'] >= min_jogos].sort_values('Média', ascending=False)
    
    st.dataframe(
        agg_jogador.head(20),
        column_config={
            "Média": st.column_config.NumberColumn(format="%.2f"),
            "Total Pontos": st.column_config.NumberColumn(format="%.1f")
        },
        hide_index=True,
        width=1200
    )

    # --- Seção 3: Análise por Time ---
    st.divider()
    st.subheader("🏟️ Força dos Times (Média de Pontuação Cedida/Conquistada)")
    
    agg_time = df_filtrado.groupby('Clube').agg({
        'pontuacao': ['mean', 'sum'],
        'G': 'sum',
        'SG': 'sum'
    }).reset_index()
    agg_time.columns = ['Clube', 'Média Pontos Jogadores', 'Total Pontos', 'Total Gols', 'Total SG']
    
    fig_time = px.scatter(
        agg_time, 
        x='Média Pontos Jogadores', 
        y='Total Gols',
        size='Total SG', 
        color='Clube',
        hover_name='Clube',
        title="Relação: Pontuação Média vs Gols Feitos (Tamanho = Saldo de Gols/SG)"
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --- Seção 4: Evolução Temporal ---
    st.divider()
    st.subheader("📅 Evolução da Pontuação Média (Rodada a Rodada)")
    
    agg_tempo = df_filtrado.groupby(['ano', 'rodada']).agg({'pontuacao': 'mean'}).reset_index()
    agg_tempo['Ano_Rodada'] = agg_tempo['ano'].astype(str) + " - R" + agg_tempo['rodada'].astype(str)
    
    fig_evolucao = px.line(
        agg_tempo, 
        x='rodada', 
        y='pontuacao', 
        color='ano',
        title="Média de Pontos por Rodada ao longo dos Anos",
        markers=True
    )
    st.plotly_chart(fig_evolucao, use_container_width=True)
