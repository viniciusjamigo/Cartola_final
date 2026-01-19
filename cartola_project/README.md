# ⚽ Cartola FC Pro - Otimizador de Escalação

Bem-vindo ao Cartola FC Pro, um projeto completo em Python para análise e previsão de pontuações de jogadores do Cartola FC, com o objetivo final de recomendar automaticamente uma escalação ideal para cada rodada.

## 🎯 Objetivo

O sistema foi construído para coletar, tratar, analisar e prever as pontuações dos jogadores, e a partir dessas previsões, montar o time ideal da rodada, respeitando restrições de orçamento e formação tática.

## ✨ Funcionalidades

- **Coleta de Dados Automática**: Busca os dados mais recentes do mercado de jogadores diretamente da API do Cartola FC.
- **Pré-processamento e Análise**: Limpa os dados e prepara para a modelagem.
- **Otimização de Escalação**: Utiliza programação linear para encontrar o time que maximiza a pontuação prevista, respeitando:
  - Orçamento total.
  - Esquema tático selecionado.
  - Limite de 5 jogadores por clube.
- **Dashboard Interativo**: Uma interface amigável construída com Streamlit para controlar o processo e visualizar os resultados.

## 🔑 Configuração da API de Odds

Para que o sistema consiga prever o favoritismo dos times de forma precisa, ele utiliza dados de casas de apostas em tempo real.

1.  **Crie uma conta gratuita** em [The Odds API](https://the-odds-api.com/).
2.  Após confirmar seu e-mail, você receberá uma **API Key**.
3.  Ao abrir o dashboard do projeto, você verá um campo chamado **"Sua Chave da The Odds API"** na barra lateral.
4.  Cole sua chave lá para habilitar a atualização de odds.

---

## 🖥️ Como Usar o Dashboard

O sistema é dividido em 4 abas principais, cada uma com um propósito específico:

### 1. 📋 Escalar Time
É onde a "mágica" acontece. Siga esta ordem:
*   **"1. Atualizar Dados da Rodada"**: Baixa os dados mais recentes do Cartola e as odds (se a chave estiver preenchida).
*   **"2. Gerar Time Ideal"**: O otimizador calcula a melhor combinação de jogadores baseada na inteligência escolhida.
*   **Copiloto (Manual)**: Você pode forçar a escalação de jogadores específicos (Travas) ou banir jogadores que não quer de jeito nenhum.

### 2. 📊 Análise de Performance
Aqui você pode ver o quão bem a IA está performando em comparação com:
*   **Você (Vini)**: Compara com suas pontuações reais.
*   **Time Perfeito**: O máximo de pontos que alguém poderia ter feito na rodada.
*   **Diferentes IAs**: Compara modelos com e sem a inteligência de mando de campo.

### 3. 📈 Análises Estatísticas
Inspirada em plataformas como o BIA Score, esta aba traz:
*   **Análise de Goleiros e Atacantes**: Quem tem mais chance de SG ou Gol.
*   **Recorrência**: Jogadores que mantém constância de pontos.
*   **Cartola + FBref**: Cruzamento de dados do Cartola com estatísticas avançadas (xG, xA) do futebol mundial.

### 4. 📉 Dashboard Analítico
Visualizações gráficas sobre a saúde do seu time e tendências do campeonato.

### 🛠️ Ferramentas Avançadas (Barra Lateral)
Para usuários que querem ir além:
*   **"Treinar Novo Modelo Preditivo"**: Atualiza o cérebro da IA com os dados mais recentes de todas as rodadas jogadas até hoje.
*   **"Simular Melhor Risco (Backtest)"**: Testa diferentes níveis de "ousadia" da IA nas últimas 10 rodadas para ver qual teria dado mais pontos.
*   **"🧹 Limpar Cache"**: Resolve problemas caso os dados pareçam travados ou desatualizados.

---

## 🛠️ Tecnologias Utilizadas

- **Análise de Dados**: `pandas`, `numpy`
- **Machine Learning**: `scikit-learn`, `xgboost`
- **Otimização**: `pulp`
- **Dashboard**: `streamlit`
- **Coleta de Dados**: `requests`

---

## 🚀 Como Executar o Projeto Localmente

Siga os passos abaixo para rodar a aplicação no seu computador.

### 1. Pré-requisitos

- Python 3.8 ou superior instalado.
- `pip` (gerenciador de pacotes do Python).

### 2. Clone o Repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd cartola_project
```

### 3. Crie um Ambiente Virtual (Recomendado)

É uma boa prática isolar as dependências do projeto.

```bash
# Criar o ambiente
python -m venv venv

# Ativar o ambiente
# No Windows
venv\Scripts\activate
# No macOS/Linux
source venv/bin/activate
```

### 4. Instale as Dependências

Todas as bibliotecas necessárias estão listadas no arquivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 5. Execute a Aplicação

Com as dependências instaladas, inicie o dashboard Streamlit.

```bash
streamlit run app.py
```

Após executar o comando, uma nova aba abrirá no seu navegador com a aplicação rodando.

## 📈 Próximos Passos (Roadmap)

- [ ] Coletar e consolidar dados históricos para treinar um modelo de previsão preciso.
- [ ] Implementar a etapa de treinamento e previsão no pipeline.
- [ ] Adicionar mais features de engenharia (força do adversário, fator casa/fora, etc.).
- [ ] Criar notebooks para análise exploratória e testes.
- [ ] Melhorar a interface com mais gráficos e filtros.
- [ ] Empacotar o projeto com Docker para facilitar o deploy.
