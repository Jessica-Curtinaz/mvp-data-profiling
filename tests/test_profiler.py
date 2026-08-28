import pandas as pd

from src.profiler import profile_data


def test_profile_data_structure():
    """
    Valida a estrutura principal produzida pelo profiler.
    """
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Produto": ["A", "B", None]
    })

    resultado = profile_data(df)

    assert resultado["geral"]["linhas"] == 3
    assert resultado["geral"]["colunas"] == 2
    assert resultado["geral"]["duplicadas"] == 0
    assert resultado["geral"]["base_vazia"] is False

    coluna_produto = next(
        col
        for col in resultado["colunas"]
        if col["nome"] == "Produto"
    )

    assert coluna_produto["nulos"] == 1
    assert coluna_produto["proporcao_nulos"] == round(1 / 3, 4)
    assert coluna_produto["preenchidos"] == 2


def test_profile_data_text_type():
    """
    Verifica classificação semântica de tipos.
    """
    df = pd.DataFrame({
        "Nome": ["Ana", "João"]
    })

    resultado = profile_data(df)

    coluna = resultado["colunas"][0]

    assert coluna["categoria_tipo"] in [
        "texto",
        "objeto"
    ]


def test_profile_data_empty_strings():
    """
    Verifica contabilização de strings vazias.
    """
    df = pd.DataFrame({
        "Cidade": ["Porto Alegre", "", "   ", None]
    })

    resultado = profile_data(df)

    coluna = resultado["colunas"][0]

    assert coluna["nulos"] == 1
    assert coluna["vazios"] == 2
    assert coluna["ausentes_total"] == 3