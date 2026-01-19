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
