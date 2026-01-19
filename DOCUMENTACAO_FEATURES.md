# Documentação de Features do Modelo Cartola IA

Este documento descreve as variáveis (features) utilizadas pelos modelos de inteligência artificial para prever a pontuação dos jogadores no Cartola FC.

## 1. Features Universais (Usadas em todas as posições)

Estas features fornecem o contexto básico do jogador e da partida.

*   `preco_num`: Preço do jogador antes da rodada começar (usando o preço da rodada anterior para evitar leakage).
*   `media_temporada`: Média de pontos acumulada pelo jogador na temporada atual.
*   `media_3_rodadas`: Média móvel dos pontos nas últimas 3 partidas (capta fase recente).
*   `fl_mandante`: Indica se o jogador joga em casa (1) ou fora (0).
*   `rodada`: O número da rodada atual.
*   `clube_id`: Identificação do clube para capturar o "peso da camisa".

---

## 2. Features de Inteligência Coletiva (Equilíbrio de Jogo)

Calculadas para entender o cenário tático e o favoritismo.

*   `dif_forca_clube`: **(NOVA)** Métrica avançada que combina o aproveitamento recente do clube (60%) com o seu valor de mercado (40%) comparado ao adversário. Útil para identificar clubes tecnicamente superiores que podem estar em má fase passageira ou clubes que subiram de divisão.
*   `dif_aproveitamento`: Diferença entre o aproveitamento puro do time do jogador e o do adversário.
*   `odd_vitoria_propria`: **(NOVA)** Probabilidade implícita do mercado (Odd). Indica o favoritismo real baseado em casas de apostas, capturando desfalques e notícias de última hora que as estatísticas puras podem perder.
*   `probabilidade_sg`: Cálculo que cruza a solidez defensiva do time com a ineficiência ofensiva do adversário. **Nota:** Esta feature recebe um bônus de peso de 20% para Goleiros e Defensores.
*   `adv_media_gols_feitos/sofridos`: Médias históricas do adversário.
*   `own_media_gols_feitos/sofridos`: Médias históricas do próprio time.

---

## 3. Features de Performance Individual (Momentum e Eficiência)

*   `pontos_slope_5`: Tendência de crescimento nos últimos 5 jogos (Inclinação da curva).
*   `pontos_aceleracao`: Mudança na tendência (Momentum).
*   `pontuacao_cv_temporada`: Coeficiente de Variação (Estabilidade vs. Explosividade).
*   `medalhas_top5_acumuladas`: Total de aparições entre os 5 melhores da posição no ano.
*   `percentual_top5_acumulado`: Eficiência real (Medalhas / Jogos Realmente Disputados).

---

## 4. Dados Avançados FBRef (Previsão Proativa)

*   `fbref_xG_jogo`: Gols Esperados (Expected Goals). Indica volume ofensivo e qualidade de finalização.
*   `fbref_xA_jogo`: Assistências Esperadas (Expected Assists). Indica volume de criação de jogadas.

---

## 5. Features de Interação e Scouts Específicos

*   `mando_x_adv_gols_sofridos`: Potencializa atacantes mandantes contra defesas fracas.
*   `ata_x_adv_gols_sofridos`: Interação específica para Atacantes.
*   `def_x_adv_gols_feitos`: Interação específica para Defensores contra ataques produtivos.

| Posição | Scouts Monitorados |
| :--- | :--- |
| **Goleiro** | DE, GS, SG, DP, PS |
| **Defensores** | SG, DS, FS, G, A, CA, CV, GC |
| **Meias** | G, A, DS, FS, FF, FD, FT, I, PP, CA |
| **Atacantes** | G, A, FF, FD, FT, FS, DS, I |
| **Técnico** | Foca em médias coletivas, mando e diferença de aproveitamento. |
