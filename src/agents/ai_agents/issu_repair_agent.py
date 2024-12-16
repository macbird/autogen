from autogen_core import TypeSubscription
from autogen_core.models import SystemMessage

from src.agents.ai_agent import AIAgent
from src.tools.custom_tools import search_tool, protocolo_tool, create_template, send_email_tool
from src.tools.delegate_tools import transfer_back_to_triage_tool
from src.utils.topics import issues_and_repairs_agent_topic_type, user_topic_type


async def register_issues_and_repairs_agent(runtime, model_client, websocket):
    # Register the issues and repairs agent.
    issues_and_repairs_agent_type = await AIAgent.register(
        runtime,
        type=issues_and_repairs_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(
            description="An issues and repairs agent.",
            system_message=SystemMessage(

                content="""
                            Você é um agente de suporte ao cliente da Vivo.
                            Siga a seguinte rotina com o usuário:
                            1. Coleta de informações: Faça perguntas de sondagem para entender detalhadamente o problema do usuário, 
                               e utilize recursos da internet para obter know-how e informações adicionais sobre o problema.
                            2. Coleta de e-mail: Certifique-se de coletar o e-mail do cliente durante a conversa para envio do protocolo.
                            3. Proponha soluções: Baseando-se nas informações coletadas e na pesquisa realizada, sugira soluções claras e objetivas para o problema.
                            4. Registro de protocolo: Após apresentar a solução, registre o protocolo da reclamação utilizando a função `protocolo_tool`
                               para acompanhamento, informando o usuário sobre o número do protocolo gerado.
                            5. Envio de e-mail: Após registrar o protocolo, utilize a função `create_template` para montar o corpo do e-mail contendo a reclamação 
                               e o número do protocolo no formato HTML. Envie o e-mail com as informações de forma organizada e clara.
                            """
            ),
            model_client=model_client,
            tools=[
                search_tool, protocolo_tool, create_template, send_email_tool
            ],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=issues_and_repairs_agent_topic_type,
            user_topic_type=user_topic_type,
            websocket = websocket,
            nome = "Andre - Suporte tecnico VIVO",
            avatar = "https://png.pngtree.com/png-vector/20231014/ourlarge/pngtree-3d-customer-service-operator-png-illustration-png-image_10160272.png"
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(
            topic_type=issues_and_repairs_agent_topic_type, agent_type=issues_and_repairs_agent_type.type
        )
    )
    return issues_and_repairs_agent_type