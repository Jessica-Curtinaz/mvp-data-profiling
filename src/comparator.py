import re
import unicodedata
from typing import Any


# ==================================================
# CATÁLOGO DE ANÁLISES
# ==================================================

CATALOGO_ANALISES = {
    "faturamento_por_regiao": {
        "nome": "Faturamento por Região",
        "descricao": (
            "Avalia se a base contém os dados mínimos necessários "
            "para calcular e analisar o faturamento por região."
        ),
        "dados_necessarios": [
            "data_venda",
            "regiao",
            "valor_venda",
        ],
    }
}


# ==================================================
# DICIONÁRIO CONTROLADO DE ALIASES
# ==================================================

DICIONARIO_ALIASES = {
    "valor_venda": [
        "valor_venda",
        "valor venda",
        "valor total",
        "valor da venda",
        "faturamento",
        "sales amount",
        "sale amount",
        "vendas",
    ],
    "data_venda": [
        "data_venda",
        "data venda",
        "data da venda",
        "sale date",
        "order date",
        "data pedido",
        "data do pedido",
    ],
    "regiao": [
        "regiao",
        "região",
        "uf",
        "estado",
        "region",
        "unidade da federacao",
        "unidade da federação",
        "grande regiao",
        "grande região",
    ],
}


# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def normalize_name(name: Any) -> str:
    """
    Normaliza um nome para facilitar a comparação semântica.

    Etapas:
    - Converte o valor para texto quando possível;
    - Remove espaços nas extremidades;
    - Remove acentos;
    - Converte para minúsculas;
    - Remove caracteres que não sejam letras ou números.

    Exemplos:
        "Valor Total" -> "valortotal"
        "valor_total" -> "valortotal"
        "REGIÃO" -> "regiao"
        "Data-da-Venda" -> "datadavenda"
    """
    if name is None:
        return ""

    if not isinstance(name, str):
        name = str(name)

    name = name.strip()

    if not name:
        return ""

    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ASCII", "ignore").decode("utf-8")
    name = name.lower()

    return re.sub(r"[^a-z0-9]", "", name)


def _validate_profile(profile: dict) -> None:
    """
    Valida a estrutura mínima esperada do profiling.
    """
    if not isinstance(profile, dict):
        raise TypeError(
            "O profile deve ser um dicionário gerado por profile_data()."
        )

    if "colunas" not in profile:
        raise ValueError(
            "O profile informado não contém a chave obrigatória 'colunas'."
        )

    if not isinstance(profile["colunas"], list):
        raise ValueError(
            "A chave 'colunas' do profile deve conter uma lista."
        )

    for indice, coluna in enumerate(profile["colunas"]):
        if not isinstance(coluna, dict):
            raise ValueError(
                f"O item {indice} de 'colunas' deve ser um dicionário."
            )

        if "nome" not in coluna:
            raise ValueError(
                f"O item {indice} de 'colunas' não possui a chave 'nome'."
            )


def _get_aliases_normalizados(conceito: str) -> dict:
    """
    Retorna um dicionário no formato:

        {
            "aliasnormalizado": "alias original"
        }

    O próprio nome do conceito é sempre incluído.
    """
    aliases = DICIONARIO_ALIASES.get(conceito, [])

    aliases_completos = list(dict.fromkeys([conceito] + aliases))

    return {
        normalize_name(alias): alias
        for alias in aliases_completos
        if normalize_name(alias)
    }


# ==================================================
# MOTOR DE COMPARAÇÃO
# ==================================================

def check_required_data(profile: dict, analise_id: str) -> dict:
    """
    Cruza as colunas encontradas no profiling com os dados necessários
    para uma finalidade analítica.

    Retorna:
    - Identificador e nome da finalidade;
    - Status estrutural da base;
    - Mapeamento entre conceitos e colunas físicas;
    - Colunas adicionais não utilizadas;
    - Resumo da comparação.

    Status possíveis:
    - APTA: todos os dados necessários foram encontrados;
    - INCOMPLETA: pelo menos um dado necessário não foi encontrado.

    Esta função avalia somente a presença estrutural das colunas.
    A qualidade dos valores é avaliada em diagnostics.py.
    """
    _validate_profile(profile)

    if analise_id not in CATALOGO_ANALISES:
        analises_disponiveis = ", ".join(
            sorted(CATALOGO_ANALISES.keys())
        )

        raise ValueError(
            f"Análise '{analise_id}' não cadastrada. "
            f"Análises disponíveis: {analises_disponiveis}"
        )

    analise = CATALOGO_ANALISES[analise_id]
    requisitos = analise["dados_necessarios"]

    colunas_encontradas = [
        coluna["nome"]
        for coluna in profile["colunas"]
    ]

    resultado = {
        "finalidade_id": analise_id,
        "finalidade": analise["nome"],
        "descricao_finalidade": analise.get("descricao"),
        "status": "APTA",
        "mapeamento": [],
        "dados_adicionais": [],
        "resumo": {
            "requisitos_total": len(requisitos),
            "requisitos_encontrados": 0,
            "requisitos_ausentes": 0,
            "colunas_adicionais": 0,
        },
    }

    colunas_utilizadas = set()

    for requisito in requisitos:
        coluna_correspondente = None
        alias_reconhecido = None

        aliases_normalizados = _get_aliases_normalizados(
            requisito
        )

        for coluna_original in colunas_encontradas:
            if coluna_original in colunas_utilizadas:
                continue

            coluna_normalizada = normalize_name(
                coluna_original
            )

            if coluna_normalizada in aliases_normalizados:
                coluna_correspondente = coluna_original
                alias_reconhecido = aliases_normalizados[
                    coluna_normalizada
                ]

                colunas_utilizadas.add(coluna_original)
                break

        encontrado = coluna_correspondente is not None

        resultado["mapeamento"].append(
            {
                "conceito": requisito,
                "status": (
                    "Encontrado"
                    if encontrado
                    else "NÃO encontrado"
                ),
                "coluna_base": coluna_correspondente,
                "alias_reconhecido": alias_reconhecido,
            }
        )

        if encontrado:
            resultado["resumo"][
                "requisitos_encontrados"
            ] += 1
        else:
            resultado["resumo"][
                "requisitos_ausentes"
            ] += 1

            resultado["status"] = "INCOMPLETA"

    resultado["dados_adicionais"] = [
        coluna
        for coluna in colunas_encontradas
        if coluna not in colunas_utilizadas
    ]

    resultado["resumo"]["colunas_adicionais"] = len(
        resultado["dados_adicionais"]
    )

    return resultado


# ==================================================
# APRESENTAÇÃO DO RESULTADO
# ==================================================

def print_analise_status(resultado: dict) -> None:
    """
    Exibe o resultado da comparação de forma legível
    no terminal ou notebook.
    """
    print("=" * 50)
    print("COMPARAÇÃO COM A FINALIDADE")
    print("=" * 50)

    print(f"Finalidade: {resultado['finalidade']}")
    print(
        f"Identificador: "
        f"{resultado.get('finalidade_id', 'Não informado')}"
    )

    descricao = resultado.get("descricao_finalidade")

    if descricao:
        print(f"Descrição: {descricao}")

    print("\nDADOS NECESSÁRIOS\n")

    for item in resultado.get("mapeamento", []):
        print(f"Conceito: {item['conceito']}")
        print(f"Status: {item['status']}")

        if item.get("coluna_base"):
            print(f"Coluna encontrada: {item['coluna_base']}")

        if item.get("alias_reconhecido"):
            print(
                f"Alias reconhecido: "
                f"{item['alias_reconhecido']}"
            )

        print()

    dados_adicionais = resultado.get(
        "dados_adicionais",
        [],
    )

    if dados_adicionais:
        print("DADOS ADICIONAIS\n")

        for coluna in dados_adicionais:
            print(f"- {coluna}")

        print()

    resumo = resultado.get("resumo", {})

    if resumo:
        print("RESUMO\n")
        print(
            "Requisitos encontrados: "
            f"{resumo.get('requisitos_encontrados', 0)}"
            f"/{resumo.get('requisitos_total', 0)}"
        )
        print(
            "Requisitos ausentes: "
            f"{resumo.get('requisitos_ausentes', 0)}"
        )
        print(
            "Colunas adicionais: "
            f"{resumo.get('colunas_adicionais', 0)}"
        )
        print()

    print(f"STATUS ESTRUTURAL\n\n{resultado['status']}")