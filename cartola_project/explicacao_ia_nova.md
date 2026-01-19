# Como Funciona a IA Nova - Explicação Completa

## Visão Geral

A IA Nova usa **Machine Learning (XGBoost)** para prever a pontuação de cada jogador na rodada, e depois usa **Programação Linear** para montar o melhor time possível dentro das regras do Cartola FC.

## Processo em 3 Etapas

### 1. PREPROCESSAMENTO DE DADOS (`utils/preprocessamento.py`)

Antes de fazer previsões, o sistema prepara os dados:
- Identifica quem joga em **casa** ou **fora**
- Identifica o **adversário** de cada time
- Calcula estatísticas do adversário (média de gols feitos/sofridos)

### 2. PREVISÃO DA PONTUAÇÃO (`utils/modelagem.py`)

O modelo XGBoost usa **5 modelos especialistas** (um para cada tipo de posição):
- **Goleiros** (modelo_gol.pkl)
- **Defensores** - Laterais e Zagueiros (modelo_def.pkl)
- **Meias** (modelo_mei.pkl) ← **Luiz Gustavo usa este modelo**
- **Atacantes** (modelo_ata.pkl)
- **Técnicos** (modelo_tec.pkl)

#### Features que o Modelo Usa (Exemplo: Meias)

**Features Básicas:**
- `preco_num`: Preço do jogador
- `media_temporada`: Média de pontos na temporada
- `media_3_rodadas`: Média das últimas 3 rodadas
- `posicao_id`: ID da posição (4 = Meia)

**Features Avançadas (IA Nova):**
- `fl_mandante`: 1 se joga em casa, 0 se joga fora
- `adv_media_gols_feitos`: Média de gols que o adversário faz
- `adv_media_gols_sofridos`: Média de gols que o adversário toma

**Features de Scouts (para meias):**
- `media_G_season`, `media_G_last3`: Média de gols
- `media_A_season`, `media_A_last3`: Média de assistências
- `media_DS_season`, `media_DS_last3`: Média de desarmes
- `media_FS_season`, `media_FS_last3`: Média de finalizações certas
- `media_FF_season`, `media_FF_last3`: Média de finalizações para fora
- E outros scouts relevantes para meias...

#### Como o Modelo Preve a Pontuação

1. O modelo **XGBoost** recebe todas essas features
2. Ele compara com **160 mil+ jogos históricos** (2022-2025)
3. Ele aprende padrões como:
   - "Jogadores que jogam em casa tendem a pontuar mais"
   - "Jogadores contra adversários que tomam muitos gols tendem a pontuar mais"
   - "Jogadores com média alta recente tendem a manter boa pontuação"

4. O modelo retorna uma **previsão base** (`pontuacao_prevista_base`)

#### Bônus Tático (`aplicar_bonus_tatico`)

Após a previsão base, o sistema aplica **multiplicadores táticos**:

**Para MEIAS (posição 4):**

```python
multiplicador = 1.0

# 1. Bônus de Mando de Campo
if joga_em_casa:
    multiplicador += 0.08  # +8%
elif joga_fora:
    multiplicador -= 0.03  # -3%

# 2. Bônus do Adversário (para meias/atacantes)
if adversario_toma_muitos_gols (>= 1.5 gols/jogo):
    multiplicador += 0.20  # +20%
elif adversario_toma_poucos_gols (<= 0.8 gols/jogo):
    multiplicador -= 0.15  # -15%

# 3. Pontuação Final = Previsão Base × Multiplicador
pontuacao_prevista = pontuacao_prevista_base × multiplicador
```

### 3. OTIMIZAÇÃO DO TIME (`utils/otimizador.py`)

Depois de ter a pontuação prevista de **TODOS** os jogadores, o otimizador usa **Programação Linear** para:

**OBJETIVO:** Maximizar a soma de `pontuacao_prevista` de todos os jogadores escolhidos

**RESTRIÇÕES:**
1. **Orçamento**: Custo total ≤ 140 cartoletas (ou o definido)
2. **Formação**: 
   - 4-3-3: 1 Goleiro, 2 Laterais, 2 Zagueiros, 3 Meias, 3 Atacantes, 1 Técnico
   - O Luiz Gustavo entra como um dos 3 meias
3. **Limite por Clube**: Máximo 5 jogadores do mesmo clube

**Como Funciona:**
- O algoritmo testa **milhões de combinações** possíveis
- Ele escolhe a combinação que **maximiza a pontuação total** respeitando todas as restrições
- Se o Luiz Gustavo foi escolhido, é porque ele oferece a **melhor relação pontuação/preço** dentro do orçamento

---

## Por Que o Luiz Gustavo Foi Escolhido?

### Dados do Luiz Gustavo (Rodada Atual):

- **Nome**: Luiz Gustavo
- **Clube**: São Paulo (ID 276)
- **Posição**: Meia (ID 4)
- **Preço**: 8.02 cartoletas
- **Média Temporada**: 3.5 pontos
- **Adversário**: Juventude (ID 286)
- **Mando**: Em casa (fator_casa = 1)

### Por que ele foi escolhido?

1. **Preço Acessível (8.02)**:
   - O modelo precisa escalar 3 meias
   - Meias caros (15-20 cartoletas) podem não caber no orçamento
   - Luiz Gustavo oferece um preço intermediário que libera orçamento para outros setores

2. **Mando de Campo**:
   - São Paulo joga em CASA contra Juventude
   - Isso dá +8% de bônus na previsão

3. **Adversário**:
   - Juventude é um adversário "acessível"
   - O modelo pode ter previsto uma boa pontuação baseada nas estatísticas do adversário

4. **Razão Pontuação/Preço**:
   - Mesmo que sua pontuação prevista não seja a maior entre os meias
   - O **custo-benefício** pode ser melhor que meias mais caros
   - Exemplo: Um meia de 15 cartoletas pode prever 6 pontos, mas o Luiz Gustavo de 8 cartoletas pode prever 4 pontos = melhor relação

5. **Restrição de Orçamento**:
   - Se o modelo escalou jogadores caros em outras posições
   - O orçamento pode ter ficado apertado para meias
   - Luiz Gustavo pode ser a melhor opção dentro do orçamento restante

### O que o Modelo NÃO Considera (Limitações):

1. **Oscilação**: O modelo usa a **média**, não considera especificamente a volatilidade
2. **Contexto Recente**: Usa média de 3 rodadas, mas pode não capturar tendências muito recentes
3. **Fatores Subjetivos**: Não considera lesões recentes, clima, etc. (apenas dados históricos)

---

## Como Verificar os Dados do Luiz Gustavo

Para ver exatamente o que o modelo previu para ele, você pode:

1. Abrir `rodada_atual_processada.csv`
2. Procurar pelo atleta_id `71536`
3. Ver a coluna `pontuacao_prevista` (última coluna antes dos scouts detalhados)

Isso mostrará a pontuação exata que o modelo previu para ele e por que ele foi escolhido pelo otimizador.

