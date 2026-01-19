# Explicação das Métricas xG e xA do FBref

## 📊 Métricas de Expected Goals (xG) e Expected Assists (xA)

### **1. xG (Expected Goals) - Total da Temporada**
- **O que é:** Soma de todos os Expected Goals do jogador na temporada
- **Interpretação:** Quantos gols o jogador "deveria" ter marcado baseado na qualidade das finalizações
- **Exemplo:** Se um jogador tem xG = 17.3, significa que baseado nas chances que teve, ele deveria ter marcado ~17 gols
- **Uso:** Comparar com gols reais (Gls) para ver se o jogador está finalizando melhor ou pior que o esperado

### **2. npxG (Non-Penalty Expected Goals) - Total da Temporada**
- **O que é:** Expected Goals excluindo pênaltis
- **Interpretação:** Quantos gols o jogador "deveria" ter marcado apenas em jogadas abertas (sem pênaltis)
- **Por que importa:** Pênaltis têm xG muito alto (~0.76), então npxG é mais representativo do desempenho em campo
- **Uso:** Melhor métrica para avaliar a qualidade das finalizações em jogadas normais

### **3. xAG (Expected Assisted Goals) ou xA (Expected Assists) - Total da Temporada**
- **O que é:** Soma de todos os Expected Assists do jogador na temporada
- **Interpretação:** Quantas assistências o jogador "deveria" ter dado baseado na qualidade dos passes que fez
- **Exemplo:** Se um jogador tem xAG = 7.3, significa que baseado nos passes que fez, ele deveria ter dado ~7 assistências
- **Uso:** Comparar com assistências reais (Ast) para ver se os companheiros estão finalizando bem os passes dele

### **4. npxG+xAG - Total da Temporada**
- **O que é:** Soma de Non-Penalty Expected Goals + Expected Assisted Goals
- **Interpretação:** Contribuição total esperada do jogador (gols + assistências) excluindo pênaltis
- **Uso:** Métrica completa de criação de gols (próprios e para companheiros)

---

## 📈 Métricas "Per 90 Minutes" (Por 90 Minutos)

### **5. xG.1 (Expected Goals per 90)**
- **O que é:** xG total dividido por minutos jogados, multiplicado por 90
- **Fórmula:** `(xG_total / Minutos) * 90`
- **Interpretação:** Quantos Expected Goals o jogador gera por 90 minutos jogados
- **Uso:** Comparar jogadores que jogaram quantidades diferentes de minutos
- **Exemplo:** xG.1 = 0.38 significa que o jogador gera 0.38 Expected Goals a cada 90 minutos

### **6. xAG.1 (Expected Assisted Goals per 90)**
- **O que é:** xAG total dividido por minutos jogados, multiplicado por 90
- **Fórmula:** `(xAG_total / Minutos) * 90`
- **Interpretação:** Quantos Expected Assists o jogador gera por 90 minutos jogados
- **Uso:** Comparar capacidade de criar chances para companheiros independente de minutos jogados
- **Exemplo:** xAG.1 = 0.29 significa que o jogador gera 0.29 Expected Assists a cada 90 minutos

### **7. xG+xAG (Expected Goals + Assists per 90)**
- **O que é:** Soma de xG.1 + xAG.1
- **Interpretação:** Contribuição total esperada por 90 minutos (gols próprios + assistências)
- **Uso:** Métrica completa de criação de gols normalizada por tempo

### **8. npxG.1 (Non-Penalty Expected Goals per 90)**
- **O que é:** npxG total dividido por minutos jogados, multiplicado por 90
- **Interpretação:** Expected Goals (sem pênaltis) por 90 minutos
- **Uso:** Melhor métrica para avaliar qualidade de finalizações normalizada por tempo

### **9. npxG+xAG.1 (Non-Penalty xG + xA per 90)**
- **O que é:** Soma de npxG.1 + xAG.1
- **Interpretação:** Contribuição total esperada por 90 minutos excluindo pênaltis
- **Uso:** Métrica mais completa e justa para comparar jogadores

---

## 🎯 Qual Usar?

### **Para Análise Combinada Cartola + FBref:**
- **XA/jogo:** Use `xAG.1` (Expected Assists por 90 minutos)
- **XG/jogo:** Use `xG.1` (Expected Goals por 90 minutos)

**Por quê?**
- Já estão normalizados por 90 minutos
- Permitem comparar jogadores que jogaram quantidades diferentes de minutos
- São as métricas mais usadas para análise de performance

### **Comparações Úteis:**

1. **xG vs Gls (Gols Reais):**
   - Se Gls > xG: Jogador está finalizando melhor que o esperado
   - Se Gls < xG: Jogador está desperdiçando chances

2. **xAG vs Ast (Assistências Reais):**
   - Se Ast > xAG: Companheiros estão finalizando bem os passes dele
   - Se Ast < xAG: Companheiros estão desperdiçando chances criadas

3. **npxG vs xG:**
   - Diferença mostra quantos Expected Goals vieram de pênaltis
   - npxG é mais representativo do desempenho em campo

---

## 📋 Exemplo Prático (Kaio Jorge):

Do arquivo CSV:
- **Gls:** 21 gols reais
- **xG:** 17.3 Expected Goals
- **npxG:** 17.3 (sem pênaltis, então não marcou pênaltis)
- **xG.1:** 0.68 Expected Goals por 90 min
- **Ast:** 8 assistências reais
- **xAG:** 3.4 Expected Assists
- **xAG.1:** 0.12 Expected Assists por 90 min

**Interpretação:**
- Kaio Jorge marcou **21 gols** mas tinha **xG de 17.3**, então está finalizando **23% melhor** que o esperado
- Deu **8 assistências** mas tinha **xAG de 3.4**, então os companheiros estão finalizando **135% melhor** que o esperado nos passes dele
- Gera **0.68 Expected Goals por 90 minutos** (alta eficiência ofensiva)
- Gera **0.12 Expected Assists por 90 minutos** (moderada criação de chances)




