from autogen_core import TypeSubscription
from autogen_core.models import SystemMessage

from src.agents.ai_agent import AIAgent
from src.tools.custom_tools import buscar_assinaturas_ativas_tool, buscar_faturas_abertas_tool, cancelar_assinatura_tool
from src.utils.topics import user_topic_type


async def register_admin_agent(runtime, model_client, websocket):
    admin_agent_type = await AIAgent.register(
        runtime,
        type="admin_agent_type",  # Você pode criar esse novo tipo em `topics` ou substituir por outro preexistente.
        factory=lambda: AIAgent(
            description="Um agente responsável por administrar assinaturas e resolver pendências financeiras.",
            system_message=SystemMessage(
                content="""
                            Você é um agente administrativo da Vivo.

                            Suas responsabilidades incluem:

                            1. Buscar informações sobre assinaturas ativas e histórico de produtos no sistema.  
                               - Certifique-se de verificar a situação detalhada e informar o cliente de maneira clara.

                            2. Verificar pendências financeiras e consultar faturas em aberto para clientes existentes.  
                               - Explique ao cliente como regularizar pendências, caso necessário.

                            3. Cancelar assinaturas quando solicitado, garantindo a comunicação clara sobre qualquer impacto no serviço.

                            **Seu foco é assegurar precisão nas buscas, clareza nas explicações e resolver problemas de forma eficiente!**
                            """
            ),
            model_client=model_client,
            tools=[buscar_assinaturas_ativas_tool, buscar_faturas_abertas_tool, cancelar_assinatura_tool],
            delegate_tools=[],
            agent_topic_type="admin_agent_type",  # Substituir aqui, se necessário.
            user_topic_type=user_topic_type,
            websocket=websocket,
            nome="Carlos - Setor Administrativo",
            avatar="https://img.freepik.com/fotos-premium/avatar-masculino-desenho-animado-de-pessoa-em-3d-suporte-ao-cliente_839035-194109.jpg?w=200"
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type="admin_agent_type", agent_type=admin_agent_type.type)
    )
    return admin_agent_type