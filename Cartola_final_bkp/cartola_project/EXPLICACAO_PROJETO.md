# 📄 Explicação Detalhada do Projeto Cartola FC Pro

Este documento detalha o funcionamento de cada componente do sistema `Cartola FC Pro`, explicando o fluxo de dados desde a coleta até a recomendação da escalação ideal.

---

## ⛓️ Fluxo de Funcionamento dos Scripts

O sistema é modularizado em vários scripts, cada um com uma responsabilidade clara. A execução é orquestrada pelo dashboard `app.py`.

### 1. `utils/coleta_dados.py`

- **O que faz?**: É o ponto de partida do nosso fluxo. Este script é responsável por se conectar à API pública do Cartola FC e baixar os dados brutos do mercado de jogadores para a rodada atual.
- **Como funciona?**:
  - Utiliza a biblioteca `requests` para fazer uma chamada `GET` à URL do mercado.
  - Recebe os dados em formato JSON.
  - Utiliza a biblioteca `pandas` para processar esse JSON, extraindo informações relevantes de cada jogador (nome, posição, clube, preço, pontuação média, status, etc.).
  - Salva o resultado em um arquivo `rodada_atual.csv` dentro da pasta `data/`.
- **Quando é executado?**: É acionado quando o usuário clica no botão **"1. Atualizar Dados da Rodada"** no dashboard.

### 2. `utils/preprocessamento.py`

- **O que faz?**: Prepara os dados brutos para as próximas etapas, realizando limpeza e criando novas informações (engenharia de features).
- **Como funciona?**:
  - Carrega o arquivo `rodada_atual.csv`.
  - **Limpeza**: Filtra os jogadores, mantendo apenas aqueles com status "Provável", pois são os que têm maior chance de jogar.
  - **Engenharia de Features**: Cria uma coluna `custo_beneficio`, que é a `media_num` dividida pelo `preco_num`. Isso ajuda a identificar jogadores que pontuam bem e custam pouco.
  - Salva o DataFrame processado em um novo arquivo, `rodada_atual_processada.csv`.
- **Quando é executado?**: É a primeira etapa acionada pelo botão **"2. Gerar Time Ideal"**.

### 3. `utils/modelagem.py` (Estrutura para o Futuro)

- **O que faz?**: Contém a lógica de Machine Learning para prever a pontuação de cada jogador na rodada.
- **Como funciona (atualmente)?**:
  - A função `treinar_modelo()` está preparada para carregar um dataset histórico (`historico_jogadores.csv`), treinar um modelo (`XGBoost`) e salvá-lo como `modelo_previsao.pkl`. **Esta parte ainda precisa dos dados históricos para ser funcional.**
  - A função `prever_pontuacao()` carrega o modelo salvo e o utiliza para prever a pontuação dos jogadores no arquivo `rodada_atual_processada.csv`, criando a coluna `pontuacao_prevista`.
- **Quando é executado?**: Seria a segunda etapa do botão "Gerar Time Ideal". **Atualmente, como não temos um modelo treinado, o app usa a média de pontos do jogador como um substituto para a previsão.**

### 4. `utils/otimizador.py`

- **O que faz?**: É o cérebro do projeto. Usa programação linear para resolver o quebra-cabeça de montar o melhor time possível.
- **Como funciona?**:
  - Utiliza a biblioteca `pulp`.
  - **Objetivo**: Maximizar a soma da `pontuacao_prevista` de todos os jogadores escolhidos.
  - **Restrições (Regras do Jogo)**:
    1.  O custo total do time não pode ultrapassar o orçamento definido (ex: 100 cartoletas).
    2.  O número de jogadores em cada posição deve obedecer ao esquema tático escolhido (ex: 4 zagueiros, 3 meias, 3 atacantes para um 4-3-3).
    3.  O número máximo de jogadores de um mesmo clube é limitado a 5.
  - O algoritmo encontra a combinação de jogadores que atende a todas as regras e resulta na maior pontuação total possível.
- **Quando é executado?**: É a terceira e última etapa do pipeline do botão "Gerar Time Ideal".

### 5. `app.py`

- **O que faz?**: É a interface do usuário final. Ele junta todos os scripts anteriores em um fluxo lógico e visual.
- **Como funciona?**:
  - Utiliza a biblioteca `streamlit` para criar o dashboard web.
  - Cria os botões, sliders e caixas de seleção que permitem ao usuário interagir com o sistema.
  - Orquestra a chamada das funções: `coletar_dados_rodada_atual()`, `preprocessar_dados_rodada()`, `prever_pontuacao()` e `otimizar_escalacao()`.
  - Exibe os resultados (a escalação ideal, pontuação, custo) de forma clara e organizada.

---

## 📈 Possíveis Melhorias para Aumentar a Precisão

Para evoluir o projeto e obter previsões ainda melhores, podemos focar nas seguintes áreas:

### 1. Coleta e Uso de Dados Históricos
A melhoria mais impactante. Sem dados históricos, o modelo não pode aprender padrões.
- **Ação**: Criar um script para buscar resultados de rodadas e temporadas passadas do Cartola FC. Existem APIs não-oficiais e datasets no Kaggle que podem ser utilizados. O ideal é ter scout por scout de cada jogador em cada partida.

### 2. Engenharia de Features Avançada
Criar variáveis mais inteligentes para que o modelo possa tomar melhores decisões.
- **Força do Adversário**: Criar um índice de força para cada time, baseado na sua posição na tabela do campeonato. Jogadores que enfrentam times mais fracos tendem a pontuar mais.
- **Fator Casa/Fora**: Criar uma variável que indica se o jogador jogará em casa ou fora. Jogadores da casa costumam ter um desempenho melhor.
- **Desempenho Recente (Momentum)**: Calcular a média de pontos das últimas 3 ou 5 rodadas para capturar a "fase" do jogador.
- **Análise de Confronto**: Verificar o histórico de desempenho de um jogador ou time contra o adversário da rodada.
- **Dados de Scouts**: Em vez de usar apenas a pontuação final, usar os scouts individuais (desarmes, finalizações, assistências, gols) como features.

### 3. Modelagem de Machine Learning
Aprimorar a forma como o modelo é treinado e utilizado.
- **Modelos por Posição**: Em vez de um único modelo para todos, criar modelos especialistas: um para prever pontos de atacantes, outro para zagueiros, e assim por diante, pois os scouts que geram pontos são diferentes para cada posição.
- **Testar Outros Algoritmos**: Comparar o desempenho do `XGBoost` com outros modelos robustos, como `LightGBM`, `CatBoost` ou `RandomForest`.
- **Otimização de Hiperparâmetros**: Usar técnicas como `GridSearchCV` ou `RandomizedSearchCV` para encontrar a melhor combinação de parâmetros para o modelo, aumentando sua precisão.

### 4. Melhorias no Otimizador
Adicionar mais flexibilidade e inteligência à seleção do time.
- **"Cravar" Jogadores**: Permitir que o usuário force a inclusão de um ou mais jogadores na escalação final.
- **Diversificação de Jogadores**: Adicionar uma restrição para evitar a concentração de jogadores de poucos times, buscando um time mais diversificado e menos arriscado.
- **Otimização de Banco de Reservas**: Expandir o otimizador para escalar também os 4 jogadores do banco de reservas.
