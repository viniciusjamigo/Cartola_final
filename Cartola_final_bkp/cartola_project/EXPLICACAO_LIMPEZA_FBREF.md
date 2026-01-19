# 📋 Explicação: Limpeza de Dados do FBref

## 🔍 Problema Identificado

O arquivo `fbref_jogadores_serie_a.csv` foi gerado coletando dados clube por clube. A cada coleta de um novo clube, o `pandas.read_html()` incluiu **2 linhas de cabeçalho**:

1. **Linha de sub-cabeçalho**: `,,,,Playing Time,Playing Time,...` (categorias das colunas)
2. **Linha de cabeçalho principal**: `Player,Nation,Pos,Age,MP,Starts,...` (nomes das colunas)

Isso resultou em cabeçalhos duplicados a cada novo clube coletado.

## 🧹 Como o Script de Limpeza Funciona

### Script: `limpar_fbref_jogadores.py`

**Passo a passo:**

1. **Lê o arquivo linha por linha**
   - Mantém apenas a **primeira linha** como cabeçalho válido
   - Identifica e remove todas as linhas subsequentes que são cabeçalhos

2. **Identifica cabeçalhos duplicados:**
   - Linhas que começam com `,,,,Playing Time` → **Sub-cabeçalho** (remove)
   - Linhas que começam com `Player,Nation,Pos,Age` → **Cabeçalho principal** (remove, exceto a primeira)

3. **Extrai o clube de cada linha:**
   - O clube está nas últimas colunas, antes da URL
   - Usa "forward fill" para preencher o clube em todas as linhas

4. **Cria coluna "Clube":**
   - Identifica automaticamente qual coluna contém o nome do clube
   - Cria a coluna "Clube" e preenche com os valores corretos

5. **Remove linhas inválidas:**
   - Remove linhas onde Player é vazio
   - Remove linhas duplicadas
   - Remove linhas que são apenas vírgulas

6. **Salva o arquivo limpo:**
   - Substitui o arquivo original pelo arquivo limpo

## 🛡️ Prevenção Futura: Melhorias no Script de Coleta

### Script: `coletar_fbref.py` - Função `coletar_jogadores_de_clube()`

**Melhorias implementadas:**

1. **Remove cabeçalhos durante a coleta:**
   ```python
   # Remove linhas onde a primeira coluna é "Player" (cabeçalho)
   df_temp = df_temp[df_temp.iloc[:, 0].astype(str) != 'Player'].copy()
   
   # Remove linhas onde a primeira coluna começa com vírgulas (sub-cabeçalhos)
   df_temp = df_temp[~df_temp.iloc[:, 0].astype(str).str.startswith(',')].copy()
   ```

2. **Adiciona coluna Clube imediatamente:**
   ```python
   df_temp['Clube'] = nome_clube
   df_temp['URL_Clube'] = url_clube
   ```

3. **Limpeza final antes de salvar:**
   ```python
   # Remove cabeçalhos duplicados que possam ter sido incluídos
   if 'Player' in df_jogadores.columns:
       df_jogadores = df_jogadores[df_jogadores['Player'].astype(str) != 'Player'].copy()
       df_jogadores = df_jogadores[~df_jogadores['Player'].astype(str).str.startswith(',')].copy()
   ```

## 🔄 Fluxo Completo

### Coleta Atual (com problema):
```
Clube 1: [Cabeçalho] + [Dados]
Clube 2: [Cabeçalho] + [Dados]  ← Cabeçalho duplicado!
Clube 3: [Cabeçalho] + [Dados]  ← Cabeçalho duplicado!
```

### Coleta Futura (corrigida):
```
Clube 1: [Cabeçalho] + [Dados limpos]
Clube 2: [Dados limpos]  ← Sem cabeçalho!
Clube 3: [Dados limpos]  ← Sem cabeçalho!
```

## 📝 Como Usar

### 1. Limpar arquivo atual:
```bash
cd cartola_project
python limpar_fbref_jogadores.py
```

### 2. Coletar dados futuros:
```bash
python coletar_fbref.py --apenas-jogadores --ano 2025
```
**Agora já vem limpo!** ✅

## ✅ Garantias

- ✅ **Cabeçalho único**: Apenas a primeira linha do arquivo será cabeçalho
- ✅ **Coluna Clube**: Sempre criada e preenchida corretamente
- ✅ **Dados limpos**: Sem cabeçalhos duplicados em coletas futuras
- ✅ **Backward compatible**: O script de limpeza funciona mesmo com arquivos antigos




