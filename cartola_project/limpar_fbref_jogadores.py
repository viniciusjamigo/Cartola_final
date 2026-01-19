"""
Script para limpar o arquivo fbref_jogadores_serie_a.csv:
- Remove cabeçalhos duplicados
- Remove linhas de sub-cabeçalhos
- Garante que a coluna 'Clube' está preenchida
"""

import pandas as pd
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FBREF_DIR = os.path.join(DATA_DIR, "fbref")
FBREF_JOGADORES_PATH = os.path.join(FBREF_DIR, "fbref_jogadores_serie_a.csv")
FBREF_JOGADORES_LIMPO_PATH = os.path.join(FBREF_DIR, "fbref_jogadores_serie_a_limpo.csv")

def limpar_arquivo_fbref():
    """Limpa o arquivo FBref removendo cabeçalhos duplicados."""
    
    if not os.path.exists(FBREF_JOGADORES_PATH):
        print(f"ERRO: Arquivo não encontrado: {FBREF_JOGADORES_PATH}")
        return
    
    print(f"Lendo arquivo: {FBREF_JOGADORES_PATH}")
    
    # Lê o arquivo linha por linha para identificar cabeçalhos
    linhas_validas = []
    cabecalho_principal = None
    clube_atual = None
    
    with open(FBREF_JOGADORES_PATH, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    print(f"Total de linhas no arquivo: {len(linhas)}")
    
    for i, linha in enumerate(linhas):
        linha_original = linha
        linha = linha.strip()
        
        # Primeira linha válida é o cabeçalho principal
        if i == 0:
            if linha.startswith('Player,Nation,Pos,Age'):
                cabecalho_principal = linha
                # Extrai clube do cabeçalho
                partes = linha.split(',')
                for j in range(len(partes) - 2, max(0, len(partes) - 5), -1):
                    if partes[j] and partes[j] != 'Matches' and not partes[j].startswith('http') and partes[j] != 'Player':
                        clube_atual = partes[j]
                        break
                # Adiciona cabeçalho apenas uma vez
                linhas_validas.append(linha)
                continue
            elif 'Playing Time' in linha:
                # Primeira linha é sub-cabeçalho, pula
                print(f"  Pulando sub-cabeçalho na linha {i+1}")
                continue
        
        # Verifica se é a primeira linha de sub-cabeçalho (começa com vírgulas e tem "Playing Time")
        if linha.startswith(',,,') and 'Playing Time' in linha:
            print(f"  Removendo sub-cabeçalho na linha {i+1}")
            # Extrai clube desta linha
            partes = linha.split(',')
            for j in range(len(partes) - 2, max(0, len(partes) - 5), -1):
                if partes[j] and partes[j] != 'Matches' and not partes[j].startswith('http'):
                    clube_atual = partes[j]
                    break
            continue
        
        # Verifica se é a segunda linha de cabeçalho (Player, Nation, Pos, Age...)
        if linha.startswith('Player,Nation,Pos,Age'):
            print(f"  Removendo cabeçalho duplicado na linha {i+1}")
            # Extrai clube desta linha de cabeçalho
            partes = linha.split(',')
            for j in range(len(partes) - 2, max(0, len(partes) - 5), -1):
                if partes[j] and partes[j] != 'Matches' and not partes[j].startswith('http') and partes[j] != 'Player':
                    clube_atual = partes[j]
                    break
            continue
        
        # Se a linha está vazia, pula
        if not linha or linha == '':
            continue
        
        # Extrai o clube da linha (está nas últimas colunas, antes da URL)
        partes = linha.split(',')
        if len(partes) > 30:
            # Procura o clube nas últimas colunas (antes da URL)
            for j in range(len(partes) - 2, max(0, len(partes) - 5), -1):
                if partes[j] and partes[j] != 'Matches' and not partes[j].startswith('http') and partes[j] != 'Player':
                    # Verifica se parece um nome de clube (não é número, não é muito curto)
                    valor = partes[j].strip()
                    if len(valor) > 2 and not valor.replace('.', '').isdigit():
                        clube_atual = valor
                        break
        
        # Se não encontrou clube na linha, tenta extrair de outra forma
        if not clube_atual and 'Matches' in linha:
            idx_matches = linha.find('Matches,')
            if idx_matches != -1:
                resto = linha[idx_matches + 8:].split(',')
                for r in resto:
                    r = r.strip()
                    if r and not r.startswith('http') and r != 'Matches' and len(r) > 2:
                        clube_atual = r
                        break
        
        # Adiciona a linha válida com o clube atual
        if clube_atual:
            # Adiciona o clube no final da linha se não estiver lá
            if 'Matches' in linha:
                # Já tem o clube na linha
                linhas_validas.append(linha)
            else:
                # Adiciona clube e URL vazia
                linhas_validas.append(linha + f',{clube_atual},')
        else:
            # Linha sem clube identificado, adiciona mesmo assim
            linhas_validas.append(linha)
    
    print(f"Total de linhas válidas: {len(linhas_validas)}")
    
    # Salva em arquivo temporário
    arquivo_temp = FBREF_JOGADORES_PATH + '.tmp'
    with open(arquivo_temp, 'w', encoding='utf-8') as f:
        for linha in linhas_validas:
            f.write(linha + '\n')
    
    # Lê como DataFrame com tratamento de erros
    print("Lendo como DataFrame...")
    try:
        # Tenta ler com engine padrão primeiro
        df = pd.read_csv(arquivo_temp, low_memory=False, on_bad_lines='skip')
    except Exception as e:
        print(f"  AVISO: Erro ao ler CSV padrão: {e}")
        print("  Tentando com engine python (mais tolerante)...")
        # Tenta ler com engine python que é mais tolerante a erros
        try:
            df = pd.read_csv(arquivo_temp, on_bad_lines='skip', engine='python', sep=',', quotechar='"')
        except Exception as e2:
            print(f"  AVISO: Erro também com engine python: {e2}")
            print("  Tentando método manual...")
            # Método manual: lê linha por linha e constrói DataFrame
            linhas_dados = []
            with open(arquivo_temp, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
                if len(linhas) > 0:
                    cabecalho = linhas[0].strip().split(',')
                    for linha in linhas[1:]:
                        partes = linha.strip().split(',')
                        if len(partes) >= len(cabecalho) - 5:  # Tolerância para campos extras
                            # Ajusta para o tamanho do cabeçalho
                            partes = partes[:len(cabecalho)]
                            linhas_dados.append(partes)
            
            # Cria DataFrame manualmente
            if linhas_dados:
                df = pd.DataFrame(linhas_dados, columns=cabecalho[:len(linhas_dados[0])] if linhas_dados else cabecalho)
            else:
                raise Exception("Nenhum dado válido encontrado")
    
    # Remove o arquivo temporário
    os.remove(arquivo_temp)
    
    print(f"DataFrame carregado: {len(df)} linhas, {len(df.columns)} colunas")
    
    # Procura a coluna que contém o nome do clube
    # Geralmente está nas últimas colunas, antes da URL
    coluna_clube = None
    
    # Primeiro, procura por coluna chamada "Clube" ou similar
    for col in df.columns:
        if 'clube' in str(col).lower() or str(col) == 'Clube':
            coluna_clube = col
            break
    
    # Se não encontrou, procura nas últimas colunas
    if not coluna_clube:
        print("Procurando coluna de clube nas últimas colunas...")
        ultimas_colunas = df.columns[-10:].tolist()
        for col in ultimas_colunas:
            valores_unicos = df[col].dropna().unique()
            # Filtra valores que parecem nomes de clubes
            valores_texto = [str(v).strip() for v in valores_unicos 
                           if isinstance(v, str) and len(str(v).strip()) > 2 
                           and not str(v).strip().startswith('http') 
                           and str(v).strip() != 'Matches'
                           and str(v).strip() != 'Player'
                           and not str(v).strip().replace('.', '').isdigit()]
            
            # Se tem vários valores únicos que parecem nomes de clubes (entre 5 e 30 clubes)
            if 5 <= len(valores_texto) <= 30:
                coluna_clube = col
                print(f"  Encontrada coluna de clube: '{col}' com {len(valores_texto)} valores únicos")
                print(f"    Exemplos: {valores_texto[:5]}")
                break
    
    # Cria ou atualiza coluna Clube
    if coluna_clube:
        df['Clube'] = df[coluna_clube].astype(str).str.strip()
        # Remove valores inválidos
        df.loc[df['Clube'].str.startswith('http'), 'Clube'] = None
        df.loc[df['Clube'] == 'Matches', 'Clube'] = None
        df.loc[df['Clube'] == 'Player', 'Clube'] = None
        df.loc[df['Clube'] == 'nan', 'Clube'] = None
        print(f"  Coluna 'Clube' criada a partir de '{coluna_clube}'")
    else:
        print("  AVISO: Não foi possível identificar a coluna de clube automaticamente")
        print(f"  Colunas disponíveis: {list(df.columns)}")
        # Tenta criar coluna Clube vazia
        df['Clube'] = None
    
    # Remove linhas onde Player é vazio ou é o próprio cabeçalho
    if 'Player' in df.columns:
        df = df[df['Player'].notna()].copy()
        df = df[df['Player'] != 'Player'].copy()
        df = df[df['Player'] != ''].copy()
        # Remove linhas onde Player começa com vírgulas (sub-cabeçalhos)
        df = df[~df['Player'].astype(str).str.startswith(',')].copy()
    
    # Remove linhas duplicadas baseado em Player e outras colunas chave
    colunas_dup = ['Player']
    if 'Clube' in df.columns:
        colunas_dup.append('Clube')
    df = df.drop_duplicates(subset=colunas_dup, keep='first').copy()
    
    # Garante que Clube está preenchido (forward fill e backward fill)
    if 'Clube' in df.columns:
        # Remove valores inválidos antes do fill
        df.loc[df['Clube'].astype(str).str.startswith('http'), 'Clube'] = None
        df.loc[df['Clube'] == 'Matches', 'Clube'] = None
        
        # Forward fill e backward fill (sintaxe moderna)
        df['Clube'] = df['Clube'].ffill()
        df['Clube'] = df['Clube'].bfill()
    
    print(f"DataFrame final: {len(df)} linhas")
    print(f"Colunas: {list(df.columns)}")
    
    if 'Clube' in df.columns:
        print(f"\nClubes encontrados: {df['Clube'].value_counts().to_dict()}")
    
    # Salva arquivo limpo
    print(f"\nSalvando arquivo limpo: {FBREF_JOGADORES_LIMPO_PATH}")
    df.to_csv(FBREF_JOGADORES_LIMPO_PATH, index=False, encoding='utf-8-sig')
    
    # Substitui o arquivo original
    print(f"Substituindo arquivo original...")
    os.replace(FBREF_JOGADORES_LIMPO_PATH, FBREF_JOGADORES_PATH)
    
    print(f"\nSUCESSO: Arquivo limpo e salvo!")
    print(f"  - Linhas removidas: {len(linhas_validas) - len(df)}")
    print(f"  - Linhas finais: {len(df)}")
    print(f"  - Coluna 'Clube' preenchida: {'Sim' if 'Clube' in df.columns and not df['Clube'].isna().all() else 'Não'}")

if __name__ == "__main__":
    limpar_arquivo_fbref()

