import pandas as pd

from src.profiler import profile_data
from src.comparator import check_required_data
from src.diagnostics import run_diagnostic
from src.preparer import prepare_data


FINALIDADE_ID = "faturamento_por_regiao"


def _executar_ate_preparacao(
    df: pd.DataFrame,
) -> dict:
    """
    Executa o pipeline mínimo necessário para testar
    o preparador.
    """
    perfil = profile_data(df)

    mapeamento = check_required_data(
        perfil,
        FINALIDADE_ID,
    )

    diagnostico = run_diagnostic(
        perfil,
        mapeamento,
    )

    return prepare_data(
        df,
        diagnostico,
        mapeamento,
    )


def test_prepare_data_does_not_change_original():
    """
    Verifica que a preparação não altera o DataFrame original.
    """
    df = pd.DataFrame({
        "Data Venda": ["01/01/2026"],
        "UF": [" rs "],
        "Valor Total": ["R$ 100,00"],
    })

    original = df.copy(deep=True)

    _executar_ate_preparacao(df)

    pd.testing.assert_frame_equal(
        df,
        original,
    )


def test_prepare_data_preserves_rows():
    """
    Verifica que nenhuma linha é removida automaticamente.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
        ],
        "UF": [
            "RS",
            None,
        ],
        "Valor Total": [
            "R$ 100,00",
            "R$ 200,00",
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert len(base_preparada) == len(df)
    assert (
        preparacao["resumo"]["linhas_removidas"]
        == 0
    )


def test_prepare_data_fills_missing_region():
    """
    Verifica o preenchimento categórico seguro.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
            "03/01/2026",
        ],
        "UF": [
            "RS",
            None,
            "   ",
        ],
        "Valor Total": [
            100.0,
            200.0,
            300.0,
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert (
        base_preparada["UF"].isna().sum()
        == 0
    )

    assert (
        list(base_preparada["UF"])
        == [
            "RS",
            "NÃO INFORMADO",
            "NÃO INFORMADO",
        ]
    )


def test_prepare_data_trims_and_uppercases_region():
    """
    Verifica remoção de espaços e padronização categórica.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
        ],
        "UF": [
            " rs ",
            "sp",
        ],
        "Valor Total": [
            100.0,
            200.0,
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert list(
        base_preparada["UF"]
    ) == [
        "RS",
        "SP",
    ]


def test_prepare_data_converts_currency_to_numeric():
    """
    Verifica conversão de valores monetários brasileiros.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
        ],
        "UF": [
            "RS",
            "SP",
        ],
        "Valor Total": [
            "R$ 1.234,56",
            "R$ 200,00",
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert pd.api.types.is_numeric_dtype(
        base_preparada["Valor Total"]
    )

    assert (
        base_preparada["Valor Total"].iloc[0]
        == 1234.56
    )

    assert (
        base_preparada["Valor Total"].iloc[1]
        == 200.0
    )


def test_prepare_data_records_invalid_numbers():
    """
    Verifica que valores não convertíveis sejam registrados
    e não sejam inventados.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
        ],
        "UF": [
            "RS",
            "SP",
        ],
        "Valor Total": [
            "R$ 100,00",
            "valor desconhecido",
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert pd.isna(
        base_preparada[
            "Valor Total"
        ].iloc[1]
    )

    conversao = next(
        item
        for item in preparacao[
            "transformacoes"
        ]
        if item["acao"]
        == "converter_numerico"
    )

    assert (
        conversao["valores_invalidos"]
        == 1
    )

    assert (
        conversao["status"]
        == "APLICADA COM PENDÊNCIAS"
    )


def test_prepare_data_standardizes_dates():
    """
    Verifica conversão e padronização de datas.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "2026-01-02",
        ],
        "UF": [
            "RS",
            "SP",
        ],
        "Valor Total": [
            100.0,
            200.0,
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    base_preparada = preparacao["df"]

    assert pd.api.types.is_datetime64_any_dtype(
        base_preparada["Data Venda"]
    )


def test_prepare_data_returns_traceability_log():
    """
    Verifica a rastreabilidade problema-decisão-transformação.
    """
    df = pd.DataFrame({
        "Data Venda": [
            "01/01/2026",
            "02/01/2026",
        ],
        "UF": [
            "RS",
            None,
        ],
        "Valor Total": [
            "R$ 100,00",
            "R$ 200,00",
        ],
    })

    preparacao = _executar_ate_preparacao(df)

    assert "transformacoes" in preparacao
    assert "problemas_nao_tratados" in preparacao
    assert "resumo" in preparacao

    assert all(
        "problema_origem" in item
        and "acao" in item
        and "status" in item
        and "registros_afetados" in item
        for item in preparacao[
            "transformacoes"
        ]
    )