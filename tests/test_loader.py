import pytest

from src.loader import (
    load_data,
    UnsupportedExtensionError
)


def test_load_csv_success(tmp_path):
    """
    Testa leitura CSV com ponto e vírgula.
    """
    arquivo_teste = tmp_path / "teste.csv"

    arquivo_teste.write_text(
        "id;nome\n1;Ana\n2;João",
        encoding="utf-8"
    )

    resultado = load_data(
        str(arquivo_teste)
    )

    assert "df" in resultado
    assert "metadata" in resultado

    assert len(resultado["df"]) == 2

    assert (
        resultado["metadata"]["delimitador"]
        == ";"
    )

    assert (
        resultado["metadata"]["extensao"]
        == ".csv"
    )


def test_load_csv_comma_separator(tmp_path):
    """
    Testa detecção de CSV separado por vírgula.
    """
    arquivo_teste = tmp_path / "teste.csv"

    arquivo_teste.write_text(
        "id,nome\n1,Ana\n2,João",
        encoding="utf-8"
    )

    resultado = load_data(
        str(arquivo_teste)
    )

    assert len(resultado["df"]) == 2

    assert (
        resultado["metadata"]["delimitador"]
        == ","
    )


def test_load_unsupported_extension(tmp_path):
    """
    Testa extensão não suportada.
    """
    arquivo_teste = tmp_path / "teste.txt"

    arquivo_teste.write_text(
        "dados falsos"
    )

    with pytest.raises(
        UnsupportedExtensionError
    ):
        load_data(
            str(arquivo_teste)
        )


def test_file_not_found():
    """
    Testa arquivo inexistente.
    """
    with pytest.raises(
        FileNotFoundError
    ):
        load_data(
            "caminho/que/nao/existe.csv"
        )
        