import csv
from pathlib import Path
from typing import Optional, Union

import pandas as pd


# ==================================================
# EXCEÇÕES CUSTOMIZADAS
# ==================================================

class UnsupportedExtensionError(ValueError):
    """
    Exceção gerada quando a extensão do arquivo
    não é suportada pelo sistema.
    """

    pass


class EmptyFileError(ValueError):
    """
    Exceção gerada quando o arquivo informado está vazio.
    """

    pass


class DataLoadError(ValueError):
    """
    Exceção gerada quando o arquivo existe e possui uma
    extensão válida, mas seu conteúdo não pode ser carregado.
    """

    pass


# ==================================================
# CONFIGURAÇÕES
# ==================================================

ENCODINGS_CSV = [
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin1",
]

DELIMITADORES_CANDIDATOS = [
    ",",
    ";",
    "\t",
    "|",
]

TAMANHO_AMOSTRA = 4096


# ==================================================
# FUNÇÕES AUXILIARES PARA CSV
# ==================================================

def _read_sample(
    file_path: Path,
    encoding: str,
) -> str:
    """
    Lê uma amostra do arquivo para identificação
    do delimitador.
    """
    with file_path.open(
        mode="r",
        encoding=encoding,
        newline="",
    ) as arquivo:
        return arquivo.read(TAMANHO_AMOSTRA)


def _detect_delimiter(sample: str) -> str:
    """
    Tenta identificar o delimitador do CSV.

    Caso o csv.Sniffer não consiga detectar,
    utiliza a frequência dos delimitadores candidatos.
    """
    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=DELIMITADORES_CANDIDATOS,
        )
        return dialect.delimiter

    except csv.Error:
        primeira_linha = (
            sample.splitlines()[0]
            if sample.splitlines()
            else ""
        )

        frequencias = {
            delimitador: primeira_linha.count(
                delimitador
            )
            for delimitador in DELIMITADORES_CANDIDATOS
        }

        delimitador_mais_frequente = max(
            frequencias,
            key=frequencias.get,
        )

        if frequencias[
            delimitador_mais_frequente
        ] > 0:
            return delimitador_mais_frequente

        return ","


def _try_alternative_delimiters(
    file_path: Path,
    encoding: str,
    sample: str,
    detected_delimiter: str,
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    """
    Quando a leitura gera apenas uma coluna, tenta outros
    delimitadores encontrados na amostra.
    """
    if len(dataframe.columns) != 1:
        return dataframe, detected_delimiter

    primeira_linha = (
        sample.splitlines()[0]
        if sample.splitlines()
        else ""
    )

    candidatos = sorted(
        DELIMITADORES_CANDIDATOS,
        key=lambda separador: primeira_linha.count(
            separador
        ),
        reverse=True,
    )

    for delimitador in candidatos:
        if delimitador == detected_delimiter:
            continue

        if delimitador not in primeira_linha:
            continue

        tentativa = pd.read_csv(
            file_path,
            sep=delimitador,
            encoding=encoding,
        )

        if len(tentativa.columns) > len(
            dataframe.columns
        ):
            return tentativa, delimitador

    return dataframe, detected_delimiter


def _load_csv(file_path: Path) -> dict:
    """
    Carrega um arquivo CSV, tentando identificar:
    - Encoding;
    - Delimitador;
    - Estrutura de colunas.

    Retorna o DataFrame e os metadados de leitura.
    """
    erros_encontrados = []

    for encoding in ENCODINGS_CSV:
        try:
            amostra = _read_sample(
                file_path,
                encoding,
            )

            if not amostra.strip():
                raise EmptyFileError(
                    f"O arquivo '{file_path}' está vazio."
                )

            delimitador = _detect_delimiter(
                amostra
            )

            df = pd.read_csv(
                file_path,
                sep=delimitador,
                encoding=encoding,
            )

            df, delimitador = (
                _try_alternative_delimiters(
                    file_path=file_path,
                    encoding=encoding,
                    sample=amostra,
                    detected_delimiter=delimitador,
                    dataframe=df,
                )
            )

            return {
                "df": df,
                "metadata": {
                    "nome_arquivo": file_path.name,
                    "caminho": str(file_path),
                    "extensao": ".csv",
                    "encoding": encoding,
                    "delimitador": delimitador,
                    "planilha": "n/a",
                    "linhas_carregadas": int(len(df)),
                    "colunas_carregadas": int(
                        len(df.columns)
                    ),
                },
            }

        except UnicodeDecodeError as erro:
            erros_encontrados.append(
                f"{encoding}: encoding incompatível"
            )
            continue

        except pd.errors.EmptyDataError as erro:
            raise EmptyFileError(
                f"O arquivo '{file_path}' não contém "
                "dados tabulares."
            ) from erro

        except pd.errors.ParserError as erro:
            erros_encontrados.append(
                f"{encoding}: erro de estrutura CSV "
                f"({erro})"
            )
            continue

        except EmptyFileError:
            raise

        except OSError as erro:
            raise DataLoadError(
                f"Não foi possível acessar o arquivo "
                f"'{file_path}': {erro}"
            ) from erro

    detalhes = "; ".join(erros_encontrados)

    raise DataLoadError(
        f"Não foi possível ler o arquivo '{file_path}'. "
        f"Encodings tentados: {ENCODINGS_CSV}. "
        f"Detalhes: {detalhes}"
    )


# ==================================================
# FUNÇÃO AUXILIAR PARA EXCEL
# ==================================================

def _load_excel(
    file_path: Path,
    sheet_name: Optional[Union[str, int]] = 0,
) -> dict:
    """
    Carrega uma planilha de um arquivo XLSX.
    """
    try:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
        )

        if not isinstance(df, pd.DataFrame):
            raise DataLoadError(
                "A leitura retornou múltiplas planilhas. "
                "Informe uma planilha específica."
            )

        return {
            "df": df,
            "metadata": {
                "nome_arquivo": file_path.name,
                "caminho": str(file_path),
                "extensao": ".xlsx",
                "encoding": "n/a",
                "delimitador": "n/a",
                "planilha": sheet_name,
                "linhas_carregadas": int(len(df)),
                "colunas_carregadas": int(
                    len(df.columns)
                ),
            },
        }

    except ValueError as erro:
        raise DataLoadError(
            f"Não foi possível ler a planilha "
            f"'{sheet_name}' do arquivo '{file_path}': "
            f"{erro}"
        ) from erro

    except (OSError, ImportError) as erro:
        raise DataLoadError(
            f"Não foi possível carregar o arquivo Excel "
            f"'{file_path}': {erro}"
        ) from erro


# ==================================================
# FUNÇÃO PÚBLICA DE CARREGAMENTO
# ==================================================

def load_data(
    file_path: str,
    sheet_name: Optional[Union[str, int]] = 0,
) -> dict:
    """
    Carrega arquivos de dados nos formatos CSV ou XLSX.

    Parâmetros:
        file_path:
            Caminho do arquivo.

        sheet_name:
            Nome ou posição da planilha para arquivos XLSX.
            O valor padrão 0 seleciona a primeira planilha.

    Retorno:
        {
            "df": pandas.DataFrame,
            "metadata": {...}
        }
    """
    if not isinstance(file_path, str):
        raise TypeError(
            "O caminho do arquivo deve ser uma string."
        )

    if not file_path.strip():
        raise ValueError(
            "O caminho do arquivo não pode estar vazio."
        )

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Erro: o arquivo '{file_path}' "
            "não foi encontrado."
        )

    if not path.is_file():
        raise ValueError(
            f"O caminho '{file_path}' não representa "
            "um arquivo."
        )

    extensao = path.suffix.lower()

    if extensao == ".csv":
        return _load_csv(path)

    if extensao == ".xlsx":
        return _load_excel(
            path,
            sheet_name=sheet_name,
        )

    raise UnsupportedExtensionError(
        f"Extensão '{extensao}' não suportada. "
        "Utilize apenas arquivos .csv ou .xlsx."
    )