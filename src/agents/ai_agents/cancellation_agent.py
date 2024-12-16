from autogen_core import TypeSubscription
from autogen_core.models import SystemMessage

from src.agents.ai_agent import AIAgent
from src.tools.custom_tools import busca_assinatura_api_tool, cancelar_assinatura_api_tool
from src.tools.delegate_tools import transfer_back_to_triage_tool
from src.utils.topics import cancellation_agent_topic_type, user_topic_type


async def register_cancellation_agent(runtime, model_client, websocket):
    cancellation_agent_type = await AIAgent.register(
        runtime,
        type=cancellation_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(
            description="An agent responsible for plan and service cancellations.",
            system_message=SystemMessage(

                content="""
                        Você é um agente responsável por cancelamento de planos e serviços da Vivo. 
                        Siga a seguinte rotina com o usuário: 
                        
                        1. Busque as assinaturas ativas do cliente utilizando a ferramenta `busca_assinatura_api_tool`. 
                           Certifique-se de fornecer as informações necessárias para a função, como CPF ou outro identificador solicitado pela ferramenta.
                        
                        2. Apresente ao cliente a lista de assinaturas ativas, indicando claramente os detalhes de cada assinatura:
                           - Nome do plano.
                           - Status do plano.
                           - Outros detalhes relevantes (como data de início ou ID do cliente, se disponíveis).
                        
                        3. Após apresentar as informações, pergunte ao cliente qual assinatura deve ser cancelada e aguarde a confirmação.
                        
                        4. Extraia o identificador da assinatura (por exemplo, `id_plano` e o `id_cliente`) do retorno da ferramenta 
                           `buscar_assinaturas_ativas_api` com base na escolha do cliente.
                        
                        5. Realize o cancelamento da assinatura escolhida utilizando a função `cancelar_assinatura_api_tool`, 
                           certificando-se de passar exatamente os argumentos esperados no formato correto, por exemplo: 
                           `{"id_cliente": <id_cliente>, "id_plano": <id_plano>}`. Caso o backend exija informações adicionais, como CPF ou token de autenticação, inclua esses campos 
                           nos argumentos.
                        
                        6. Após a execução da ferramenta, capture o resultado e informe ao cliente se o cancelamento foi bem-sucedido. 
                           Em caso de erro, comunique claramente que não foi possível concluir a ação no momento e peça para tentar novamente mais tarde ou 
                           entre em contato com suporte humano.
                        
                        7. Finalize a interação de maneira clara e profissional, garantindo que o cliente esteja satisfeito com o atendimento.
                        """
            ),
            model_client=model_client,
            tools=[
                busca_assinatura_api_tool, cancelar_assinatura_api_tool
            ],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=cancellation_agent_topic_type,
            user_topic_type=user_topic_type,
            websocket = websocket,
            nome = "Vick - Setor de cancelamento VIVO",
            avatar = "https://img.freepik.com/fotos-gratis/retrato-de-mulher-de-negocios-sorridente-com-oculos-e-fones-de-ouvido-em-fundo-cinzento_1142-54747.jpg"
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(
            topic_type=cancellation_agent_topic_type, agent_type=cancellation_agent_type.type
        )
    )
