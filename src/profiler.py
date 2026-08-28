from typing import Any

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def _classificar_tipo(serie: pd.Series) -> str:
    """
    Classifica o dtype técnico do pandas em uma categoria
    mais adequada para as regras de diagnóstico.

    Categorias:
    - booleano
    - numerico
    - data
    - texto
    - objeto
    """
    if is_bool_dtype(serie):
        return "booleano"

    if is_numeric_dtype(serie):
        return "numerico"

    if is_datetime64_any_dtype(serie):
        return "data"

    if is_string_dtype(serie):
        return "texto"

    return "objeto"


def _contar_textos_vazios(serie: pd.Series) -> int:
    """
    Conta strings vazias ou compostas somente por espaços.

    Valores nulos do pandas não são contabilizados aqui,
    pois são medidos separadamente.
    """
    if not (
        is_string_dtype(serie)
        or serie.dtype == "object"
    ):
        return 0

    valores_nao_nulos = serie[serie.notna()]

    if valores_nao_nulos.empty:
        return 0

    textos = valores_nao_nulos.astype("string")

    return int(
        textos.str.strip().eq("").sum()
    )

"""
def _is_serializable_scalar(value: Any) -> bool:
    
    Verifica se um valor simples pode ser apresentado
    diretamente em saídas estruturadas.

    Função reservada para futuras métricas do profiling.
    
    return isinstance(
        value,
        (str, int, float, bool, type(None)),
    )
"""

# ==================================================
# MOTOR DE PROFILING
# ==================================================

def profile_data(df: pd.DataFrame) -> dict:
    """
    Realiza o profiling estrutural de um DataFrame.

    Métricas gerais:
    - Quantidade de linhas;
    - Quantidade de colunas;
    - Linhas integralmente duplicadas;
    - Indicação de base vazia.

    Métricas por coluna:
    - Nome;
    - Dtype do pandas;
    - Categoria de tipo;
    - Total de registros;
    - Valores preenchidos;
    - Nulos;
    - Textos vazios;
    - Ausências totais;
    - Proporções de ausência;
    - Valores distintos;
    - Indicação de coluna completamente vazia.

    A função não altera o DataFrame original.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "O parâmetro 'df' deve ser um pandas.DataFrame."
        )

    qtd_linhas = int(len(df))
    qtd_colunas = int(len(df.columns))
    qtd_duplicadas = int(df.duplicated().sum())

    resultado = {
        "geral": {
            "linhas": qtd_linhas,
            "colunas": qtd_colunas,
            "duplicadas": qtd_duplicadas,
            "base_vazia": qtd_linhas == 0,
        },
        "colunas": [],
    }

    for coluna in df.columns:
        serie = df[coluna]

        nulos = int(serie.isna().sum())
        vazios = _contar_textos_vazios(serie)
        ausentes_total = nulos + vazios
        preenchidos = qtd_linhas - ausentes_total

        proporcao_nulos = 0.0
        proporcao_vazios = 0.0
        proporcao_ausentes = 0.0

        if qtd_linhas > 0:
            proporcao_nulos = round(
                nulos / qtd_linhas,
                4,
            )
            proporcao_vazios = round(
                vazios / qtd_linhas,
                4,
            )
            proporcao_ausentes = round(
                ausentes_total / qtd_linhas,
                4,
            )

        valores_distintos = int(
            serie.nunique(dropna=True)
        )

        info_coluna = {
            "nome": str(coluna),
            "tipo": str(serie.dtype),
            "categoria_tipo": _classificar_tipo(serie),
            "total": qtd_linhas,
            "preenchidos": preenchidos,
            "nulos": nulos,
            "vazios": vazios,
            "ausentes_total": ausentes_total,
            "proporcao_nulos": proporcao_nulos,
            "proporcao_vazios": proporcao_vazios,
            "proporcao_ausentes": proporcao_ausentes,
            "valores_distintos": valores_distintos,
            "coluna_vazia": (
                qtd_linhas > 0
                and ausentes_total == qtd_linhas
            ),
        }

        resultado["colunas"].append(info_coluna)

    return resultado
