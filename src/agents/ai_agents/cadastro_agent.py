from autogen_core import TypeSubscription
from autogen_core.models import SystemMessage

from src.agents.ai_agent import AIAgent
from src.tools.custom_tools import cadastrar_cliente_tool, cadastrar_assinatura_tool
from src.utils.topics import user_topic_type


async def register_cadastro_agent(runtime, model_client, websocket):
    cadastro_agent_type = await AIAgent.register(
        runtime,
        type="cadastro_agent_type",  # Você pode criar esse novo tipo em `topics` ou substituir conforme necessário.
        factory=lambda: AIAgent(
            description="Um agente de cadastro responsável por registrar novos clientes e atualizar dados.",
            system_message=SystemMessage(
                content="""
                            Você é um agente especializado no cadastro de novos clientes e atualização de assinaturas.

                            Suas principais responsabilidades incluem:

                            1. Solicitar e registrar as informações do cliente de forma progressiva e clara:  
                               Pergunte as informações necessárias uma de cada vez, como nome, e-mail, telefone, CPF, cidade e estado.

                            2. Atualizar dados para clientes existentes, conforme solicitado.

                            3. Realizar o cadastro de novas assinaturas no sistema, garantindo a integridade dos dados registrados.

                            4. Confirmar com o cliente se todos os dados estão corretos antes de finalizar o processo.

                            **Seu foco é garantir que cada cadastro ou atualização seja feito de forma precisa, eficiente e amigável!**
                            """
            ),
            model_client=model_client,
            tools=[cadastrar_cliente_tool, cadastrar_assinatura_tool],
            delegate_tools=[],
            agent_topic_type="cadastro_agent_type",  # Substituir aqui, se necessário.
            user_topic_type=user_topic_type,
            websocket=websocket,
            nome="Mariana - Setor de Cadastro",
            avatar="https://img.freepik.com/fotos-premium/avatar-feminino-desenho-animado-de-pessoa-em-3d-servico-ao-cliente_839035-194111.jpg?w=200"
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type="cadastro_agent_type", agent_type=cadastro_agent_type.type)
    )
    return cadastro_agent_type