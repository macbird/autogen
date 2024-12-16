import os

from dotenv import load_dotenv

# Carregar variáveis do arquivo `.env`
load_dotenv()
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient


def get_model_client():
    azure_deployment = os.getenv("AZURE_OPENAI_API_VERSION")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    azure_endpoint = os.getenv("AZURE_OPENAI_API_BASE")

    print("AZURE_OPENAI_API_VERSION:", os.getenv("AZURE_OPENAI_API_VERSION"))

    # Verifica se as variáveis estão definidas
    if not all([azure_deployment, key, api_version, azure_endpoint]):
        raise ValueError(
            "Credenciais do Azure OpenAI estão faltando. Por favor, defina as variáveis de ambiente apropriadas."
        )

    # Configura o cliente AzureOpenAI
    return AzureOpenAIChatCompletionClient(
        model="gpt-4o",
        api_key=key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )



