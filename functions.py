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

TOOLS_MAP = {
    "flight": flight,
    "compra_passagem": compra_passagem,
    # Adicione mais mapeamentos de funções conforme necessário
}


def get_tool_function(tool_name):
    """Recupera uma função a partir do nome da ferramenta."""
    return TOOLS_MAP.get(tool_name)