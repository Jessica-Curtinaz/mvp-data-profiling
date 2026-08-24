import pandas as pd
from src.profiler import profile_data

def test_profile_data_structure():
    """Testa se a extração de métricas estruturais está correta."""
    # Cria um DataFrame simulado
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Produto": ["A", "B", None], # 1 nulo
    })
    
    resultado = profile_data(df)
    
    # Validações gerais
    assert resultado["geral"]["linhas"] == 3
    assert resultado["geral"]["colunas"] == 2
    
    # Validação de coluna específica
    coluna_produto = next(col for col in resultado["colunas"] if col["nome"] == "Produto")
    assert coluna_produto["nulos"] == 1
    assert coluna_produto["proporcao_nulos"] == round(1/3, 4)
    assert coluna_produto["preenchidos"] == 2