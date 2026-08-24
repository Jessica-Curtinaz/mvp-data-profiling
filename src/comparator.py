import unicodedata
import re

# ==================================================
# CATÁLOGO DE ANÁLISES E ALIASES
# ==================================================

# Estrutura base de análises disponíveis
CATALOGO_ANALISES = {
    "faturamento_por_regiao": {
        "nome": "Faturamento por Região",
        "dados_necessarios": [
            "data_venda",
            "regiao",
            "valor_venda"
        ]
    }
}

# Mapeamento controlado de variações conhecidas (Aliases)
DICIONARIO_ALIASES = {
    "valor_venda": [
        "valor_venda", "valor total", "faturamento", 
        "sales amount", "vendas"
    ],
    "data_venda": [
        "data_venda", "data venda", "data da venda", 
        "sale date", "order date", "mes", "ano"
    ],
    "regiao": [
        "regiao", "uf", "estado", 
        "region", "unidade da federacao", "grande regiao"
    ]
}

# ==================================================
# FUNÇÕES DO MOTOR DE COMPARAÇÃO
# ==================================================

def normalize_name(name: str) -> str:
    """
    Normaliza o nome da coluna para facilitar o cruzamento:
    - Remove acentos
    - Converte para minúsculas
    - Remove espaços, underscores e hifens
    """
    if not isinstance(name, str):
        return ""
    # Remove acentos
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    # Minúsculas
    name = name.lower()
    # Remove espaços, underscores e hifens
    name = re.sub(r'[\s_\-]', '', name)
    return name

def check_required_data(profile: dict, analise_id: str) -> dict:
    """
    Cruza as colunas encontradas no profiling com os requisitos da análise.
    Retorna o mapeamento, colunas adicionais e status (APTA / INCOMPLETA).
    """
    analise = CATALOGO_ANALISES[analise_id]
    requisitos = analise["dados_necessarios"]
    
    # Extrai as colunas reais encontradas no MVP 2
    colunas_encontradas = [col["nome"] for col in profile["colunas"]]
    
    resultado = {
        "finalidade": analise["nome"],
        "status": "APTA",
        "mapeamento": [],
        "dados_adicionais": []
    }
    
    colunas_utilizadas = set()
    
    # 1. Verifica cada requisito
    for req in requisitos:
        encontrado = False
        coluna_correspondente = None
        
        # Pega a lista de aliases e já inclui o próprio nome do requisito
        aliases = DICIONARIO_ALIASES.get(req, [])
        aliases_normalizados = [normalize_name(a) for a in aliases + [req]]
        
        # Procura nas colunas da base
        for col_original in colunas_encontradas:
            if normalize_name(col_original) in aliases_normalizados:
                encontrado = True
                coluna_correspondente = col_original
                colunas_utilizadas.add(col_original)
                break # Achou, vai para o próximo requisito
                
        # Registra o resultado do mapeamento
        resultado["mapeamento"].append({
            "conceito": req,
            "status": "Encontrado" if encontrado else "NÃO encontrado",
            "coluna_base": coluna_correspondente
        })
        
        if not encontrado:
            resultado["status"] = "INCOMPLETA"
            
    # 2. Identifica colunas adicionais
    for col_original in colunas_encontradas:
        if col_original not in colunas_utilizadas:
            resultado["dados_adicionais"].append(col_original)
            
    return resultado

def print_analise_status(resultado: dict):
    """Função auxiliar para imprimir o resultado de forma legível no terminal/notebook."""
    print(f"FINALIDADE\n{resultado['finalidade']}\n")
    print("DADOS NECESSÁRIOS\n")
    
    for item in resultado["mapeamento"]:
        print(item["conceito"])
        print(f"→ {item['status']}")
        if item["coluna_base"]:
            print(f"→ Coluna: {item['coluna_base']}")
        print()
        
    if resultado["dados_adicionais"]:
        print("DADOS ADICIONAIS\n")
        for col in resultado["dados_adicionais"]:
            print(col)
        print()
        
    print(f"STATUS\n\n{resultado['status']}")

    