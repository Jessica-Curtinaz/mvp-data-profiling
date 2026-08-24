import pytest
import pandas as pd
from src.loader import load_data, UnsupportedExtensionError

def test_load_csv_success(tmp_path):
    """Testa se o loader lê um CSV corretamente e retorna os metadados."""
    # Cria um CSV temporário
    arquivo_teste = tmp_path / "teste_valido.csv"
    arquivo_teste.write_text("id;nome\n1;Ana\n2;João", encoding="utf-8")
    
    resultado = load_data(str(arquivo_teste))
    
    # Verifica a estrutura do retorno
    assert "df" in resultado
    assert "metadata" in resultado
    assert len(resultado["df"]) == 2
    assert resultado["metadata"]["delimitador"] == ";"

def test_load_unsupported_extension(tmp_path):
    """Testa se o sistema barra extensões não suportadas."""
    arquivo_teste = tmp_path / "teste.txt"
    arquivo_teste.write_text("dados falsos")
    
    # Verifica se a exceção correta é levantada
    with pytest.raises(UnsupportedExtensionError):
        load_data(str(arquivo_teste))

def test_file_not_found():
    """Testa o comportamento com arquivo inexistente."""
    with pytest.raises(FileNotFoundError):
        load_data("caminho/que/nao/existe.csv")