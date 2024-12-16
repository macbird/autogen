from autogen_core import TypeSubscription
from autogen_core.models import SystemMessage

from src.agents.ai_agent import AIAgent
from src.utils.topics import triage_agent_topic_type, user_topic_type
from src.tools.delegate_tools import (
    transfer_to_cancellation_agent_tool,
    transfer_to_issues_and_repairs_tool,
    transfer_to_sales_agent_tool,
    escalate_to_human_tool,
)


async def register_triage_agent(runtime, model_client, websocket):
    triage_agent_type = await AIAgent.register(
        runtime,
        type=triage_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(
            description="A triage agent.",

            system_message=SystemMessage(

                content="Você é um atendente de suporte ao cliente da Vivo. "
                        "Responda apenas a perguntas relacionadas à Vivo e que estejam dentro das capacidades de seus agentes. "
                        "Apresente-se brevemente perguntando o nome do cliente. "
                        "Sempre seja muito sucinto. "
                        "Use o nome do cliente durante a conversa para criar uma experiência mais personalizada. "
                        "Reúna informações para direcionar o cliente para o departamento correto. "
                        "Faça suas perguntas de forma sutil e natural."
            )
            ,
            model_client=model_client,
            tools=[],
            delegate_tools=[
                transfer_to_cancellation_agent_tool,
                transfer_to_issues_and_repairs_tool,
                transfer_to_sales_agent_tool,
                escalate_to_human_tool,
            ],
            agent_topic_type=triage_agent_topic_type,
            user_topic_type=user_topic_type,
            websocket = websocket,
            nome = "VIVO",
            avatar= "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQa9LTRwY9js7KvxKd-lHD-LtWBKMD06O3BAziiHu7MkkE11eLTJZ2LZzXx4Fff2Khs1es&usqp=CAU"
        ),
    )
    # Add subscriptions for the triage agent: ele vai receber mensagens publicadas somente no tópico correspondente.
    await runtime.add_subscription(
        TypeSubscription(topic_type=triage_agent_topic_type, agent_type=triage_agent_type.type)
    )
    return triage_agent_type