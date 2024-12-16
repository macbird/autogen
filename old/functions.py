import os
from typing import Annotated

from dotenv import load_dotenv
from tavily import TavilyClient

# Carregar variáveis do arquivo `.env`
load_dotenv()


tavily = TavilyClient(api_key="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")

import requests
def flight(origem:str, destino:str, data: str):
    access_key = '80186ddb7932e0d80ecc0b0cea14659e'
    url = 'http://api.aviationstack.com/v1/flights'
    params = {'access_key': access_key, 'dep_iata': origem, 'arr_iata': destino, 'flight_date': data}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()['data']
    else:
        return f"Erro na solicitação: {response.status_code}"

def compra_passagem(nome, email, data_nascimento, numero_passaporte):
    return {
        "nome": nome,
        "email": email,
        "data_nascimento": data_nascimento,
        "numero_passaporte": numero_passaporte
    }

def search_tool(query: Annotated[str, "The search query"]) -> Annotated[str, "The search results"]:
    result = tavily.get_search_context(query=query, search_depth="advanced")
    print(f"Tavily response: {result}")
    return result



def get_tool_function(tool_name):
    """Recupera uma função a partir do nome da ferramenta."""
    return TOOLS_MAP.get(tool_name)

def efetuar_venda(cpf: str, email:str, endereco: str, nome: str):
    print("efetuar venda")
    return "ok"

def send_email(email: str):
    print("send email")
    return "ok"

TOOLS_MAP = {
    "flight": flight,
    "compra_passagem": compra_passagem,
    "search_tool": search_tool,
    "efetuar_venda": efetuar_venda,
    "send_email": send_email,
    # Adicione mais mapeamentos de funções conforme necessário
}