import re
from typing import Optional

import pandas as pd


# ==================================================
# POLÍTICAS SEGURAS DE PREPARAÇÃO
# ==================================================

POLITICAS_PREPARACAO = {
    "faturamento_por_regiao": {
        "data_venda": {
            "remover_espacos": True,
            "padronizar_data": True,
            "preencher_ausentes": False,
        },
        "regiao": {
            "remover_espacos": True,
            "padronizar_maiusculo": True,
            "preencher_ausentes": True,
            "valor_ausente": "NÃO INFORMADO",
        },
        "valor_venda": {
            "remover_espacos": True,
            "converter_numerico": True,
            "preencher_ausentes": False,
        },
    }
}


# ==================================================
# VALIDAÇÕES
# ==================================================

def _validar_entradas(
    df: pd.DataFrame,
    diagnostico: dict,
    mapeamento: dict,
) -> str:
    """
    Valida as entradas do motor de preparação e retorna
    o identificador da finalidade.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "O parâmetro 'df' deve ser um pandas.DataFrame."
        )

    if not isinstance(diagnostico, dict):
        raise TypeError(
            "O diagnóstico deve ser um dicionário."
        )

    if not isinstance(mapeamento, dict):
        raise TypeError(
            "O mapeamento deve ser um dicionário."
        )

    if "problemas" not in diagnostico:
        raise ValueError(
            "O diagnóstico não contém a chave 'problemas'."
        )

    if "mapeamento" not in mapeamento:
        raise ValueError(
            "O mapeamento não contém a chave 'mapeamento'."
        )

    finalidade_diagnostico = diagnostico.get(
        "finalidade_id"
    )

    finalidade_mapeamento = mapeamento.get(
        "finalidade_id"
    )

    if not finalidade_diagnostico:
        raise ValueError(
            "O diagnóstico não contém 'finalidade_id'."
        )

    if not finalidade_mapeamento:
        raise ValueError(
            "O mapeamento não contém 'finalidade_id'."
        )

    if finalidade_diagnostico != finalidade_mapeamento:
        raise ValueError(
            "O diagnóstico e o mapeamento pertencem "
            "a finalidades diferentes."
        )

    if finalidade_diagnostico not in POLITICAS_PREPARACAO:
        disponiveis = ", ".join(
            sorted(POLITICAS_PREPARACAO.keys())
        )

        raise ValueError(
            f"Não existem políticas de preparação para "
            f"'{finalidade_diagnostico}'. "
            f"Finalidades disponíveis: {disponiveis}"
        )

    return finalidade_diagnostico


def _obter_mapeamento_por_conceito(
    mapeamento: dict,
) -> dict:
    """
    Converte a lista de mapeamentos em um dicionário:

        conceito -> coluna física
    """
    resultado = {}

    for item in mapeamento.get("mapeamento", []):
        conceito = item.get("conceito")
        coluna = item.get("coluna_base")

        if conceito and coluna:
            resultado[conceito] = coluna

    return resultado


# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def _mascara_texto_vazio(
    serie: pd.Series,
) -> pd.Series:
    """
    Identifica valores textuais vazios ou compostos
    somente por espaços, sem considerar nulos.
    """
    mascara = pd.Series(
        False,
        index=serie.index,
        dtype=bool,
    )

    valores_validos = serie.notna()

    if valores_validos.any():
        textos = serie.loc[
            valores_validos
        ].astype("string")

        mascara.loc[valores_validos] = (
            textos.str.strip().eq("")
        )

    return mascara


def _contar_alteracoes(
    antes: pd.Series,
    depois: pd.Series,
) -> int:
    """
    Conta quantos registros mudaram, tratando dois valores
    nulos como equivalentes.
    """
    iguais = antes.eq(depois)

    ambos_nulos = (
        antes.isna()
        & depois.isna()
    )

    return int(
        (~(iguais | ambos_nulos)).sum()
    )


def _normalizar_texto_comparacao(
    valor,
) -> Optional[str]:
    """
    Converte um valor para texto normalizado apenas para
    comparação e detecção de alterações.
    """
    if pd.isna(valor):
        return None

    return str(valor)


def _criar_registro_log(
    *,
    problema_origem: str,
    conceito: Optional[str],
    coluna: Optional[str],
    acao: str,
    status: str,
    registros_afetados: int = 0,
    detalhes: Optional[str] = None,
    valores_invalidos: int = 0,
) -> dict:
    """
    Cria uma entrada padronizada para o log de preparação.
    """
    return {
        "problema_origem": problema_origem,
        "conceito": conceito,
        "coluna": coluna,
        "acao": acao,
        "status": status,
        "registros_afetados": int(
            registros_afetados
        ),
        "valores_invalidos": int(
            valores_invalidos
        ),
        "detalhes": detalhes,
    }


# ==================================================
# TRANSFORMAÇÕES SEGURAS
# ==================================================

def _remover_espacos(
    df: pd.DataFrame,
    coluna: str,
) -> dict:
    """
    Remove espaços no início e no fim de valores textuais.

    Valores nulos continuam nulos.
    """
    antes = df[coluna].copy()

    df[coluna] = (
        df[coluna]
        .astype("string")
        .str.strip()
    )

    depois = df[coluna]

    quantidade = _contar_alteracoes(
        antes.astype("string"),
        depois,
    )

    return {
        "df": df,
        "registros_afetados": quantidade,
    }


def _padronizar_maiusculo(
    df: pd.DataFrame,
    coluna: str,
) -> dict:
    """
    Padroniza uma coluna textual para letras maiúsculas.
    """
    antes = df[coluna].copy()

    df[coluna] = (
        df[coluna]
        .astype("string")
        .str.upper()
    )

    depois = df[coluna]

    quantidade = _contar_alteracoes(
        antes.astype("string"),
        depois,
    )

    return {
        "df": df,
        "registros_afetados": quantidade,
    }


def _preencher_categorico_ausente(
    df: pd.DataFrame,
    coluna: str,
    valor_substituto: str,
) -> dict:
    """
    Substitui nulos e textos vazios de uma coluna categórica
    por um marcador explícito.

    Nenhuma linha é removida.
    """
    serie = df[coluna].copy()

    mascara_nulos = serie.isna()
    mascara_vazios = _mascara_texto_vazio(
        serie
    )

    mascara_ausentes = (
        mascara_nulos
        | mascara_vazios
    )

    quantidade = int(
        mascara_ausentes.sum()
    )

    if quantidade > 0:
        if not (
            pd.api.types.is_string_dtype(serie)
            or serie.dtype == "object"
        ):
            df[coluna] = serie.astype("string")

        df.loc[
            mascara_ausentes,
            coluna,
        ] = valor_substituto

    return {
        "df": df,
        "registros_afetados": quantidade,
    }


def _normalizar_valor_numerico(
    valor,
):
    """
    Normaliza um valor textual para posterior conversão
    numérica.

    Exemplos suportados:
        R$ 1.234,56 -> 1234.56
        1.234,56    -> 1234.56
        1,234.56    -> 1234.56
        1234,56     -> 1234.56
        1234.56     -> 1234.56

    Valores vazios permanecem ausentes.
    """
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    if not texto:
        return pd.NA

    texto = (
        texto
        .replace("\u00a0", "")
        .replace(" ", "")
    )

    texto = re.sub(
        r"[^\d,\.\-\+]",
        "",
        texto,
    )

    if texto in {
        "",
        "-",
        "+",
        ".",
        ",",
    }:
        return pd.NA

    possui_virgula = "," in texto
    possui_ponto = "." in texto

    if possui_virgula and possui_ponto:
        ultima_virgula = texto.rfind(",")
        ultimo_ponto = texto.rfind(".")

        if ultima_virgula > ultimo_ponto:
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")

    elif possui_virgula:
        partes = texto.split(",")

        if (
            len(partes) == 2
            and len(partes[1]) in {1, 2}
        ):
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")

    elif possui_ponto:
        partes = texto.split(".")

        if len(partes) > 2:
            casas_decimais = partes[-1]

            if len(casas_decimais) in {1, 2}:
                texto = (
                    "".join(partes[:-1])
                    + "."
                    + casas_decimais
                )
            else:
                texto = "".join(partes)

    return texto


def _converter_numerico(
    df: pd.DataFrame,
    coluna: str,
) -> dict:
    """
    Converte uma coluna para numérico.

    A conversão nunca preenche valores inválidos. Valores
    que não puderem ser convertidos tornam-se ausentes e
    são registrados no log.
    """
    antes = df[coluna].copy()

    normalizada = antes.map(
        _normalizar_valor_numerico
    )

    convertida = pd.to_numeric(
        normalizada,
        errors="coerce",
    )

    originalmente_preenchidos = (
        antes.notna()
        & antes.astype("string").str.strip().ne("")
    )

    invalidos = (
        originalmente_preenchidos
        & convertida.isna()
    )

    qtd_invalidos = int(
        invalidos.sum()
    )

    df[coluna] = convertida

    antes_comparacao = antes.map(
        _normalizar_texto_comparacao
    )

    depois_comparacao = convertida.map(
        _normalizar_texto_comparacao
    )

    quantidade = _contar_alteracoes(
        antes_comparacao,
        depois_comparacao,
    )

    return {
        "df": df,
        "registros_afetados": quantidade,
        "valores_invalidos": qtd_invalidos,
    }


def _padronizar_data(
    df: pd.DataFrame,
    coluna: str,
) -> dict:
    """
    Converte uma coluna para datetime.

    Valores não convertíveis tornam-se NaT e são registrados.
    Não ocorre preenchimento ou criação artificial de datas.
    """
    antes = df[coluna].copy()

    convertida = pd.to_datetime(
        antes,
        errors="coerce",
        format="mixed",
        dayfirst=True,
    )

    originalmente_preenchidos = (
        antes.notna()
        & antes.astype("string").str.strip().ne("")
    )

    invalidos = (
        originalmente_preenchidos
        & convertida.isna()
    )

    qtd_invalidos = int(
        invalidos.sum()
    )

    df[coluna] = convertida

    antes_comparacao = antes.astype(
        "string"
    )

    depois_comparacao = convertida.astype(
        "string"
    )

    quantidade = _contar_alteracoes(
        antes_comparacao,
        depois_comparacao,
    )

    return {
        "df": df,
        "registros_afetados": quantidade,
        "valores_invalidos": qtd_invalidos,
    }


# ==================================================
# MOTOR DE PREPARAÇÃO
# ==================================================

def prepare_data(
    df: pd.DataFrame,
    diagnostico: dict,
    mapeamento: dict,
) -> dict:
    """
    Aplica transformações seguras orientadas pela finalidade,
    pelo mapeamento e pelo diagnóstico.

    Princípios:
    - Não altera o DataFrame original;
    - Não remove registros automaticamente;
    - Não cria valores numéricos ou datas;
    - Não imputa ausências sem uma política explícita;
    - Restringe as transformações às colunas mapeadas;
    - Registra todas as ações e decisões;
    - Mantém problemas não tratáveis para decisão futura.

    Retorno:
        {
            "df": DataFrame preparado,
            "df_original": cópia da base original,
            "transformacoes": [...],
            "problemas_nao_tratados": [...],
            "resumo": {...}
        }
    """
    finalidade_id = _validar_entradas(
        df,
        diagnostico,
        mapeamento,
    )

    base_original = df.copy(deep=True)
    base_preparada = df.copy(deep=True)

    politicas = POLITICAS_PREPARACAO[
        finalidade_id
    ]

    colunas_por_conceito = (
        _obter_mapeamento_por_conceito(
            mapeamento
        )
    )

    transformacoes = []
    problemas_nao_tratados = []

    codigos_por_coluna = {}

    for problema in diagnostico.get(
        "problemas",
        [],
    ):
        coluna = problema.get("coluna_base")
        codigo = problema.get("codigo")

        if coluna and codigo:
            codigos_por_coluna.setdefault(
                coluna,
                set(),
            ).add(codigo)

    # ==================================================
    # TRANSFORMAÇÕES POR CONCEITO E FINALIDADE
    # ==================================================

    for conceito, politica in politicas.items():
        coluna = colunas_por_conceito.get(
            conceito
        )

        if not coluna:
            continue

        if coluna not in base_preparada.columns:
            problemas_nao_tratados.append(
                _criar_registro_log(
                    problema_origem=(
                        "COLUNA_NAO_LOCALIZADA"
                    ),
                    conceito=conceito,
                    coluna=coluna,
                    acao="nenhuma",
                    status="NÃO APLICADA",
                    detalhes=(
                        "A coluna mapeada não existe "
                        "na base recebida."
                    ),
                )
            )
            continue

        problemas_coluna = codigos_por_coluna.get(
            coluna,
            set(),
        )

        # ----------------------------------------------
        # REMOÇÃO DE ESPAÇOS
        # ----------------------------------------------

        if politica.get(
            "remover_espacos",
            False,
        ):
            if (
                pd.api.types.is_string_dtype(
                    base_preparada[coluna]
                )
                or base_preparada[
                    coluna
                ].dtype == "object"
            ):
                resultado = _remover_espacos(
                    base_preparada,
                    coluna,
                )

                base_preparada = resultado["df"]

                transformacoes.append(
                    _criar_registro_log(
                        problema_origem=(
                            "NORMALIZACAO_SEGURA"
                        ),
                        conceito=conceito,
                        coluna=coluna,
                        acao="remover_espacos",
                        status="APLICADA",
                        registros_afetados=resultado[
                            "registros_afetados"
                        ],
                        detalhes=(
                            "Espaços no início e no fim "
                            "foram removidos."
                        ),
                    )
                )

        # ----------------------------------------------
        # PADRONIZAÇÃO DE TEXTO CATEGÓRICO
        # ----------------------------------------------

        if politica.get(
            "padronizar_maiusculo",
            False,
        ):
            resultado = _padronizar_maiusculo(
                base_preparada,
                coluna,
            )

            base_preparada = resultado["df"]

            transformacoes.append(
                _criar_registro_log(
                    problema_origem=(
                        "NORMALIZACAO_CATEGORICA"
                    ),
                    conceito=conceito,
                    coluna=coluna,
                    acao="padronizar_maiusculo",
                    status="APLICADA",
                    registros_afetados=resultado[
                        "registros_afetados"
                    ],
                    detalhes=(
                        "Valores categóricos foram "
                        "padronizados para maiúsculas."
                    ),
                )
            )

        # ----------------------------------------------
        # PREENCHIMENTO CATEGÓRICO SEGURO
        # ----------------------------------------------

        if (
            politica.get(
                "preencher_ausentes",
                False,
            )
            and "VALORES_AUSENTES"
            in problemas_coluna
        ):
            valor_ausente = politica.get(
                "valor_ausente",
                "NÃO INFORMADO",
            )

            resultado = (
                _preencher_categorico_ausente(
                    base_preparada,
                    coluna,
                    valor_ausente,
                )
            )

            base_preparada = resultado["df"]

            transformacoes.append(
                _criar_registro_log(
                    problema_origem=(
                        "VALORES_AUSENTES"
                    ),
                    conceito=conceito,
                    coluna=coluna,
                    acao=(
                        "preencher_categorico_ausente"
                    ),
                    status="APLICADA",
                    registros_afetados=resultado[
                        "registros_afetados"
                    ],
                    detalhes=(
                        "Ausências substituídas por "
                        f"'{valor_ausente}'. "
                        "Nenhuma linha foi removida."
                    ),
                )
            )

        # ----------------------------------------------
        # CONVERSÃO NUMÉRICA
        # ----------------------------------------------

        if (
            politica.get(
                "converter_numerico",
                False,
            )
            and "TIPO_INADEQUADO"
            in problemas_coluna
        ):
            resultado = _converter_numerico(
                base_preparada,
                coluna,
            )

            base_preparada = resultado["df"]

            status = "APLICADA"

            if resultado["valores_invalidos"] > 0:
                status = "APLICADA COM PENDÊNCIAS"

            transformacoes.append(
                _criar_registro_log(
                    problema_origem=(
                        "TIPO_INADEQUADO"
                    ),
                    conceito=conceito,
                    coluna=coluna,
                    acao="converter_numerico",
                    status=status,
                    registros_afetados=resultado[
                        "registros_afetados"
                    ],
                    valores_invalidos=resultado[
                        "valores_invalidos"
                    ],
                    detalhes=(
                        "Valores compatíveis foram "
                        "convertidos para numérico. "
                        "Valores não convertíveis "
                        "permanecem ausentes."
                    ),
                )
            )

        # ----------------------------------------------
        # PADRONIZAÇÃO DE DATA
        # ----------------------------------------------

        if politica.get(
            "padronizar_data",
            False,
        ):
            resultado = _padronizar_data(
                base_preparada,
                coluna,
            )

            base_preparada = resultado["df"]

            status = "APLICADA"

            if resultado["valores_invalidos"] > 0:
                status = "APLICADA COM PENDÊNCIAS"

            transformacoes.append(
                _criar_registro_log(
                    problema_origem=(
                        "PADRONIZACAO_DATA"
                    ),
                    conceito=conceito,
                    coluna=coluna,
                    acao="padronizar_data",
                    status=status,
                    registros_afetados=resultado[
                        "registros_afetados"
                    ],
                    valores_invalidos=resultado[
                        "valores_invalidos"
                    ],
                    detalhes=(
                        "Valores compatíveis foram "
                        "convertidos para datetime. "
                        "Datas inválidas permanecem "
                        "ausentes."
                    ),
                )
            )

    # ==================================================
    # PROBLEMAS QUE EXIGEM DECISÃO HUMANA
    # ==================================================

    codigos_automaticamente_trataveis = {
        "TIPO_INADEQUADO",
        "VALORES_AUSENTES",
    }

    for problema in diagnostico.get(
        "problemas",
        [],
    ):
        codigo = problema.get("codigo")

        if codigo in {
            "DADO_NECESSARIO_AUSENTE",
            "COLUNA_NAO_LOCALIZADA_NO_PERFIL",
            "POSSIVEIS_DUPLICIDADES",
            "BASE_VAZIA",
        }:
            problemas_nao_tratados.append(
                _criar_registro_log(
                    problema_origem=codigo,
                    conceito=problema.get("dado"),
                    coluna=problema.get(
                        "coluna_base"
                    ),
                    acao="nenhuma",
                    status="NÃO APLICADA",
                    detalhes=(
                        problema.get(
                            "acao_recomendada"
                        )
                        or (
                            "O problema exige regra de "
                            "negócio ou decisão humana."
                        )
                    ),
                )
            )

        elif (
            codigo
            not in codigos_automaticamente_trataveis
            and problema.get(
                "classificacao"
            ) != "IGNORADO"
        ):
            problemas_nao_tratados.append(
                _criar_registro_log(
                    problema_origem=codigo,
                    conceito=problema.get("dado"),
                    coluna=problema.get(
                        "coluna_base"
                    ),
                    acao="nenhuma",
                    status="NÃO APLICADA",
                    detalhes=(
                        "Não há transformação automática "
                        "cadastrada para esse problema."
                    ),
                )
            )

    aplicadas = sum(
        1
        for item in transformacoes
        if item["status"] == "APLICADA"
    )

    aplicadas_com_pendencias = sum(
        1
        for item in transformacoes
        if item["status"]
        == "APLICADA COM PENDÊNCIAS"
    )

    registros_afetados = sum(
        item["registros_afetados"]
        for item in transformacoes
    )

    valores_invalidos = sum(
        item["valores_invalidos"]
        for item in transformacoes
    )

    return {
        "finalidade_id": finalidade_id,
        "finalidade": diagnostico.get(
            "finalidade"
        ),
        "df_original": base_original,
        "df": base_preparada,
        "transformacoes": transformacoes,
        "problemas_nao_tratados": (
            problemas_nao_tratados
        ),
        "resumo": {
            "transformacoes_total": len(
                transformacoes
            ),
            "aplicadas": aplicadas,
            "aplicadas_com_pendencias": (
                aplicadas_com_pendencias
            ),
            "problemas_nao_tratados": len(
                problemas_nao_tratados
            ),
            "registros_afetados": (
                registros_afetados
            ),
            "valores_invalidos": (
                valores_invalidos
            ),
            "linhas_antes": int(
                len(base_original)
            ),
            "linhas_depois": int(
                len(base_preparada)
            ),
            "linhas_removidas": int(
                len(base_original)
                - len(base_preparada)
            ),
        },
    }


# ==================================================
# APRESENTAÇÃO
# ==================================================

def print_preparation(
    preparacao: dict,
) -> None:
    """
    Exibe o resultado da preparação de forma legível.
    """
    print("=" * 50)
    print("PREPARAÇÃO DE DADOS")
    print("=" * 50)

    print(
        f"Finalidade: "
        f"{preparacao.get('finalidade')}"
    )

    resumo = preparacao.get("resumo", {})

    print("\nRESUMO\n")
    print(
        "Transformações registradas: "
        f"{resumo.get('transformacoes_total', 0)}"
    )
    print(
        "Aplicadas sem pendências: "
        f"{resumo.get('aplicadas', 0)}"
    )
    print(
        "Aplicadas com pendências: "
        f"{resumo.get('aplicadas_com_pendencias', 0)}"
    )
    print(
        "Problemas não tratados: "
        f"{resumo.get('problemas_nao_tratados', 0)}"
    )
    print(
        "Registros afetados pelas operações: "
        f"{resumo.get('registros_afetados', 0)}"
    )
    print(
        "Valores não convertíveis: "
        f"{resumo.get('valores_invalidos', 0)}"
    )
    print(
        "Linhas antes/depois: "
        f"{resumo.get('linhas_antes', 0)}"
        "/"
        f"{resumo.get('linhas_depois', 0)}"
    )
    print(
        "Linhas removidas: "
        f"{resumo.get('linhas_removidas', 0)}"
    )

    transformacoes = preparacao.get(
        "transformacoes",
        [],
    )

    if transformacoes:
        print("\nTRANSFORMAÇÕES\n")

        for indice, item in enumerate(
            transformacoes,
            start=1,
        ):
            print(f"{indice}. {item['acao']}")
            print(
                f"Problema/origem: "
                f"{item['problema_origem']}"
            )
            print(
                f"Conceito: {item['conceito']}"
            )
            print(
                f"Coluna: {item['coluna']}"
            )
            print(
                f"Status: {item['status']}"
            )
            print(
                "Registros afetados: "
                f"{item['registros_afetados']}"
            )

            if item["valores_invalidos"] > 0:
                print(
                    "Valores não convertíveis: "
                    f"{item['valores_invalidos']}"
                )

            if item.get("detalhes"):
                print(
                    f"Detalhes: {item['detalhes']}"
                )

            print()

    nao_tratados = preparacao.get(
        "problemas_nao_tratados",
        [],
    )

    if nao_tratados:
        print("PROBLEMAS NÃO TRATADOS AUTOMATICAMENTE\n")

        for indice, item in enumerate(
            nao_tratados,
            start=1,
        ):
            print(
                f"{indice}. "
                f"{item['problema_origem']}"
            )
            print(
                f"Dado: {item['conceito']}"
            )

            if item.get("coluna"):
                print(
                    f"Coluna: {item['coluna']}"
                )

            print(
                f"Motivo: {item['detalhes']}"
            )
            print()