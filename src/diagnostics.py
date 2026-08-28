from typing import Optional


# ==================================================
# CATÁLOGO DE REGRAS DE QUALIDADE POR FINALIDADE
# ==================================================

REGRAS_QUALIDADE = {
    "faturamento_por_regiao": {
        "valor_venda": {
            "tipo_esperado": "numerico",
            "tolera_ausentes": False,
        },
        "regiao": {
            "tipo_esperado": "texto",
            "tolera_ausentes": False,
        },
        "data_venda": {
            # No MVP atual, datas importadas de CSV podem
            # permanecer como texto. A validação de formato
            # e convertibilidade pode entrar no MVP 5.
            "tipos_aceitos": [
                "data",
                "texto",
                "objeto",
            ],
            "tolera_ausentes": False,
        },
    }
}


# ==================================================
# CONSTANTES DE SEVERIDADE
# ==================================================

NIVEL_SEVERIDADE = {
    "IGNORADO": 0,
    "REVISAR": 1,
    "CRÍTICO": 2,
}

STATUS_POR_NIVEL = {
    0: "APTA",
    1: "REVISAR",
    2: "REQUER PREPARAÇÃO",
}


# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def _get_coluna_perfil(
    nome_coluna: str,
    perfil: dict,
) -> Optional[dict]:
    """
    Recupera os metadados de uma coluna específica
    no resultado do profiling.
    """
    for coluna in perfil.get("colunas", []):
        if coluna.get("nome") == nome_coluna:
            return coluna

    return None


def _get_ausentes(perfil_coluna: dict) -> int:
    """
    Obtém a quantidade total de ausências da coluna.

    Usa 'ausentes_total' quando disponível.
    Mantém compatibilidade com versões anteriores do profiler,
    que possuíam somente o campo 'nulos'.
    """
    if "ausentes_total" in perfil_coluna:
        return int(
            perfil_coluna.get("ausentes_total", 0)
        )

    return int(perfil_coluna.get("nulos", 0))


def _get_categoria_tipo(perfil_coluna: dict) -> str:
    """
    Obtém a categoria semântica do tipo.

    Mantém compatibilidade com perfis antigos por meio
    de uma classificação baseada no dtype textual.
    """
    categoria = perfil_coluna.get("categoria_tipo")

    if categoria:
        return str(categoria).lower()

    tipo = str(
        perfil_coluna.get("tipo", "")
    ).lower()

    if "bool" in tipo:
        return "booleano"

    if any(
        marcador in tipo
        for marcador in [
            "int",
            "float",
            "decimal",
            "double",
        ]
    ):
        return "numerico"

    if any(
        marcador in tipo
        for marcador in [
            "datetime",
            "date",
            "timestamp",
        ]
    ):
        return "data"

    if any(
        marcador in tipo
        for marcador in [
            "object",
            "string",
            "str",
        ]
    ):
        return "texto"

    return "objeto"


def _adicionar_problema(
    diagnostico: dict,
    *,
    codigo: str,
    dado: str,
    coluna_base: Optional[str],
    problema: str,
    impacto: str,
    classificacao: str,
    acao_recomendada: str,
) -> None:
    """
    Adiciona um problema ao diagnóstico usando
    uma estrutura padronizada.
    """
    diagnostico["problemas"].append(
        {
            "codigo": codigo,
            "dado": dado,
            "coluna_base": coluna_base,
            "problema": problema,
            "impacto": impacto,
            "classificacao": classificacao,
            "acao_recomendada": acao_recomendada,
        }
    )


def _validar_entradas(
    perfil: dict,
    mapeamento: dict,
) -> str:
    """
    Valida as estruturas recebidas e retorna
    o identificador da finalidade.
    """
    if not isinstance(perfil, dict):
        raise TypeError(
            "O perfil deve ser um dicionário."
        )

    if not isinstance(mapeamento, dict):
        raise TypeError(
            "O mapeamento deve ser um dicionário."
        )

    if "colunas" not in perfil:
        raise ValueError(
            "O perfil não contém a chave 'colunas'."
        )

    if "mapeamento" not in mapeamento:
        raise ValueError(
            "O resultado da comparação não contém "
            "a chave 'mapeamento'."
        )

    finalidade_id = mapeamento.get("finalidade_id")

    if not finalidade_id:
        raise ValueError(
            "O mapeamento não contém 'finalidade_id'. "
            "Execute novamente check_required_data() com "
            "a versão atualizada de comparator.py."
        )

    if finalidade_id not in REGRAS_QUALIDADE:
        finalidades_disponiveis = ", ".join(
            sorted(REGRAS_QUALIDADE.keys())
        )

        raise ValueError(
            f"Não existem regras cadastradas para a finalidade "
            f"'{finalidade_id}'. Finalidades disponíveis: "
            f"{finalidades_disponiveis}"
        )

    return finalidade_id


# ==================================================
# MOTOR DE DIAGNÓSTICO
# ==================================================

def run_diagnostic(
    perfil: dict,
    mapeamento: dict,
) -> dict:
    """
    Avalia a qualidade dos dados de acordo com uma finalidade.

    Consome:
    - O profiling estrutural produzido por profile_data();
    - O mapeamento produzido por check_required_data().

    Esta função não altera e não prepara os dados.
    Ela apenas identifica problemas, impactos e ações
    recomendadas para a futura etapa de preparação.
    """
    finalidade_id = _validar_entradas(
        perfil,
        mapeamento,
    )

    regras = REGRAS_QUALIDADE[finalidade_id]

    diagnostico = {
        "finalidade_id": finalidade_id,
        "finalidade": mapeamento.get(
            "finalidade",
            "Desconhecida",
        ),
        "status": "APTA",
        "nivel_severidade": 0,
        "problemas": [],
        "resumo": {
            "total_problemas": 0,
            "criticos": 0,
            "revisar": 0,
            "ignorados": 0,
        },
    }

    nivel_maximo = 0

    # ==================================================
    # REGRA 1: BASE SEM REGISTROS
    # ==================================================

    qtd_linhas = int(
        perfil.get("geral", {}).get("linhas", 0)
    )

    if qtd_linhas == 0:
        _adicionar_problema(
            diagnostico,
            codigo="BASE_VAZIA",
            dado="Base Geral",
            coluna_base=None,
            problema="A base não possui registros",
            impacto=(
                "Não existem dados para realizar a finalidade "
                "analítica selecionada"
            ),
            classificacao="CRÍTICO",
            acao_recomendada=(
                "Fornecer uma base que contenha registros"
            ),
        )

        nivel_maximo = max(
            nivel_maximo,
            NIVEL_SEVERIDADE["CRÍTICO"],
        )

    # ==================================================
    # REGRA 2: LINHAS INTEGRALMENTE DUPLICADAS
    # ==================================================

    qtd_duplicadas = int(
        perfil.get("geral", {}).get(
            "duplicadas",
            0,
        )
    )

    if qtd_duplicadas > 0:
        _adicionar_problema(
            diagnostico,
            codigo="POSSIVEIS_DUPLICIDADES",
            dado="Base Geral",
            coluna_base=None,
            problema=(
                f"{qtd_duplicadas} possíveis duplicidades"
            ),
            impacto=(
                "Pode provocar contagem ou faturamento "
                "duplicado"
            ),
            classificacao="REVISAR",
            acao_recomendada=(
                "Verificar a regra de identificação de uma "
                "venda antes de remover registros"
            ),
        )

        nivel_maximo = max(
            nivel_maximo,
            NIVEL_SEVERIDADE["REVISAR"],
        )

    # ==================================================
    # REGRAS DOS DADOS NECESSÁRIOS
    # ==================================================

    for item in mapeamento.get("mapeamento", []):
        conceito = item.get("conceito")
        coluna_fisica = item.get("coluna_base")
        status_mapeamento = item.get("status")

        regra_conceito = regras.get(
            conceito,
            {},
        )

        # ----------------------------------------------
        # REGRA 3: DADO NECESSÁRIO AUSENTE
        # ----------------------------------------------

        if (
            status_mapeamento == "NÃO encontrado"
            or not coluna_fisica
        ):
            _adicionar_problema(
                diagnostico,
                codigo="DADO_NECESSARIO_AUSENTE",
                dado=conceito,
                coluna_base=None,
                problema=(
                    "Dado necessário não encontrado"
                ),
                impacto=(
                    f"A análise dependente de '{conceito}' "
                    "não pode ser realizada"
                ),
                classificacao="CRÍTICO",
                acao_recomendada=(
                    "Incluir essa informação na base ou "
                    "selecionar outra fonte de dados"
                ),
            )

            nivel_maximo = max(
                nivel_maximo,
                NIVEL_SEVERIDADE["CRÍTICO"],
            )

            continue

        perfil_coluna = _get_coluna_perfil(
            coluna_fisica,
            perfil,
        )

        if perfil_coluna is None:
            _adicionar_problema(
                diagnostico,
                codigo="COLUNA_NAO_LOCALIZADA_NO_PERFIL",
                dado=conceito,
                coluna_base=coluna_fisica,
                problema=(
                    "A coluna mapeada não foi localizada "
                    "no profiling"
                ),
                impacto=(
                    "A qualidade da coluna não pôde ser "
                    "avaliada"
                ),
                classificacao="CRÍTICO",
                acao_recomendada=(
                    "Executar novamente o profiling e o "
                    "mapeamento sobre a mesma base"
                ),
            )

            nivel_maximo = max(
                nivel_maximo,
                NIVEL_SEVERIDADE["CRÍTICO"],
            )

            continue

        # ----------------------------------------------
        # REGRA 4: AUSÊNCIAS EM DADO NECESSÁRIO
        # ----------------------------------------------

        ausentes = _get_ausentes(
            perfil_coluna
        )

        tolera_ausentes = regra_conceito.get(
            "tolera_ausentes",
            regra_conceito.get(
                "tolera_nulos",
                True,
            ),
        )

        if ausentes > 0 and not tolera_ausentes:
            _adicionar_problema(
                diagnostico,
                codigo="VALORES_AUSENTES",
                dado=conceito,
                coluna_base=coluna_fisica,
                problema=(
                    f"{ausentes} valores ausentes"
                ),
                impacto=(
                    "Pode impedir ou distorcer operações "
                    f"analíticas envolvendo '{conceito}'"
                ),
                classificacao="CRÍTICO",
                acao_recomendada=(
                    "Avaliar preenchimento, exclusão dos "
                    "registros ou aplicação de uma regra "
                    "de negócio"
                ),
            )

            nivel_maximo = max(
                nivel_maximo,
                NIVEL_SEVERIDADE["CRÍTICO"],
            )

        # ----------------------------------------------
        # REGRA 5: TIPO INADEQUADO
        # ----------------------------------------------

        categoria_tipo = _get_categoria_tipo(
            perfil_coluna
        )

        tipo_esperado = regra_conceito.get(
            "tipo_esperado"
        )

        tipos_aceitos = regra_conceito.get(
            "tipos_aceitos"
        )

        tipo_valido = True
        tipo_descrito = None

        if tipo_esperado:
            tipo_valido = (
                categoria_tipo == tipo_esperado
            )
            tipo_descrito = tipo_esperado

        elif tipos_aceitos:
            tipo_valido = (
                categoria_tipo in tipos_aceitos
            )
            tipo_descrito = ", ".join(
                tipos_aceitos
            )

        elif regra_conceito.get(
            "numerico_obrigatorio",
            False,
        ):
            tipo_valido = (
                categoria_tipo == "numerico"
            )
            tipo_descrito = "numerico"

        if not tipo_valido:
            _adicionar_problema(
                diagnostico,
                codigo="TIPO_INADEQUADO",
                dado=conceito,
                coluna_base=coluna_fisica,
                problema=(
                    f"Tipo '{categoria_tipo}' incompatível. "
                    f"Tipo esperado: {tipo_descrito}"
                ),
                impacto=(
                    "Pode impedir as operações necessárias "
                    "para a finalidade selecionada"
                ),
                classificacao="CRÍTICO",
                acao_recomendada=(
                    f"Converter a coluna '{coluna_fisica}' "
                    f"para o tipo esperado: {tipo_descrito}"
                ),
            )

            nivel_maximo = max(
                nivel_maximo,
                NIVEL_SEVERIDADE["CRÍTICO"],
            )

    # ==================================================
    # REGRA 6: AUSÊNCIAS EM DADOS ADICIONAIS
    # ==================================================

    for coluna_adicional in mapeamento.get(
        "dados_adicionais",
        [],
    ):
        perfil_adicional = _get_coluna_perfil(
            coluna_adicional,
            perfil,
        )

        if perfil_adicional is None:
            continue

        ausentes = _get_ausentes(
            perfil_adicional
        )

        if ausentes > 0:
            _adicionar_problema(
                diagnostico,
                codigo="AUSENCIA_DADO_ADICIONAL",
                dado=coluna_adicional,
                coluna_base=coluna_adicional,
                problema=(
                    f"{ausentes} valores ausentes"
                ),
                impacto=(
                    "Não afeta a finalidade selecionada"
                ),
                classificacao="IGNORADO",
                acao_recomendada=(
                    "Nenhuma ação necessária para esta "
                    "finalidade"
                ),
            )

    # ==================================================
    # CONSOLIDAÇÃO DO RESULTADO
    # ==================================================

    diagnostico["nivel_severidade"] = nivel_maximo
    diagnostico["status"] = STATUS_POR_NIVEL[
        nivel_maximo
    ]

    problemas = diagnostico["problemas"]

    diagnostico["resumo"]["total_problemas"] = len(
        problemas
    )

    diagnostico["resumo"]["criticos"] = sum(
        1
        for problema in problemas
        if problema["classificacao"] == "CRÍTICO"
    )

    diagnostico["resumo"]["revisar"] = sum(
        1
        for problema in problemas
        if problema["classificacao"] == "REVISAR"
    )

    diagnostico["resumo"]["ignorados"] = sum(
        1
        for problema in problemas
        if problema["classificacao"] == "IGNORADO"
    )

    return diagnostico


# ==================================================
# APRESENTAÇÃO DO DIAGNÓSTICO
# ==================================================

def print_diagnostic(diag: dict) -> None:
    """
    Exibe o diagnóstico de forma estruturada
    no terminal ou notebook.
    """
    print("=" * 50)
    print("DIAGNÓSTICO")
    print("=" * 50)

    print(f"Finalidade: {diag['finalidade']}")
    print(
        f"Identificador: "
        f"{diag.get('finalidade_id', 'Não informado')}"
    )
    print(f"Status: {diag['status']}")

    resumo = diag.get("resumo", {})

    print("\nRESUMO\n")
    print(
        f"Total de problemas: "
        f"{resumo.get('total_problemas', 0)}"
    )
    print(
        f"Críticos: "
        f"{resumo.get('criticos', 0)}"
    )
    print(
        f"Para revisão: "
        f"{resumo.get('revisar', 0)}"
    )
    print(
        f"Ignorados nesta finalidade: "
        f"{resumo.get('ignorados', 0)}"
    )

    problemas = diag.get("problemas", [])

    if not problemas:
        print("\nNenhum problema identificado.")
        print(
            "A base está apta para a finalidade "
            "selecionada."
        )
        return

    print("\nPROBLEMAS\n")

    for indice, problema in enumerate(
        problemas,
        start=1,
    ):
        print(f"{indice}. {problema['codigo']}")
        print(f"Dado: {problema['dado']}")

        if problema.get("coluna_base"):
            print(
                f"Coluna: {problema['coluna_base']}"
            )

        print(
            f"Problema: {problema['problema']}"
        )
        print(
            f"Impacto: {problema['impacto']}"
        )
        print(
            "Classificação: "
            f"{problema['classificacao']}"
        )
        print(
            f"Ação recomendada: "
            f"{problema['acao_recomendada']}"
        )
        print()

    print("=" * 50)
    print(f"STATUS FINAL: {diag['status']}")
    print("=" * 50)