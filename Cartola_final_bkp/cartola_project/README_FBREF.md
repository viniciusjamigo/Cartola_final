# 📊 Coleta de Dados do FBref

Script para coletar dados do FBref usando a biblioteca `soccerdata`.

## 🚀 Instalação

Primeiro, instale a biblioteca `soccerdata`:

```bash
pip install soccerdata
```

Ou adicione ao `requirements.txt` e instale tudo:

```bash
pip install -r requirements.txt
```

## 📋 O que o script coleta

### Dados dos Clubes:
- Estatísticas dos times da Série A
- Salvo em: `data/fbref/fbref_estatisticas_times.csv`

### Dados dos Jogadores:
- Estatísticas padrão (gols, assistências, etc.)
- Estatísticas avançadas (xG, xA, finalizações)
- Estatísticas de passes
- Salvo em: `data/fbref/fbref_jogadores_serie_a.csv`

## 🎯 Como usar

### Opção 1: Coletar tudo (clubes + jogadores)
```bash
cd cartola_project
python coletar_fbref.py
```

### Opção 2: Apenas clubes
```bash
python coletar_fbref.py --apenas-clubes
```

### Opção 3: Apenas jogadores
```bash
python coletar_fbref.py --apenas-jogadores
```

### Opção 4: Especificar ano
```bash
python coletar_fbref.py --ano 2024
```

## ⚠️ Importante

1. **Rate Limiting**: O FBref permite apenas 1 requisição a cada 6 segundos
   - O script respeita automaticamente essa limitação
   - O processo pode levar vários minutos

2. **Códigos de Liga**: O script tenta automaticamente diferentes códigos:
   - `BRA-SerieA` (padrão)
   - `BRA1`
   - `BRA-Serie-A`
   - `Brasileirão`

3. **Erros Comuns**:
   - Se nenhum código funcionar, verifique manualmente no FBref
   - Certifique-se de que a temporada existe no FBref
   - Verifique sua conexão com a internet

## 📁 Estrutura de Arquivos

Após a execução, os dados serão salvos em:

```
cartola_project/
└── data/
    └── fbref/
        ├── fbref_estatisticas_times.csv
        └── fbref_jogadores_serie_a.csv
```

## 🔄 Integração com o Sistema

Os dados coletados podem ser usados para:
- Enriquecer análises de participações
- Melhorar aproximações de xG/xA
- Adicionar dados de escanteios (se disponíveis)
- Comparar com dados do Cartola FC

## 📝 Exemplo de Uso Programático

```python
from coletar_fbref import coletar_dados_completos

# Coleta dados de 2025
df_clubes, df_jogadores = coletar_dados_completos(ano=2025)

if df_clubes is not None:
    print(f"Clubes coletados: {len(df_clubes)}")
    
if df_jogadores is not None:
    print(f"Jogadores coletados: {len(df_jogadores)}")
```

## 🐛 Troubleshooting

### Erro: "soccerdata não está disponível"
**Solução**: Instale a biblioteca
```bash
pip install soccerdata
```

### Erro: "Nenhum dado encontrado"
**Possíveis causas**:
- Código da liga incorreto
- Temporada não existe no FBref
- Dados ainda não disponíveis para o ano especificado

**Solução**: Verifique manualmente no site do FBref qual é o código correto da liga.

### Erro: "Rate limit exceeded"
**Solução**: O script já respeita rate limiting, mas se ainda assim ocorrer:
- Aguarde alguns minutos antes de tentar novamente
- Reduza a frequência de execução

## 📚 Referências

- [soccerdata Documentation](https://soccerdata.readthedocs.io/)
- [FBref Website](https://fbref.com/)
- [FBref - Série A do Brasil](https://fbref.com/en/comps/24/Serie-A-Stats)




