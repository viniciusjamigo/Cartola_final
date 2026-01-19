# 📊 Como o Modelo Está Sendo Treinado Atualmente

## 🎯 Visão Geral

O sistema utiliza **modelos especialistas por posição** treinados com **XGBoost Regressor**. Cada posição (Goleiro, Defensor, Meia, Atacante, Técnico) tem seu próprio modelo treinado separadamente.

---

## 📁 Arquivos Envolvidos

- **`cartola_project/utils/modelagem.py`**: Contém toda a lógica de treinamento
- **`retreinar_modelos.py`**: Script para executar o retreinamento
- **Dados de entrada**: `data/historico_jogadores.csv` (dados históricos desde 2022)

---

## 🔄 Processo de Treinamento

### **1. Carregamento e Filtragem dos Dados**

```250:373:cartola_project/utils/modelagem.py
def treinar_modelo_especifico(df_treino, nome_modelo, posicoes_nome, model_prefix='novo_', use_new_features=True):
    
    # ... código de treinamento ...
    
def treinar_modelo(ano_limite=None, rodada_limite=None):
    try:
        if not os.path.exists(HISTORICAL_DATA_PATH):
            print(f"Arquivo '{HISTORICAL_DATA_PATH}' não encontrado.")
            return

        print("Carregando dados históricos...")
        df = pd.read_csv(HISTORICAL_DATA_PATH)
        
        # Filtra para usar apenas dados a partir de 2022
        print(f"Dados históricos totais: {len(df)}")
        
        # --- FILTRO DE ANO E RODADA (CONTROLE DO USUÁRIO) ---
        if ano_limite and rodada_limite:
            print(f"Aplicando limite de treino: Até Rodada {rodada_limite} de {ano_limite}")
            # Lógica: Pega tudo antes do ano limite, OU do ano limite mas até a rodada especificada
            mask_limite = (df['ano'] < ano_limite) | ((df['ano'] == ano_limite) & (df['rodada'] <= rodada_limite))
            df = df[mask_limite].copy()
        
        df = df[df['ano'] >= 2022].copy()
        print(f"Dados após filtro de ano (>= 2022) e corte ({ano_limite if ano_limite else 'N/A'}): {len(df)}")
```

**Características:**
- Usa dados históricos desde **2022**
- Permite filtrar até uma rodada específica (útil para evitar "vazamento de dados")
- Remove registros com pontuação zero (jogadores que não jogaram)

---

### **2. Engenharia de Features**

O sistema cria várias features preditivas:

#### **A. Features Temporais (Pontuação)**
- `pontos_last`: Pontuação do jogo anterior
- `media_3_rodadas`: Média móvel exponencial (EMA) das últimas 3 rodadas
- `media_temporada`: Média acumulada da temporada

#### **B. Features de Mando de Campo e Adversário**
- `fl_mandante`: Flag indicando se o time joga em casa (1) ou fora (0)
- `adversario_id`: ID do time adversário
- `adv_media_gols_feitos`: Média de gols feitos pelo adversário
- `adv_media_gols_sofridos`: Média de gols sofridos pelo adversário

#### **C. Features de Scouts (Estatísticas Detalhadas)**
Para cada scout relevante (G, A, DS, SG, FS, FF, FD, FT, I, PE, etc.):
- `media_{scout}_last3`: Média EMA dos últimos 3 jogos
- `media_{scout}_season`: Média acumulada da temporada

**Exemplo:** `media_G_last3`, `media_A_season`, `media_DS_last3`, etc.

#### **D. Features Básicas**
- `preco_num`: Preço do jogador
- `posicao_id`: ID da posição (1=Goleiro, 2=Lateral, 3=Zagueiro, 4=Meia, 5=Atacante, 6=Técnico)

---

### **3. Seleção de Features por Posição**

Cada posição usa apenas os scouts relevantes:

```267:298:cartola_project/utils/modelagem.py
    # --- FEATURE SELECTION INTELIGENTE POR POSIÇÃO ---
    # Define quais scouts fazem sentido para cada grupo para evitar ruído
    scouts_relevantes_map = {
        'gol': ['DE', 'GS', 'SG', 'DP', 'PS'],
        'def': ['SG', 'DS', 'FS', 'G', 'A', 'CA', 'CV', 'GC'], # Zagueiros/Laterais
        'mei': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'ata': ['G', 'A', 'DS', 'FS', 'FF', 'FD', 'FT', 'I', 'PP', 'CA'],
        'tec': [] # Técnicos não têm scouts individuais
    }
    
    # Seleciona a lista de scouts alvo para esta posição
    scouts_do_grupo = scouts_relevantes_map.get(posicoes_nome, [])
    
    features_scouts = []
    for col in df_treino.columns:
        # Verifica se é uma coluna de média de scout
        if 'media_' in col and ('_last3' in col or '_season' in col) and col not in features_base:
            # Extrai o nome do scout da coluna (ex: media_DE_last3 -> DE)
            # Padrão esperado: media_NOME_last3 ou media_NOME_season
            partes = col.split('_')
            if len(partes) >= 3:
                nome_scout = partes[1]
                
                # Se for técnico, não adiciona nada. Se for outro, verifica a lista.
                # Se a lista estiver vazia (caso não mapeado), adiciona tudo por segurança.
                if posicoes_nome == 'tec':
                    continue 
                elif scouts_do_grupo and nome_scout in scouts_do_grupo:
                    features_scouts.append(col)
                elif not scouts_do_grupo:
                    features_scouts.append(col)
```

**Por exemplo:**
- **Goleiros** usam: DE (Defesas), GS (Gols Sofridos), SG (Sem Gols), DP (Defesas de Pênalti), PS (Pênaltis Sofridos)
- **Atacantes** usam: G (Gols), A (Assistências), FF (Finalizações), FD (Finalizações Defendidas), etc.

---

### **4. Configuração do Modelo XGBoost**

```317:328:cartola_project/utils/modelagem.py
    # Configuração para buscar a MÉDIA (reg:squarederror) e não a mediana (reg:absoluteerror)
    # Isso ajuda a aumentar as previsões em distribuições "skewed" como a do Cartola (muitos pontos baixos, poucos altos)
    modelo = XGBRegressor(
        n_estimators=1000, 
        learning_rate=0.02, 
        max_depth=6, 
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        objective='reg:squarederror' # MUDANÇA CRÍTICA: Foca na Média (valores maiores)
    )
```

**Parâmetros:**
- **`n_estimators=1000`**: 1000 árvores (boosting rounds)
- **`learning_rate=0.02`**: Taxa de aprendizado baixa (aprendizado mais conservador)
- **`max_depth=6`**: Profundidade máxima das árvores
- **`subsample=0.85`**: Usa 85% dos dados em cada árvore (reduz overfitting)
- **`colsample_bytree=0.85`**: Usa 85% das features em cada árvore
- **`objective='reg:squarederror'`**: Minimiza erro quadrático médio (foca na média, não na mediana)

---

### **5. Divisão Treino/Teste**

```315:330:cartola_project/utils/modelagem.py
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Configuração para buscar a MÉDIA (reg:squarederror) e não a mediana (reg:absoluteerror)
    # Isso ajuda a aumentar as previsões em distribuições "skewed" como a do Cartola (muitos pontos baixos, poucos altos)
    modelo = XGBRegressor(
        n_estimators=1000, 
        learning_rate=0.02, 
        max_depth=6, 
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        objective='reg:squarederror' # MUDANÇA CRÍTICA: Foca na Média (valores maiores)
    )
    
    modelo.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
```

- **80%** dos dados para treino
- **20%** dos dados para teste
- Usa `eval_set` para monitorar performance durante o treinamento

---

### **6. Treinamento de Modelos Duplos**

O sistema treina **dois modelos** para cada posição:

```479:491:cartola_project/utils/modelagem.py
            # Treina Modelo Novo (com todas as features)
            modelo_novo, rmse_novo = treinar_modelo_especifico(
                df_grupo, nome_arquivo, nome_grupo, model_prefix='novo_', use_new_features=True
            )
            if modelo_novo:
                metricas[f"novo_{nome_grupo}"] = float(rmse_novo)

            # Treina Modelo Legado (sem as features de mando/adversário)
            modelo_legado, rmse_legado = treinar_modelo_especifico(
                df_grupo, nome_arquivo, nome_grupo, model_prefix='legado_', use_new_features=False
            )
            if modelo_legado:
                metricas[f"legado_{nome_grupo}"] = float(rmse_legado)
```

**Modelos:**
1. **`novo_`**: Usa todas as features (incluindo mando de campo e adversário)
2. **`legado_`**: Usa apenas features básicas (sem mando/adversário)

**Por quê?**
- Permite comparar performance entre modelos antigos e novos
- Facilita rollback se o modelo novo não performar bem

---

### **7. Avaliação e Salvamento**

```332:351:cartola_project/utils/modelagem.py
    previsoes = modelo.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, previsoes))
    mae = mean_absolute_error(y_test, previsoes)
    
    print(f"  > [{posicoes_nome} - {model_prefix.strip('_')}] RMSE: {rmse:.4f} | MAE: {mae:.4f}")
    
    caminho_modelo = os.path.join(MODEL_DIR, f"{model_prefix}{nome_modelo}")
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    # Remove modelo antigo para garantir atualização
    if os.path.exists(caminho_modelo):
        try:
            os.remove(caminho_modelo)
        except OSError:
            pass

    joblib.dump(modelo, caminho_modelo)
    
    return modelo, rmse
```

**Métricas calculadas:**
- **RMSE** (Root Mean Squared Error): Erro quadrático médio
- **MAE** (Mean Absolute Error): Erro absoluto médio

**Salvamento:**
- Modelos salvos em `data/modelos/`
- Nomes: `novo_modelo_gol.pkl`, `legado_modelo_gol.pkl`, etc.
- Métricas salvas em `data/modelos/metricas.json`

---

## 📊 Estrutura dos Modelos

### **Modelos por Posição:**

| Posição | IDs | Arquivo | Scouts Relevantes |
|---------|-----|---------|-------------------|
| Goleiro | [1] | `modelo_gol.pkl` | DE, GS, SG, DP, PS |
| Defensor | [2, 3] | `modelo_def.pkl` | SG, DS, FS, G, A, CA, CV, GC |
| Meia | [4] | `modelo_mei.pkl` | G, A, DS, FS, FF, FD, FT, I, PP, CA |
| Atacante | [5] | `modelo_ata.pkl` | G, A, DS, FS, FF, FD, FT, I, PP, CA |
| Técnico | [6] | `modelo_tec.pkl` | Nenhum scout |

---

## 🎯 Features Utilizadas (Modelo Novo)

### **Features Base (Todas as Posições):**
- `preco_num`
- `media_temporada`
- `media_3_rodadas`
- `posicao_id`
- `fl_mandante` ⭐ (Nova)
- `adv_media_gols_feitos` ⭐ (Nova)
- `adv_media_gols_sofridos` ⭐ (Nova)

### **Features de Scouts (Dependente da Posição):**
- `media_{scout}_last3` (para cada scout relevante)
- `media_{scout}_season` (para cada scout relevante)

**Total:** ~15-25 features por modelo (dependendo da posição)

---

## 🔄 Como Executar o Treinamento

```bash
python retreinar_modelos.py
```

Ou diretamente:

```python
from cartola_project.utils.modelagem import treinar_modelo

# Treinar com todos os dados disponíveis
treinar_modelo()

# Treinar até uma rodada específica (evita vazamento de dados)
treinar_modelo(ano_limite=2025, rodada_limite=10)
```

---

## 📈 Pós-Previsão: Bônus Tático

Após a previsão base do modelo, o sistema aplica um **multiplicador tático** baseado em:

1. **Probabilidade de Vitória** (das Odds)
2. **Mando de Campo**
3. **Força do Adversário** (média de gols feitos/sofridos)

```504:575:cartola_project/utils/modelagem.py
def aplicar_bonus_tatico(row):
    """Aplica multiplicadores táticos pós-previsão."""
    previsao = row.get('pontuacao_prevista_base', 0)
    posicao = row['posicao_id']
    
    fator_casa = row.get('fator_casa', 0)
    if fator_casa == 0 and 'fl_mandante' in row:
        # Fallback para fl_mandante se fator_casa não existir (Backtest compatibility)
        fator_casa = 1 if row['fl_mandante'] == 1 else -1

    adv_def = row.get('adversario_forca_def', 3) # Escala 1-5
    adv_of = row.get('adversario_forca_of', 3) # Escala 1-5
    
    # NOVOS DADOS (Floats diretos de estatisticas) - Preferenciais se existirem
    media_gols_sofridos_adv = row.get('adv_media_gols_sofridos', None)
    media_gols_feitos_adv = row.get('adv_media_gols_feitos', None)
    
    prob_vitoria = row.get('prob_vitoria', 0.33) # Probabilidade de vitória baseada nas Odds
    
    multiplicador = 1.0
    
    # --- FATOR ODDS (Probabilidade Real) ---
    # Se probabilidade > 50%, ganha bônus proporcional (Mais agressivo)
    # Se probabilidade < 20%, perde pontos
    if prob_vitoria > 0.5:
        multiplicador += (prob_vitoria - 0.5) * 0.6 
    elif prob_vitoria < 0.2:
        multiplicador -= 0.10 # Azarão perde 10%
    
    # Mando de Campo (Já coberto parcialmente pelas Odds, mas reforçamos pelo fator psicológico/arbitragem)
    if fator_casa == 1: multiplicador += 0.08 
    elif fator_casa == -1: multiplicador -= 0.03 
        
    # Defesa (GOL/LAT/ZAG)
    if posicao in [1, 2, 3]: 
        # Usa média de gols feitos pelo adversário se disponível (mais preciso)
        if media_gols_feitos_adv is not None:
             if media_gols_feitos_adv <= 0.8: multiplicador += 0.20 # Adversário faz poucos gols
             elif media_gols_feitos_adv >= 1.5: multiplicador -= 0.15 # Adversário faz muitos gols
        else:
            # Fallback para escala 1-5
            if adv_of <= 2: multiplicador += 0.20
            elif adv_of >= 4: multiplicador -= 0.15
            
    # Ataque (MEI/ATA)
    if posicao in [4, 5]:
        # Usa média de gols sofridos pelo adversário se disponível (mais preciso)
        if media_gols_sofridos_adv is not None:
            if media_gols_sofridos_adv >= 1.5: multiplicador += 0.20 # Adversário toma muitos gols (Bom pra mim)
            elif media_gols_sofridos_adv <= 0.8: multiplicador -= 0.15 # Adversário toma poucos gols (Ruim pra mim)
        else:
            # Fallback para escala 1-5 (Lógica Invertida: 1=Defesa Fraca/Toma Gols? Não, geralmente 1=Forte)
            # Se 1=Forte Defesa -> Ruim para Ataque.
            # Se 5=Fraca Defesa -> Bom para Ataque.
            # O código original dizia: if adv_def <= 2: +0.20.
            # Isso implica que 1-2 é DEFESA FRACA no preprocessamento antigo. Assumindo consistência.
            if adv_def <= 2: multiplicador += 0.20 
            elif adv_def >= 4: multiplicador -= 0.15
            
    # Técnico
    if posicao == 6 and fator_casa == 1:
        # Simples bônus se jogar em casa e adversário não for pedreira
        eh_jogo_facil = False
        if media_gols_sofridos_adv is not None:
            if media_gols_sofridos_adv >= 1.2: eh_jogo_facil = True
        elif adv_def <= 2:
            eh_jogo_facil = True
            
        if eh_jogo_facil:
            multiplicador += 0.15

    return previsao * multiplicador
```

---

## 🎓 Resumo do Fluxo

1. **Carrega** dados históricos desde 2022
2. **Filtra** dados válidos (pontuação > 0, posição definida)
3. **Cria** features temporais, de scouts, mando de campo e adversário
4. **Separa** por posição (Goleiro, Defensor, Meia, Atacante, Técnico)
5. **Treina** 2 modelos por posição (novo e legado)
6. **Avalia** com RMSE e MAE
7. **Salva** modelos em `.pkl` e métricas em `.json`
8. **Aplica** bônus tático na previsão final

---

## 🔍 Pontos Importantes

- ✅ **Modelos especialistas**: Cada posição tem seu próprio modelo
- ✅ **Feature selection**: Apenas scouts relevantes por posição
- ✅ **Validação**: Divisão treino/teste 80/20
- ✅ **Regularização**: Subsample e colsample para evitar overfitting
- ✅ **Duplo modelo**: Novo (com features avançadas) e Legado (básico)
- ✅ **Bônus pós-previsão**: Ajuste tático baseado em odds e adversário

