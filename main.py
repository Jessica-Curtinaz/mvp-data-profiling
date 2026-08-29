import json

import pandas as pd

from src.loader import load_data
from src.profiler import profile_data
from src.comparator import (
    check_required_data,
    print_analise_status,
)
from src.diagnostics import (
    run_diagnostic,
    print_diagnostic,
)
from src.preparer import (
    prepare_data,
    print_preparation,
)


# ==================================================
# CONFIGURAÇÕES
# ==================================================

FINALIDADE_ID = "faturamento_por_regiao"

ARQUIVOS_TESTE = [
    "data/exemplo/vendas_kaggle.csv",
    "data/exemplo/vendas_governo.csv",
    "data/exemplo/erp.csv",
]


# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def _possui_acao_automatica(
    diagnostico: dict,
) -> bool:
    """
    Verifica se o diagnóstico possui pelo menos um problema
    para o qual o MVP 5 dispõe de transformação automática.

    Normalizações seguras de data, região e espaços também
    são executadas quando a base está estruturalmente apta.
    """
    codigos_automaticos = {
        "TIPO_INADEQUADO",
        "VALORES_AUSENTES",
    }

    return any(
        problema.get("codigo")
        in codigos_automaticos
        for problema in diagnostico.get(
            "problemas",
            [],
        )
    )


def _base_estruturalmente_apta(
    mapeamento: dict,
) -> bool:
    """
    Verifica se todos os dados necessários foram encontrados.
    """
    return (
        mapeamento.get("status")
        == "APTA"
    )


def _deve_executar_preparacao(
    diagnostico: dict,
    mapeamento: dict,
) -> bool:
    """
    Executa o MVP 5 quando a base possui os dados necessários.

    Isso permite:
    - Tratar problemas diagnosticados;
    - Padronizar datas;
    - Remover espaços;
    - Padronizar categorias.

    Bases estruturalmente incompletas não são preparadas,
    pois não possuem todos os dados necessários.
    """
    if not _base_estruturalmente_apta(
        mapeamento
    ):
        return False

    if _possui_acao_automatica(
        diagnostico
    ):
        return True

    # Uma base apta ainda pode receber normalizações
    # seguras associadas à finalidade.
    return True


# ==================================================
# PIPELINE PRINCIPAL
# ==================================================

def run_pipeline() -> pd.DataFrame:
    """
    Executa o pipeline dos MVPs 1 ao 5 sobre as bases
    declaradas em ARQUIVOS_TESTE.

    Retorna um DataFrame com o resumo final.
    """
    print("Módulos carregados com sucesso!\n")
    print(
        "Iniciando validação das bases de dados...\n"
    )

    resultados_finais = []

    for caminho in ARQUIVOS_TESTE:
        print(
            f"\nINICIANDO TESTE COM: {caminho}\n"
        )

        try:
            # ==========================================
            # MVP 1: CARREGAMENTO
            # ==========================================

            carga = load_data(caminho)
            df_original = carga["df"]

            print("METADADOS DE LEITURA")
            print(carga["metadata"])
            print()

            # ==========================================
            # MVP 2: PROFILING
            # ==========================================

            perfil_original = profile_data(
                df_original
            )

            # ==========================================
            # MVP 3: COMPARAÇÃO ESTRUTURAL
            # ==========================================

            mapeamento_original = (
                check_required_data(
                    perfil_original,
                    FINALIDADE_ID,
                )
            )

            print_analise_status(
                mapeamento_original
            )
            print()

            # ==========================================
            # MVP 4: DIAGNÓSTICO
            # ==========================================

            diagnostico_original = (
                run_diagnostic(
                    perfil_original,
                    mapeamento_original,
                )
            )

            print_diagnostic(
                diagnostico_original
            )

            status_original = (
                diagnostico_original["status"]
            )

            status_final = status_original
            qtd_transformacoes = 0
            qtd_pendencias = 0
            linhas_removidas = 0
            base_preparada = (
                df_original.copy(deep=True)
            )

            # ==========================================
            # MVP 5: PREPARAÇÃO
            # ==========================================

            if _deve_executar_preparacao(
                diagnostico_original,
                mapeamento_original,
            ):
                print()

                preparacao = prepare_data(
                    df_original,
                    diagnostico_original,
                    mapeamento_original,
                )

                base_preparada = preparacao["df"]

                print_preparation(
                    preparacao
                )

                resumo_preparacao = preparacao[
                    "resumo"
                ]

                qtd_transformacoes = (
                    resumo_preparacao[
                        "transformacoes_total"
                    ]
                )

                qtd_pendencias = (
                    resumo_preparacao[
                        "aplicadas_com_pendencias"
                    ]
                    + resumo_preparacao[
                        "problemas_nao_tratados"
                    ]
                )

                linhas_removidas = (
                    resumo_preparacao[
                        "linhas_removidas"
                    ]
                )

                # ======================================
                # REVALIDAÇÃO PÓS-PREPARAÇÃO
                # ======================================

                print("\n" + "=" * 50)
                print("REVALIDAÇÃO PÓS-PREPARAÇÃO")
                print("=" * 50)

                perfil_pos = profile_data(
                    base_preparada
                )

                mapeamento_pos = (
                    check_required_data(
                        perfil_pos,
                        FINALIDADE_ID,
                    )
                )

                diagnostico_pos = (
                    run_diagnostic(
                        perfil_pos,
                        mapeamento_pos,
                    )
                )

                status_final = diagnostico_pos[
                    "status"
                ]

                print(
                    f"Status antes da preparação: "
                    f"{status_original}"
                )

                print(
                    f"Status após a preparação: "
                    f"{status_final}"
                )

                if diagnostico_pos.get(
                    "problemas"
                ):
                    print(
                        "\nDiagnóstico após "
                        "a preparação:\n"
                    )

                    print_diagnostic(
                        diagnostico_pos
                    )

            else:
                print("\n" + "=" * 50)
                print("PREPARAÇÃO DE DADOS")
                print("=" * 50)
                print(
                    "Preparação automática não executada."
                )

                if (
                    mapeamento_original.get("status")
                    == "INCOMPLETA"
                ):
                    print(
                        "Motivo: a base não contém todos "
                        "os dados necessários para a "
                        "finalidade selecionada."
                    )
                else:
                    print(
                        "Motivo: não há transformação "
                        "automática aplicável."
                    )

            resultados_finais.append(
                {
                    "arquivo": caminho,
                    "status_antes": status_original,
                    "status_depois": status_final,
                    "transformacoes": (
                        qtd_transformacoes
                    ),
                    "pendencias": qtd_pendencias,
                    "linhas_antes": int(
                        len(df_original)
                    ),
                    "linhas_depois": int(
                        len(base_preparada)
                    ),
                    "linhas_removidas": (
                        linhas_removidas
                    ),
                }
            )

        except Exception as erro:
            print(
                "Erro ao processar a base: "
                f"{type(erro).__name__}: {erro}"
            )

            resultados_finais.append(
                {
                    "arquivo": caminho,
                    "status_antes": "ERRO",
                    "status_depois": "ERRO",
                    "transformacoes": 0,
                    "pendencias": 0,
                    "linhas_antes": 0,
                    "linhas_depois": 0,
                    "linhas_removidas": 0,
                }
            )

        print("\n" + "=" * 60 + "\n")

    print("\nRESUMO FINAL\n")

    df_resumo = pd.DataFrame(
        resultados_finais
    )

    print(
        df_resumo.to_string(index=False)
    )

    return df_resumo


# ==================================================
# INSPEÇÃO OPCIONAL DO PROFILING
# ==================================================

def run_inspection(
    caminho_inspecao: str = (
        "data/exemplo/vendas_kaggle.csv"
    ),
) -> None:
    """
    Exibe uma versão parcial do JSON de profiling.
    """
    try:
        carga = load_data(
            caminho_inspecao
        )

        df = carga["df"]
        perfil = profile_data(df)

        print(
            f"\nRadiografia da base: "
            f"{caminho_inspecao}\n"
        )

        json_saida = json.dumps(
            perfil,
            indent=4,
            ensure_ascii=False,
        )

        limite = 1000

        if len(json_saida) > limite:
            print(
                json_saida[:limite]
                + "\n\n"
                + "... [JSON TRUNCADO "
                + "PARA FACILITAR LEITURA]"
            )
        else:
            print(json_saida)

    except FileNotFoundError:
        print(
            "Para inspecionar o JSON, garanta "
            "que o arquivo informado existe."
        )

    except Exception as erro:
        print(
            "Não foi possível inspecionar a base: "
            f"{type(erro).__name__}: {erro}"
        )


# ==================================================
# EXECUÇÃO
# ==================================================

if __name__ == "__main__":
    run_pipeline()

    # Para executar a inspeção profunda:
    # run_inspection()