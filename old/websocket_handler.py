import os
import logging
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

azure_deployment = os.getenv("AZURE_OPENAI_API_VERSION")
key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_endpoint = os.getenv("AZURE_OPENAI_API_BASE")

async def start(session_id, user_input, socket_io):
    """
    Inicia o runtime ou envia mensagens do usuário para o agente.
    """
    # Exemplo de como interagir com o runtime do agente (ajuste conforme necessário).
    runtime = ...  # Obtenha o runtime do seu agente
    response = await runtime.publish_message(session_id, user_input)  # Envie para o agente

    # Após obter a resposta do agente, emita para o cliente Socket.IO.
    socket_io.emit('message', {'content': response, 'sender': 'Agente', 'session_id': session_id})
