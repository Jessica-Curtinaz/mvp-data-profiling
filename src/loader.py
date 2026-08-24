import csv
from pathlib import Path
import pandas as pd

class UnsupportedExtensionError(ValueError):
    """Exceção customizada para extensões não suportadas."""
    pass

def _load_csv(file_path: Path) -> dict:
    """
    Tenta inferir o delimitador e o encoding de um arquivo CSV.
    Retorna um dicionário com o DataFrame e os metadados de leitura para rastreabilidade.
    """
    encodings_para_testar = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings_para_testar:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                amostra = f.readline()
                try:
                    delimitador = csv.Sniffer().sniff(amostra).delimiter
                except csv.Error:
                    delimitador = ','
            
            df = pd.read_csv(file_path, sep=delimitador, encoding=encoding)
            
            # Validação contra falha silenciosa do csv.Sniffer (base com 1 coluna gigante)
            if len(df.columns) == 1:
                if delimitador != ';' and ';' in amostra:
                    delimitador = ';'
                    df = pd.read_csv(file_path, sep=delimitador, encoding=encoding)
                elif delimitador != ',' and ',' in amostra:
                    delimitador = ','
                    df = pd.read_csv(file_path, sep=delimitador, encoding=encoding)
            
            return {
                "df": df,
                "metadata": {
                    "extensao": ".csv",
                    "encoding": encoding,
                    "delimitador": delimitador
                }
            }
            
        except UnicodeDecodeError:
            # Ignora e tenta o próximo encoding da lista
            continue
            
    raise ValueError(
        f"Não foi possível ler o arquivo {file_path}. "
        f"Encodings tentados: {encodings_para_testar}"
    )

def load_data(file_path: str) -> dict:
    """
    Carrega um arquivo de dados (.csv ou .xlsx).
    Valida a existência do arquivo e se a extensão é suportada.
    Retorna um dicionário estruturado com o DataFrame e metadados.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        
    extensao = path.suffix.lower()
    
    if extensao == '.csv':
        return _load_csv(path)
    elif extensao == '.xlsx':
        df = pd.read_excel(path)
        return {
            "df": df,
            "metadata": {
                "extensao": ".xlsx",
                "encoding": "n/a", # Excel não usa encoding de texto simples
                "delimitador": "n/a" # Excel possui formato de células, não delimitador
            }
        }
    else:
        raise UnsupportedExtensionError(
            f"Extensão '{extensao}' não suportada. "
            "Utilize apenas arquivos .csv ou .xlsx."
        )