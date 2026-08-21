import os
import json
import pandas as pd
from src.loader import load_data
from src.profiler import profile_data

def criar_arquivo_exemplo():
    """Cria um CSV de exemplo com algumas 'sujeiras' (nulos, duplicados)"""
    caminho = "data/exemplo/base_teste.csv"
    
    # Se o arquivo já existir, não precisa criar de novo
    if os.path.exists(caminho):
        return caminho
        
    dados = {
        "ID": [1, 2, 3, 4, 4], # ID 4 está duplicado
        "Produto": ["Notebook", "Mouse", None, "Teclado", "Teclado"], # Possui nulo
        "Valor_Total": [4500.0, 150.0, 0.0, 250.0, 250.0]
    }
    df = pd.DataFrame(dados)
    df.to_csv(caminho, index=False, sep=";")
    return caminho

def main():
    print("1. Preparando arquivo de teste...")
    caminho_arquivo = criar_arquivo_exemplo()
    
    print(f"\n2. Executando MVP 1: Carregando dados de '{caminho_arquivo}'...")
    df = load_data(caminho_arquivo)
    print("   -> Arquivo carregado com sucesso!")
    
    print("\n3. Executando MVP 2: Gerando Profiling...")
    resultado_profiling = profile_data(df)
    
    print("\n4. Resultado Estruturado:\n")
    # json.dumps formata o dicionário com indentação, facilitando a leitura
    print(json.dumps(resultado_profiling, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()