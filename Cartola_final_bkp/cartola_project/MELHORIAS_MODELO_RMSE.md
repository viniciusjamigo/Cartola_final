# 🎯 Melhorias do Modelo para Reduzir RMSE

## Análise do Modelo Atual

### Features Atuais Utilizadas:
1. **Básicas:** `preco_num`, `media_temporada`, `media_3_rodadas`, `posicao_id`
2. **Contextuais:** `fl_mandante`, `adv_media_gols_feitos`, `adv_media_gols_sofridos`
3. **Scouts:** Médias de scouts individuais (G, A, DS, SG, etc.) - `media_{scout}_last3` e `media_{scout}_season`
4. **Bônus Pós-Predição:** Aplicado via `aplicar_bonus_tatico()` usando odds e força do adversário

### Pontos Fortes:
- ✅ Modelos especializados por posição (gol, def, mei, ata, tec)
- ✅ Uso de EMA (Exponential Moving Average) para capturar momentum
- ✅ Features de scouts individuais
- ✅ Consideração de mando de campo e força do adversário

### Pontos Fracos Identificados:
- ❌ Features de contexto do jogo limitadas
- ❌ Falta de features de tendência (aceleração, não só velocidade)
- ❌ Tratamento de outliers/extremos pode ser melhorado
- ❌ Features de interação limitadas
- ❌ Não considera contexto temporal (fase do campeonato, importância do jogo)
- ❌ Não usa histórico head-to-head
- ❌ Features de consistência vs explosividade não exploradas
- ❌ Uso limitado das odds (só probabilidade de vitória)

---

## 🚀 Melhorias por Impacto Esperado no RMSE

### 🔴 **IMPACTO MUITO ALTO** (Redução esperada: 10-20% no RMSE)

#### 1. **Features de Tendência e Aceleração (Momentum Avançado)**
**Problema:** O modelo usa apenas média móvel, mas não captura se o jogador está melhorando ou piorando.

**Solução:**
```python
# Adicionar em preparar_features_historicas()

# 1. Tendência (Slope) - Se está subindo ou descendo
df['pontos_tendencia'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).apply(
        lambda y: np.polyfit(range(len(y)), y, 1)[0] if len(y) >= 2 else 0
    )
)

# 2. Aceleração (Mudança na tendência)
df['pontos_aceleracao'] = df.groupby(['ano', 'atleta_id'])['pontos_tendencia'].diff()

# 3. Volatilidade Recente vs Histórica (Consistência)
df['volatilidade_recente'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).std()
)
df['volatilidade_historica'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.expanding().std()
)
df['ratio_volatilidade'] = df['volatilidade_recente'] / (df['volatilidade_historica'] + 0.1)

# 4. Sequência de Jogos (Momentum de Confiança)
df['sequencia_positiva'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: (x >= x.rolling(window=10, min_periods=1).mean()).rolling(window=3).sum()
)
```

**Impacto:** Captura fases de jogadores (em alta/em baixa) que a média simples perde.

---

#### 2. **Features de Contexto do Jogo e Fase do Campeonato**
**Problema:** Jogos têm importâncias diferentes (início, meio, fim de campeonato, clássicos).

**Solução:**
```python
# Adicionar em preparar_features_historicas()

# 1. Fase do Campeonato (Normalizada 0-1)
df['fase_campeonato'] = df['rodada'] / 38.0

# 2. Importância do Jogo (Baseado na posição na tabela)
# Precisa calcular posição do time na tabela naquela rodada
def calcular_posicao_tabela(df_partidas, clube_id, ano, rodada):
    # Calcula pontos até aquela rodada
    # Retorna posição (1-20)
    pass

df['posicao_tabela'] = df.apply(
    lambda row: calcular_posicao_tabela(df_partidas, row['clube_id_num'], row['ano'], row['rodada']),
    axis=1
)
df['pressao_tabela'] = np.where(df['posicao_tabela'] <= 4, 1.0,  # Líderes
                        np.where(df['posicao_tabela'] >= 17, 1.0,  # Zona de rebaixamento
                        0.5))  # Meio da tabela

# 3. Confronto Direto (Head-to-Head)
def calcular_h2h(df_partidas, clube_id, adversario_id, ano, rodada):
    # Histórico de confrontos entre os dois times
    # Retorna: média de gols feitos, média de gols sofridos, aproveitamento
    pass

df['h2h_media_gols'] = df.apply(
    lambda row: calcular_h2h(df_partidas, row['clube_id_num'], row['adversario_id'], row['ano'], row['rodada']),
    axis=1
)

# 4. Sequência de Resultados do Time
def calcular_sequencia_time(df_partidas, clube_id, ano, rodada):
    # Últimos 5 resultados do time (V/E/D)
    # Retorna: sequência de vitórias, empates, derrotas
    pass

df['time_sequencia_vitorias'] = df.apply(
    lambda row: calcular_sequencia_time(df_partidas, row['clube_id_num'], row['ano'], row['rodada']),
    axis=1
)
```

**Impacto:** Jogadores em jogos importantes ou em fases críticas têm comportamento diferente.

---

#### 3. **Features de Interação (Sinergia entre Variáveis)**
**Problema:** O modelo não captura interações importantes (ex: mando de campo + força adversário).

**Solução:**
```python
# Adicionar features de interação

# 1. Mando × Força do Adversário
df['mando_x_adv_gols_sofridos'] = df['fl_mandante'] * df['adv_media_gols_sofridos']
df['mando_x_adv_gols_feitos'] = df['fl_mandante'] * df['adv_media_gols_feitos']

# 2. Posição × Força do Adversário (Específico por posição)
df['ata_x_adv_gols_sofridos'] = (df['posicao_id'] == 5).astype(int) * df['adv_media_gols_sofridos']
df['def_x_adv_gols_feitos'] = (df['posicao_id'].isin([2, 3])).astype(int) * df['adv_media_gols_feitos']

# 3. Momentum × Preço (Jogador em alta e barato = bom negócio)
df['momentum_x_custo_beneficio'] = df['media_3_rodadas'] / (df['preco_num'] + 0.1)

# 4. Volatilidade × Média (Explosivo vs Consistente)
df['volatilidade_x_media'] = df['volatilidade'] * df['media_temporada']

# 5. Tendência × Mando (Jogador em alta jogando em casa)
df['tendencia_x_mando'] = df['pontos_tendencia'] * df['fl_mandante']
```

**Impacto:** Captura relações não-lineares que o XGBoost pode não descobrir sozinho.

---

#### 4. **Melhor Uso das Odds (Features Avançadas)**
**Problema:** Apenas probabilidade de vitória é usada, mas odds contêm mais informação.

**Solução:**
```python
# Adicionar em preprocessamento ou preparar_features_historicas()

# 1. Valor Esperado da Vitória (Expected Value)
df['ev_vitoria'] = df['prob_vitoria'] * 3  # 3 pontos por vitória

# 2. Implied Probability de Over/Under (se disponível)
# Odds de Over 2.5 gols indica jogo aberto (bom para atacantes)

# 3. Discrepância entre Odds e Estatísticas
df['odds_vs_stats'] = df['prob_vitoria'] - df['aproveitamento_time'] / 100

# 4. Probabilidade de Empate (Importante para defensores)
df['prob_empate'] = (1 / df['odd_empate']) / df['soma_inverso_odds']

# 5. Probabilidade de Gols (Over/Under implícito)
# Se odd Over 2.5 é baixa, jogo tende a ter muitos gols
```

**Impacto:** Odds refletem conhecimento coletivo do mercado, são muito informativas.

---

### 🟠 **IMPACTO ALTO** (Redução esperada: 5-10% no RMSE)

#### 5. **Features de Contexto do Time (Não só do Jogador)**
**Problema:** Jogadores do mesmo time têm correlação, mas isso não é explorado.

**Solução:**
```python
# 1. Média de Pontos dos Companheiros de Time (Últimas 3 rodadas)
df['time_media_pontos'] = df.groupby(['ano', 'rodada', 'clube_id_num'])['pontuacao'].transform('mean')

# 2. Força do Ataque do Time (Para defensores - se time ataca bem, defesa sofre menos)
df['time_forca_ataque'] = df.groupby(['ano', 'rodada', 'clube_id_num']).apply(
    lambda x: x[x['posicao_id'].isin([4, 5])]['pontuacao'].mean()
)

# 3. Força da Defesa do Time (Para atacantes - se defesa é forte, ataque tem menos pressão)
df['time_forca_defesa'] = df.groupby(['ano', 'rodada', 'clube_id_num']).apply(
    lambda x: x[x['posicao_id'].isin([1, 2, 3])]['pontuacao'].mean()
)

# 4. Sequência de Resultados do Time
df['time_ultimos_5_resultados'] = calcular_sequencia_resultados_time(df, clube_id, ano, rodada)

# 5. Posição na Tabela (Já mencionado acima, mas importante)
```

**Impacto:** Jogadores de times em boa fase tendem a pontuar mais.

---

#### 6. **Features de Consistência vs Explosividade**
**Problema:** Modelo não diferencia jogadores consistentes de explosivos.

**Solução:**
```python
# 1. Coeficiente de Variação (CV)
df['cv_pontuacao'] = df['volatilidade_historica'] / (df['media_temporada'] + 0.1)

# 2. Frequência de Pontuações Altas
df['freq_alta'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: (x >= x.quantile(0.75)).rolling(window=10, min_periods=5).mean()
)

# 3. Frequência de Pontuações Baixas
df['freq_baixa'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: (x <= x.quantile(0.25)).rolling(window=10, min_periods=5).mean()
)

# 4. Máximo vs Média (Potencial de Explosão)
df['max_vs_media'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=10, min_periods=5).max() / (x.rolling(window=10, min_periods=5).mean() + 0.1)
)

# 5. Percentil Recente (Como está em relação ao próprio histórico)
df['percentil_recente'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: (x.iloc[-1] >= x.rolling(window=20, min_periods=10).quantile(0.5)).astype(int)
)
```

**Impacto:** Ajuda o modelo a diferenciar jogadores "seguros" de "loteria".

---

#### 7. **Tratamento de Outliers e Transformações**
**Problema:** Pontuações têm distribuição assimétrica (muitos zeros/baixas, poucas altas).

**Solução:**
```python
# 1. Transformação Logarítmica para Features Assimétricas
df['log_preco'] = np.log1p(df['preco_num'])
df['log_media'] = np.log1p(df['media_temporada'] + 1)  # +1 para evitar log(0)

# 2. Winsorização (Limitar extremos)
def winsorize(series, lower=0.05, upper=0.95):
    lower_bound = series.quantile(lower)
    upper_bound = series.quantile(upper)
    return series.clip(lower_bound, upper_bound)

df['media_winsorized'] = df.groupby('posicao_id')['media_temporada'].transform(
    lambda x: winsorize(x)
)

# 3. Binning de Features Contínuas (Criar categorias)
df['preco_categoria'] = pd.cut(df['preco_num'], bins=[0, 5, 10, 15, 20, 100], labels=['Muito Barato', 'Barato', 'Médio', 'Caro', 'Muito Caro'])

# 4. Target Encoding (Média da pontuação por categoria)
df['preco_cat_media'] = df.groupby('preco_categoria')['pontuacao'].transform('mean')

# 5. Tratamento Especial para Zeros (Jogadores que não jogaram)
df['jogou'] = (df['pontuacao'] > 0).astype(int)
# Treinar modelo separado para prever se jogou, depois prever pontuação condicional
```

**Impacto:** Melhora a capacidade do modelo de lidar com distribuições não-normais.

---

#### 8. **Features Temporais Avançadas**
**Problema:** Apenas média móvel é usada, mas padrões temporais são mais complexos.

**Solução:**
```python
# 1. Sazonalidade (Alguns jogadores são melhores em certas fases)
df['rodada_sin'] = np.sin(2 * np.pi * df['rodada'] / 38)
df['rodada_cos'] = np.cos(2 * np.pi * df['rodada'] / 38)

# 2. Janelas Múltiplas (Não só 3 rodadas)
df['media_1_rodada'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].shift(1)
df['media_5_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).mean()
)
df['media_10_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=10, min_periods=5).mean()
)

# 3. Diferença entre Janelas (Momentum de Curto vs Longo Prazo)
df['diff_3_10'] = df['media_3_rodadas'] - df['media_10_rodadas']

# 4. Recência Ponderada (Últimas rodadas têm mais peso)
def weighted_average(series, weights):
    return (series * weights).sum() / weights.sum()

df['media_ponderada'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).apply(
        lambda y: weighted_average(y, np.array([5, 4, 3, 2, 1][:len(y)]))
    )
)
```

**Impacto:** Captura padrões temporais que médias simples perdem.

---

### 🟡 **IMPACTO MÉDIO** (Redução esperada: 2-5% no RMSE)

#### 9. **Features de Mercado e Popularidade**
**Problema:** Variação de preço e popularidade podem indicar expectativa do mercado.

**Solução:**
```python
# 1. Variação de Preço (Se subiu muito, expectativa alta)
df['variacao_preco_pct'] = df['variacao_num'] / (df['preco_num'] - df['variacao_num'] + 0.1)

# 2. Popularidade (Percentual de times que têm o jogador - se disponível na API)
# df['popularidade'] = df['escalacoes'] / df['total_times']  # Se disponível

# 3. Preço Relativo à Média da Posição
df['preco_vs_media_posicao'] = df['preco_num'] / df.groupby('posicao_id')['preco_num'].transform('mean')

# 4. Custo-Benefício Relativo
df['cb_vs_media_posicao'] = df['custo_beneficio'] / df.groupby('posicao_id')['custo_beneficio'].transform('mean')
```

**Impacto:** Mercado tem informação agregada que pode ser útil.

---

#### 10. **Features de Calendário e Descanso**
**Problema:** Jogadores com mais descanso ou sequência de jogos podem ter performance diferente.

**Solução:**
```python
# 1. Dias de Descanso (Se disponível nos dados)
def calcular_dias_descanso(df_partidas, clube_id, rodada, ano):
    # Calcula dias entre jogos
    pass

df['dias_descanso'] = df.apply(
    lambda row: calcular_dias_descanso(df_partidas, row['clube_id_num'], row['rodada'], row['ano']),
    axis=1
)

# 2. Sequência de Jogos (Jogos consecutivos)
df['jogos_consecutivos'] = calcular_sequencia_jogos(df_partidas, clube_id, rodada, ano)

# 3. Fadiga Acumulada (Soma de minutos/jogos recentes)
# Se disponível dados de minutos jogados
```

**Impacto:** Fadiga e descanso afetam performance.

---

#### 11. **Ensemble e Calibração de Previsões**
**Problema:** Um único modelo pode ter viés sistemático.

**Solução:**
```python
# 1. Ensemble de Modelos
# Treinar múltiplos modelos com diferentes:
#   - Hiperparâmetros
#   - Features
#   - Janelas temporais
# E fazer média ponderada

def ensemble_predict(models, X, weights=None):
    if weights is None:
        weights = [1.0 / len(models)] * len(models)
    predictions = [model.predict(X) for model in models]
    return np.average(predictions, axis=0, weights=weights)

# 2. Calibração (Ajustar previsões para serem mais calibradas)
from sklearn.calibration import CalibratedRegressorCV
calibrated_model = CalibratedRegressorCV(base_model, cv=5)

# 3. Quantile Regression (Prever intervalos, não só média)
from sklearn.ensemble import GradientBoostingRegressor
quantile_models = {
    'q10': GradientBoostingRegressor(loss='quantile', alpha=0.1),
    'q50': GradientBoostingRegressor(loss='quantile', alpha=0.5),
    'q90': GradientBoostingRegressor(loss='quantile', alpha=0.9)
}
```

**Impacto:** Reduz variância e melhora robustez.

---

#### 12. **Feature Selection Inteligente**
**Problema:** Muitas features podem causar overfitting.

**Solução:**
```python
# 1. Mutual Information
from sklearn.feature_selection import mutual_info_regression
mi_scores = mutual_info_regression(X_train, y_train)
selected_features = X_train.columns[mi_scores > threshold]

# 2. Permutation Importance (Já calculado pelo XGBoost, mas pode ser usado para seleção)
# 3. Recursive Feature Elimination
from sklearn.feature_selection import RFE
selector = RFE(XGBRegressor(), n_features_to_select=30)
selector.fit(X_train, y_train)

# 4. Remover Features Altamente Correlacionadas
correlation_matrix = X_train.corr().abs()
upper_triangle = correlation_matrix.where(
    np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
)
high_corr_features = [column for column in upper_triangle.columns if any(upper_triangle[column] > 0.95)]
```

**Impacto:** Reduz overfitting e melhora generalização.

---

## 📊 Implementação Priorizada

### Fase 1 (Implementar Primeiro - Maior Impacto):
1. ✅ Features de Tendência e Aceleração
2. ✅ Features de Interação
3. ✅ Melhor Uso das Odds
4. ✅ Features de Contexto do Time

### Fase 2 (Segundo):
5. ✅ Features de Consistência vs Explosividade
6. ✅ Tratamento de Outliers
7. ✅ Features Temporais Avançadas

### Fase 3 (Refinamento):
8. ✅ Features de Contexto do Jogo
9. ✅ Ensemble e Calibração
10. ✅ Feature Selection

---

## 🔧 Exemplo de Código Completo

```python
# Adicionar em preparar_features_historicas() após linha 247

# ========== FEATURES DE TENDÊNCIA ==========
print("  > Criando features de tendência...")
df['pontos_tendencia'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).apply(
        lambda y: np.polyfit(range(len(y)), y, 1)[0] if len(y) >= 2 else 0
    )
).fillna(0)

df['pontos_aceleracao'] = df.groupby(['ano', 'atleta_id'])['pontos_tendencia'].diff().fillna(0)

# ========== FEATURES DE INTERAÇÃO ==========
print("  > Criando features de interação...")
df['mando_x_adv_gols_sofridos'] = df['fl_mandante'] * df['adv_media_gols_sofridos']
df['mando_x_adv_gols_feitos'] = df['fl_mandante'] * df['adv_media_gols_feitos']
df['ata_x_adv_gols_sofridos'] = (df['posicao_id'] == 5).astype(int) * df['adv_media_gols_sofridos']
df['def_x_adv_gols_feitos'] = (df['posicao_id'].isin([2, 3])).astype(int) * df['adv_media_gols_feitos']

# ========== FEATURES DE CONSISTÊNCIA ==========
print("  > Criando features de consistência...")
df['volatilidade_recente'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).std()
).fillna(0)

df['volatilidade_historica'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.expanding().std()
).fillna(0)

df['ratio_volatilidade'] = (df['volatilidade_recente'] / (df['volatilidade_historica'] + 0.1)).fillna(1.0)

# ========== FEATURES TEMPORAIS AVANÇADAS ==========
print("  > Criando features temporais avançadas...")
df['media_5_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=5, min_periods=3).mean()
).fillna(df['media_3_rodadas'])

df['media_10_rodadas'] = df.groupby(['ano', 'atleta_id'])['pontos_last'].transform(
    lambda x: x.rolling(window=10, min_periods=5).mean()
).fillna(df['media_temporada'])

df['diff_3_10'] = df['media_3_rodadas'] - df['media_10_rodadas']

# ========== FEATURES DE CONTEXTO DO TIME ==========
print("  > Criando features de contexto do time...")
df['time_media_pontos'] = df.groupby(['ano', 'rodada', 'clube_id_num'])['pontuacao'].transform('mean').fillna(0)

print("  > Features avançadas criadas com sucesso!")
```

---

## 📈 Métricas para Acompanhar

Após implementar cada melhoria, medir:
- **RMSE** (objetivo principal)
- **MAE** (Mean Absolute Error)
- **R²** (Coeficiente de determinação)
- **RMSE por Posição** (algumas posições podem melhorar mais)
- **RMSE por Faixa de Pontuação** (erro em jogadores de alta pontuação vs baixa)

---

## 🎯 Expectativa de Redução de RMSE

- **Implementando Fase 1:** Redução de 15-25% no RMSE
- **Implementando Fase 1 + 2:** Redução de 20-30% no RMSE
- **Implementando Tudo:** Redução de 25-35% no RMSE

**Nota:** Resultados podem variar dependendo da qualidade dos dados históricos e do RMSE atual.

---

## ⚠️ Cuidados Importantes

1. **Data Leakage:** Garantir que todas as features usem apenas dados disponíveis ANTES da rodada
2. **Overfitting:** Usar validação temporal (não aleatória) para evitar overfitting
3. **Missing Values:** Tratar adequadamente valores faltantes (não apenas fillna(0))
4. **Feature Scaling:** XGBoost não precisa, mas algumas features podem se beneficiar
5. **Validação Temporal:** Sempre validar em rodadas futuras, não aleatórias

---

## 🔄 Próximos Passos

1. Implementar features da Fase 1
2. Retreinar modelos
3. Comparar RMSE antes/depois
4. Iterar e refinar
5. Documentar quais features têm maior importância (feature importance)

