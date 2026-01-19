import sys
import os

# Adiciona o diretório do projeto ao sys.path para garantir que as importações funcionem
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(project_root)

# Adiciona o diretório pai também, caso necessário
parent_dir = os.path.abspath(os.path.join(project_root, '..'))
sys.path.append(parent_dir)

try:
    from cartola_project.utils.modelagem import treinar_modelo
except ImportError:
    # Tenta importar sem o prefixo cartola_project se estivermos dentro dele
    try:
        from utils.modelagem import treinar_modelo
    except ImportError:
        print("Erro crítico de importação. Verifique a estrutura de diretórios.")
        sys.exit(1)

if __name__ == "__main__":
    print("=== INICIANDO RETREINAMENTO DOS MODELOS XGBOOST (MODO PRODUÇÃO) ===")
    print("Este processo irá atualizar os modelos usando TODO o histórico disponível (2022-2025).")
    print("Inclui as novas features de força do próprio time e FBRef.")
    
    # Treinar com tudo para uso real na próxima rodada
    sucesso = treinar_modelo()
    
    if sucesso:
        print("\n=== SUCESSO: Modelos retreinados! ===")
        print("Agora a 'IA Nova' deve se comportar diferente da 'IA Legado'.")
    else:
        print("\n=== FALHA: Ocorreu um erro durante o treinamento. Verifique os logs acima. ===")

