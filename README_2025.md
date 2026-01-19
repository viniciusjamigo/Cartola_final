# ⚽ Cartola FC Pro AI - Sistema Avançado de Predição e Otimização (2025)

Bem-vindo ao **Cartola FC Pro AI**, um ecossistema completo para análise, predição e otimização de escalações no Cartola FC. Diferente de otimizadores básicos, este projeto utiliza **Machine Learning (XGBoost)**, **Backtesting de Estratégia** e **Análise Pós-Rodada** para maximizar seus resultados.

![Status do Projeto](https://img.shields.io/badge/Status-Operacional%20(IA%20Ativa)-brightgreen)
![Modelo](https://img.shields.io/badge/IA-XGBoost%20Especialista-blue)
![Dados](https://img.shields.io/badge/Histórico-2018--2025-orange)
![Features](https://img.shields.io/badge/Features-Completas-purple)

---

## 🧠 O Cérebro do Sistema

A inteligência é dividida em múltiplas camadas que trabalham em conjunto:

### 1. Modelos Preditivos (XGBoost por Posição)
Não usamos um modelo genérico. Treinamos **5 modelos distintos**, cada um especialista em prever a pontuação de uma posição, agora utilizando **médias de scouts detalhados (Gols, Desarmes, Finalizações)** como features.
*   `modelo_gol.pkl`, `modelo_def.pkl`, `modelo_mei.pkl`, `modelo_ata.pkl`, `modelo_tec.pkl`.

### 2. Bônus Tático (Pós-Processamento)
Após a previsão base da IA, aplicamos uma camada de **Inteligência Tática** baseada no contexto do próximo jogo:
*   **Força do Adversário**: Bônus/pênalti para atacantes que enfrentam defesas fracas e vice-versa.
*   **Mando de Campo**: Incremento na previsão para jogadores que atuam em casa.
*   **Odds de Apostas**: *Boost* proporcional se o time é super favorito nas casas de aposta.

### 3. Gestão de Risco e Simulação (Backtesting)
O sistema não só prevê, mas também **recomenda a melhor estratégia**:
*   **Apetite ao Risco**: Você ajusta um slider de 0 (seguro) a 2 (agressivo). O otimizador buscará times consistentes ou times com alto potencial de "mitada".
*   **Simulador de Risco**: Um botão de **Backtest** analisa as últimas 10 rodadas e informa qual nível de risco teria sido mais lucrativo, ajudando a calibrar sua estratégia para o momento atual do campeonato.

### 4. Copiloto Humano (Travas e Exclusões)
A IA sugere, mas a decisão final é sua. A interface permite:
*   **🔒 Travar Jogadores**: Obriga o sistema a escalar seus "intocáveis".
*   **🚫 Banir Jogadores**: Impede que um jogador seja escalado, mesmo com boa previsão.

---

## 📂 Estrutura de Dados

O sistema se alimenta de múltiplas fontes para garantir precisão máxima:

| Fonte | Descrição | Arquivo Local |
| :--- | :--- | :--- |
| **Histórico (2018-2023)** | Base consolidada do repositório *caRtola*. | `data/historico_jogadores.csv` |
| **Histórico (2025)** | Coletado rodada a rodada via API Oficial. | `data/historico_2025.csv` |
| **Mercado Ao Vivo** | Dados em tempo real (status, preço, scouts). | `data/rodada_atual.csv` |
| **Odds (Betting)** | Cotações atualizadas via The Odds API. | `data/odds_rodada.csv` |
| **Histórico de Odds**| Histórico acumulado das odds de 2025. | `data/historico_odds.csv` |
| **Clubes e Escudos** | Metadados dos times. | `data/clubes.json` |
| **Minha Pontuação** | Histórico pessoal para análise comparativa. | `data/historico_vini.csv` |

---

## 🚀 Como Usar

### Pré-requisitos
*   Python 3.8+
*   Bibliotecas listadas em `requirements.txt`.

### Executando o Dashboard
```bash
streamlit run cartola_project/app.py
```

### Fluxo de Operação no App
1.  **Atualizar Dados da Rodada**: Baixa os dados frescos do mercado e as Odds.
2.  **Configurar Time**:
    *   Defina seu orçamento e esquema tático.
    *   **Copiloto**: Trave ou exclua jogadores se desejar.
    *   **Inteligência**: Escolha "IA Avançada (XGBoost)".
    *   **Apetite ao Risco**: Ajuste o slider. Se estiver em dúvida, use o botão **"Simular Melhor Risco"** para uma recomendação baseada em dados.
3.  **Gerar Time Ideal**: O sistema processa, prevê e otimiza a escalação.
4.  **Analisar Resultados**:
    *   Veja a escalação na **tabela**, com o **Capitão ©️** indicado.
    *   Marque a opção **"🏟️ Ver Campinho"** para uma visualização tática.
    *   Confira o **Banco de Reservas de Luxo**.
    *   Analise o **Desempenho Recente**, que mostra quantos pontos essa exata estratégia teria feito nas últimas 3 rodadas.

---

## 🔮 Próximos Passos (Roadmap)

1.  [ ] **Gráfico Comparativo de Desempenho**: Criar um dashboard para comparar a pontuação do usuário (Vini), do modelo IA e do "Time Perfeito" (a pontuação máxima possível) ao longo do campeonato.
2.  [ ] **Algoritmo de Valorização**: Criar um modo focado em ganhar cartoletas, otimizando a previsão de variação de preço em vez de pontos.
3.  [ ] **API de Classificação Real**: Automatizar o ranking de força dos times (`RANKING_FORCA`) conectando a uma API de tabela do campeonato.
4.  [ ] **Análise de Confrontos Diretos**: Ensinar ao modelo o histórico recente de confrontos (ex: "Time A sempre perde para Time B").

---

*Desenvolvido com 🤖 IA e Paixão por Futebol.*

