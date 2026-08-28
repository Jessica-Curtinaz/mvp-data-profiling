import pandas as pd

from src.profiler import profile_data
from src.comparator import check_required_data
from src.diagnostics import run_diagnostic


def test_diagnostic_rules():
    """
    Testa se as regras do diagnóstico
    classificam corretamente os problemas.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-03"
        ],
        "UF": [
            "SP",
            None,
            "RJ",
            "RJ"
        ],
        "Valor Total": [
            "R$ 100",
            "R$ 200",
            "R$ 300",
            "R$ 300"
        ],
        "Vendedor": [
            "Ana",
            None,
            "João",
            "João"
        ]
    })

    perfil = profile_data(df)

    mapeamento = check_required_data(
        perfil,
        "faturamento_por_regiao"
    )

    diagnostico = run_diagnostic(
        perfil,
        mapeamento
    )

    assert diagnostico["status"] == "REQUER PREPARAÇÃO"

    problemas = diagnostico["problemas"]

    assert any(
        p["codigo"] == "POSSIVEIS_DUPLICIDADES"
        for p in problemas
    )

    assert any(
        p["codigo"] == "TIPO_INADEQUADO"
        for p in problemas
    )

    assert any(
        p["dado"] == "regiao"
        and p["classificacao"] == "CRÍTICO"
        for p in problemas
    )

    assert any(
        p["dado"] == "Vendedor"
        and p["classificacao"] == "IGNORADO"
        for p in problemas
    )


def test_diagnostic_returns_finalidade():
    """
    Verifica se o identificador da finalidade
    é propagado corretamente.
    """
    df = pd.DataFrame({
        "Data Venda": ["2026-01-01"],
        "UF": ["RS"],
        "Valor Total": [100.0]
    })

    perfil = profile_data(df)

    mapeamento = check_required_data(
        perfil,
        "faturamento_por_regiao"
    )

    diagnostico = run_diagnostic(
        perfil,
        mapeamento
    )

    assert diagnostico["finalidade_id"] == "faturamento_por_regiao"
    