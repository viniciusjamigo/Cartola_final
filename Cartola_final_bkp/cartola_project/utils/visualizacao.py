import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as path_effects
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from io import BytesIO
from PIL import Image
import json
import os

# Cache simples de imagens em memória para não baixar toda hora na mesma sessão
IMAGE_CACHE = {}

def carregar_imagem_escudo(url):
    """Baixa e processa a imagem do escudo, com cache."""
    if not url: return None
    if url in IMAGE_CACHE: return IMAGE_CACHE[url]
    
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            IMAGE_CACHE[url] = img
            return img
    except Exception as e:
        # print(f"Erro ao baixar imagem {url}: {e}")
        pass
    return None

def get_escudo_url(clube_nome, clubes_data):
    """Busca a URL do escudo no dicionário de clubes."""
    # O DataFrame tem 'clube' como nome fantasia (ex: "Flamengo")
    # O JSON tem chaves como ID, e valores com 'nome_fantasia'.
    # Precisamos fazer o match reverso ou passar o ID do clube no time_df
    
    # Otimização: Se time_df tiver clube_id, melhor.
    # Se não, tentamos pelo nome.
    
    if clubes_data is None: return None
    
    for _, data in clubes_data.items():
        if data.get('nome_fantasia') == clube_nome or data.get('nome') == clube_nome:
            return data.get('escudos', {}).get('60x60')
    return None

def desenhar_campo(time_df, formacao_str="4-3-3"):
    """
    Gera uma visualização de campo de futebol estilo Cartola FC.
    """
    # Tenta carregar o JSON de clubes para pegar escudos
    clubes_data = None
    try:
        caminho_json = os.path.join(os.path.dirname(__file__), '..', 'data', 'clubes.json')
        with open(caminho_json, 'r', encoding='utf8') as f:
            clubes_data = json.load(f)
    except:
        pass

    # Configuração do campo (Verde mais vibrante estilo app)
    fig, ax = plt.subplots(figsize=(10, 13)) # Mais alto para caber técnico
    cor_gramado = '#28a745' # Verde Material Design
    fig.patch.set_facecolor(cor_gramado)
    ax.set_facecolor(cor_gramado)
    
    # --- Desenhar Linhas do Campo ---
    # Linhas brancas semitransparentes
    linha_style = {'color': 'white', 'linewidth': 2, 'alpha': 0.6}
    
    # Borda
    ax.add_patch(patches.Rectangle((0, 0), 100, 120, fill=False, **linha_style))
    
    # Meio campo
    ax.plot([0, 100], [60, 60], **linha_style)
    ax.add_patch(patches.Circle((50, 60), 10, fill=False, **linha_style))
    
    # Grande Área (Baixo/Gol)
    ax.add_patch(patches.Rectangle((20, 0), 60, 18, fill=False, **linha_style))
    # Pequena Área (Baixo)
    ax.add_patch(patches.Rectangle((36, 0), 28, 6, fill=False, **linha_style))
    # Lua da grande área
    arc_b = patches.Arc((50, 18), 20, 10, theta1=0, theta2=180, **linha_style)
    ax.add_patch(arc_b)

    # Grande Área (Cima/Ataque)
    ax.add_patch(patches.Rectangle((20, 102), 60, 18, fill=False, **linha_style))
    # Pequena Área (Cima)
    ax.add_patch(patches.Rectangle((36, 114), 28, 6, fill=False, **linha_style))
    # Lua da grande área
    arc_t = patches.Arc((50, 102), 20, 10, theta1=180, theta2=0, **linha_style)
    ax.add_patch(arc_t)
    
    # Escanteios
    ax.add_patch(patches.Arc((0, 0), 4, 4, theta1=0, theta2=90, **linha_style))
    ax.add_patch(patches.Arc((100, 0), 4, 4, theta1=90, theta2=180, **linha_style))
    ax.add_patch(patches.Arc((100, 120), 4, 4, theta1=180, theta2=270, **linha_style))
    ax.add_patch(patches.Arc((0, 120), 4, 4, theta1=270, theta2=360, **linha_style))

    # --- Coordenadas Fixas para Formações Comuns ---
    # Ajustadas para parecer mais "espalhado"
    coords_map = {
        "4-3-3": {
            "Goleiro": [(50, 8)],
            "Lateral": [(15, 40), (85, 40)],
            "Zagueiro": [(38, 25), (62, 25)],
            "Meia": [(30, 65), (50, 75), (70, 65)], # Triângulo invertido
            "Atacante": [(20, 100), (50, 110), (80, 100)],
            "Técnico": [(50, -10)]
        },
        "4-4-2": {
            "Goleiro": [(50, 8)],
            "Lateral": [(15, 40), (85, 40)],
            "Zagueiro": [(38, 25), (62, 25)],
            "Meia": [(20, 65), (40, 75), (60, 75), (80, 65)], # Linha ou Losango
            "Atacante": [(35, 105), (65, 105)],
            "Técnico": [(50, -10)]
        },
        "3-5-2": {
            "Goleiro": [(50, 8)],
            "Zagueiro": [(30, 25), (50, 25), (70, 25)],
            "Meia": [(15, 60), (35, 70), (50, 55), (65, 70), (85, 60)], # Alas abertos
            "Atacante": [(35, 105), (65, 105)],
            "Lateral": [], # 3-5-2 não tem lateral "oficial" no cartola as vezes, vira meia
            "Técnico": [(50, -10)]
        }
    }
    
    esquema = coords_map.get(formacao_str, coords_map["4-3-3"]) # Fallback
    
    # Se esquema não tiver lat (ex 3-4-3), lida com fallback genérico
    
    # Helpers de texto
    effect = path_effects.withStroke(linewidth=2.5, foreground="black")
    
    # Agrupa jogadores por posição
    # Copia para não alterar original
    df_plot = time_df.copy()
    
    # Ordem de plotagem: Gol, Zag, Lat, Mei, Ata, Tec
    pos_order = ["Goleiro", "Zagueiro", "Lateral", "Meia", "Atacante", "Técnico"]
    
    for pos in pos_order:
        jogadores_pos = df_plot[df_plot['posicao'] == pos]
        pontos_disp = esquema.get(pos, [])
        
        # Fallback: Se faltar coordenada (ex: 3-4-3 não mapeado), gera linear
        if len(pontos_disp) < len(jogadores_pos):
            # Gera linha reta genérica
            y_base = 50
            if pos == "Zagueiro": y_base = 25
            elif pos == "Meia": y_base = 65
            elif pos == "Atacante": y_base = 100
            
            qtd = len(jogadores_pos)
            pontos_disp = []
            for i in range(qtd):
                pontos_disp.append( (100 * (i+1)/(qtd+1), y_base) )

        for i, (_, jogador) in enumerate(jogadores_pos.iterrows()):
            if i >= len(pontos_disp): break # Segurança
            
            x, y = pontos_disp[i]
            
            # 1. Círculo do Jogador (Fundo)
            # ax.add_patch(patches.Circle((x, y), 4.5, color='white', zorder=2))
            
            # 2. Imagem do Escudo (Camisa)
            url_escudo = get_escudo_url(jogador['clube'], clubes_data)
            img = carregar_imagem_escudo(url_escudo)
            
            if img:
                # Desenha Imagem
                imagebox = OffsetImage(img, zoom=0.6) # Zoom ajusta tamanho
                ab = AnnotationBbox(imagebox, (x, y), frameon=False, zorder=3)
                ax.add_artist(ab)
            else:
                # Fallback se não tiver imagem: Círculo Branco com borda cinza
                ax.add_patch(patches.Circle((x, y), 4, color='#f0f0f0', ec='#ccc', lw=1, zorder=2))
                # Sigla do clube?
                ax.text(x, y, jogador['clube'][:3].upper(), ha='center', va='center', fontsize=6, zorder=4)

            # 3. Indicador de Capitão
            if jogador.get('C') == '©️':
                # Círculo Laranja Pequeno
                ax.add_patch(patches.Circle((x + 3.5, y + 3.5), 1.8, color='#ff9800', zorder=5))
                ax.text(x + 3.5, y + 3.5, "C", color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=6)
                
            # 4. Etiqueta de Preço/Pontos (Badge)
            # Formato: [ C$ 10.50 ]
            val = jogador.get('preco_num', 0)
            label = f"C$ {val:.2f}"
            
            # Caixa branca arredondada
            bbox_props = dict(boxstyle="round,pad=0.2", fc="white", ec="#ccc", lw=0.5, alpha=0.9)
            ax.text(x, y + 5.5, label, ha="center", va="bottom", fontsize=7, color='#333', fontweight='bold', bbox=bbox_props, zorder=4)
            
            # 5. Nome do Jogador (Embaixo)
            nome_curto = jogador['nome'].split()[0]
            if len(nome_curto) > 10: nome_curto = nome_curto[:8] + "."
            
            ax.text(x, y - 5.5, nome_curto, fontsize=9, ha='center', va='top', 
                    color='white', fontweight='bold', path_effects=[effect], zorder=4)
            
            # 6. Previsão (Pequeno, em amarelo embaixo do nome)
            prev = jogador.get('pontuacao_prevista', 0)
            ax.text(x, y - 8.5, f"{prev:.1f} pts", fontsize=7, ha='center', va='top',
                   color='#ffeb3b', fontweight='bold', path_effects=[path_effects.withStroke(linewidth=1, foreground="black")], zorder=4)

    # Ajustes finais de visualização
    ax.set_xlim(0, 100)
    ax.set_ylim(-15, 125) # Margem para o técnico embaixo
    ax.axis('off')
    
    # Remove margens brancas extras do plot
    plt.tight_layout()
    
    return fig

def gerar_grafico_comparativo(df_usuario, df_historico_geral, orcamento=140):
    """
    Gera um gráfico comparando:
    1. Pontuação do Usuário (Real)
    2. Pontuação da IA (Simulada)
    3. Pontuação Máxima Possível (Time Perfeito)
    """
    from .otimizador import otimizar_escalacao
    import pandas as pd
    import numpy as np
    
    # Filtra histórico geral para o ano do usuário
    if 'ano' not in df_usuario.columns:
        return None
        
    ano_usuario = df_usuario['ano'].iloc[0]
    df_ano = df_historico_geral[df_historico_geral['ano'] == ano_usuario].copy()
    
    # Mapeamento de posições e clubes
    posicao_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Técnico"}
    if 'posicao_id' in df_ano.columns:
        df_ano['posicao'] = df_ano['posicao_id'].map(posicao_map)
    
    resultados = []
    
    # Para cada rodada que o usuário jogou
    for _, row in df_usuario.iterrows():
        rodada = row['rodada']
        pontos_usuario = row['pontuacao']
        
        # Dados daquela rodada
        df_r = df_ano[df_ano['rodada'] == rodada].copy()
        
        if df_r.empty: continue
        
        # --- 1. SIMULAÇÃO IA (O que o robô teria feito) ---
        # Usa média acumulada como proxy da previsão da IA na época
        if 'media_num' in df_r.columns:
            df_r['pontuacao_prevista'] = df_r['media_num']
        else:
            df_r['pontuacao_prevista'] = 0
            
        df_r['volatilidade'] = 0 
        
        try:
            # Otimiza IA
            time_ia = otimizar_escalacao(
                df_r, 'pontuacao_prevista', 'preco_num', orcamento, "4-3-3"
            )
            pontos_ia = time_ia['pontuacao'].sum() # Soma os pontos REAIS que o time da IA fez
            
            # Considera Capitão da IA
            if not time_ia.empty:
                 capitao_ia = time_ia.loc[time_ia['pontuacao_prevista'].idxmax()]
                 pontos_ia += capitao_ia['pontuacao'] 
            
        except:
            pontos_ia = 0

        # --- 2. SIMULAÇÃO MÁXIMA (Bola de Cristal) ---
        try:
            time_max = otimizar_escalacao(
                df_r, 
                coluna_pontos='pontuacao', # PREVÊ O FUTURO (USA O REAL)
                coluna_preco='preco_num', 
                orcamento_total=orcamento, 
                formacao_t_str="4-3-3"
            )
            pontos_max = time_max['pontuacao'].sum()
            
            # Capitão Perfeito
            linha = time_max[time_max['posicao'] != 'Técnico']
            if not linha.empty:
                pontos_max += linha['pontuacao'].max()
                
        except:
            pontos_max = 0
            
        resultados.append({
            'rodada': rodada,
            'Voce': pontos_usuario,
            'IA': pontos_ia,
            'Maximo': pontos_max
        })
        
    df_res = pd.DataFrame(resultados)
    if df_res.empty: return None
    
    df_res.set_index('rodada', inplace=True)
    return df_res
