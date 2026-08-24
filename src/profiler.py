import pandas as pd

def profile_data(df: pd.DataFrame) -> dict:
    """
    Realiza o profiling estrutural de um DataFrame, retornando
    estatísticas básicas sobre a base e suas colunas.
    Não altera os dados originais.
    """
    qtd_linhas = len(df)
    qtd_colunas = len(df.columns)
    
    # df.duplicated().sum() retorna um numpy int, convertemos para int nativo
    qtd_duplicadas = int(df.duplicated().sum())
    
    resultado = {
        "geral": {
            "linhas": qtd_linhas,
            "colunas": qtd_colunas,
            "duplicadas": qtd_duplicadas
        },
        "colunas": []
    }
    
    for coluna in df.columns:
        # Contagens básicas
        nulos = int(df[coluna].isnull().sum())
        preenchidos = qtd_linhas - nulos
        
        # Proteção contra divisão por zero em DataFrames vazios
        proporcao_nulos = 0.0
        if qtd_linhas > 0:
            proporcao_nulos = round(nulos / qtd_linhas, 4)
            
        valores_distintos = int(df[coluna].nunique())
        
        info_coluna = {
            "nome": str(coluna),
            "tipo": str(df[coluna].dtype),
            "total": qtd_linhas,
            "preenchidos": preenchidos,
            "nulos": nulos,
            "proporcao_nulos": proporcao_nulos,
            "valores_distintos": valores_distintos
        }
        
        resultado["colunas"].append(info_coluna)
        
    return resultado