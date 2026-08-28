import pandas as pd

from src.profiler import profile_data
from src.comparator import (
    check_required_data
)


def test_comparator_recognizes_aliases():
    """
    Verifica reconhecimento correto dos aliases.
    """
    df = pd.DataFrame({
        "Data Venda": ["2026-01-01"],
        "UF": ["RS"],
        "Valor Total": [100.0],
        "Produto": ["Notebook"]
    })

    perfil = profile_data(df)

    resultado = check_required_data(
        perfil,
        "faturamento_por_regiao"
    )

    assert resultado["status"] == "APTA"

    mapeamento = {
        item["conceito"]: item["coluna_base"]
        for item in resultado["mapeamento"]
    }

    assert mapeamento["data_venda"] == "Data Venda"
    assert mapeamento["regiao"] == "UF"
    assert mapeamento["valor_venda"] == "Valor Total"

    assert (
        "Produto"
        in resultado["dados_adicionais"]
    )


def test_comparator_missing_required_data():
    """
    Verifica comportamento quando
    falta uma coluna obrigatória.
    """
    df = pd.DataFrame({
        "UF": ["RS"],
        "Valor Total": [100]
    })

    perfil = profile_data(df)

    resultado = check_required_data(
        perfil,
        "faturamento_por_regiao"
    )

    assert resultado["status"] == "INCOMPLETA"

    data_venda = next(
        item
        for item in resultado["mapeamento"]
        if item["conceito"] == "data_venda"
    )

    assert data_venda["status"] == "NÃO encontrado"
    assert data_venda["coluna_base"] is None
    