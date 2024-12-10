import asyncio
import json
import uuid
from typing import List, Tuple

from autogen_core import (
    FunctionCall,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from pydantic import BaseModel

from config import get_model_client
from functions import search_tool


class UserLogin(BaseModel):
    pass


class UserTask(BaseModel):
    context: List[LLMMessage]


class AgentResponse(BaseModel):
    reply_to_topic_type: str
    context: List[LLMMessage]

class AIAgent(RoutedAgent):
    def __init__(
            self,
            description: str,
            system_message: SystemMessage,
            model_client: AzureOpenAIChatCompletionClient,
            tools: List[Tool],
            delegate_tools: List[Tool],
            agent_topic_type: str,
            user_topic_type: str,
    ) -> None:
        super().__init__(description)
        self._system_message = system_message
        self._model_client = model_client
        self._tools = dict([(tool.name, tool) for tool in tools])
        self._tool_schema = [tool.schema for tool in tools]
        self._delegate_tools = dict([(tool.name, tool) for tool in delegate_tools])
        self._delegate_tool_schema = [tool.schema for tool in delegate_tools]
        self._agent_topic_type = agent_topic_type
        self._user_topic_type = user_topic_type


    @message_handler
    async def handle_task(self, message: UserTask, ctx: MessageContext) -> None:
        """
        Processa tarefas enviadas para este agente. Inclui o mecanismo de retry
        para chamadas ao modelo e delegação a outros agentes.
        """

        # Função de retry assíncrona utilitária
        async def retry_async(operation, max_retries=3, delay=2):
            for attempt in range(max_retries):
                try:
                    return await operation()
                except Exception as e:
                    print(f"Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        print("Todas as tentativas falharam.")
                        raise


        # Chamada do modelo com retry
        async def model_call():

            return await self._model_client.create(
                messages=[self._system_message] + message.context,
                tools=self._tool_schema + self._delegate_tool_schema,
                cancellation_token=ctx.cancellation_token,
            )

        try:
            llm_result = await retry_async(model_call, max_retries=5, delay=3)
        except Exception as e:
            print(f"Erro ao chamar o modelo após múltiplas tentativas: {e}")
            return  # Interrompe se o modelo falhar definitivamente.

        print(f"{'-' * 80}\n{self.id.type}:\n{llm_result.content}", flush=True)

        # Processa o resultado do modelo
        while isinstance(llm_result.content, list) and all(isinstance(m, FunctionCall) for m in llm_result.content):
            tool_call_results: List[FunctionExecutionResult] = []
            delegate_targets: List[Tuple[str, UserTask]] = []

            # Processa cada chamada de ferramenta do modelo
            for call in llm_result.content:
                arguments = json.loads(call.arguments)
                if call.name in self._tools:
                    # Executa a ferramenta diretamente com retry
                    async def tool_operation():
                        return await self._tools[call.name].run_json(arguments, ctx.cancellation_token)

                    try:
                        result = await retry_async(tool_operation, max_retries=3, delay=2)
                        result_as_str = self._tools[call.name].return_value_as_string(result)
                        tool_call_results.append(FunctionExecutionResult(call_id=call.id, content=result_as_str))
                    except Exception as e:
                        print(f"Erro ao executar a ferramenta {call.name}: {e}")
                        continue  # Ignora este call se falhar

                elif call.name in self._delegate_tools:
                    # Obtém o tipo de tópico do agente delegado
                    async def delegate_tool_operation():
                        return await self._delegate_tools[call.name].run_json(arguments, ctx.cancellation_token)

                    try:
                        result = await retry_async(delegate_tool_operation, max_retries=3, delay=2)
                        topic_type = self._delegate_tools[call.name].return_value_as_string(result)

                        # Cria o contexto para o agente delegado
                        delegate_messages = list(message.context) + [
                            AssistantMessage(content=[call], source=self.id.type),
                            FunctionExecutionResultMessage(
                                content=[
                                    FunctionExecutionResult(
                                        call_id=call.id,
                                        content=f"Transferred to {topic_type}. Adopt persona immediately."
                                    )
                                ]
                            ),
                        ]
                        delegate_targets.append((topic_type, UserTask(context=delegate_messages)))
                    except Exception as e:
                        print(f"Erro ao delegar para ferramenta {call.name}: {e}")
                        continue

                else:
                    raise ValueError(f"Ferramenta desconhecida: {call.name}")

            # Publica tarefas delegadas a outros agentes
            for topic_type, task in delegate_targets:
                async def delegate_operation():
                    await self.publish_message(task, topic_id=TopicId(topic_type, source=self.id.key))

                try:
                    await retry_async(lambda: delegate_operation(), max_retries=3, delay=2)
                    print(f"Delegando para {topic_type}")
                except Exception as e:
                    print(f"Erro ao delegar para {topic_type}: {e}")
                    continue

            # Integra resultados de ferramentas e faz nova chamada ao modelo
            if len(tool_call_results) > 0:
                print(f"{'-' * 80}\n{self.id.type}:\n{tool_call_results}", flush=True)
                message.context.extend(
                    [
                        AssistantMessage(content=llm_result.content, source=self.id.type),
                        FunctionExecutionResultMessage(content=tool_call_results),
                    ]
                )
                try:
                    llm_result = await retry_async(model_call, max_retries=3, delay=2)
                    print(f"{'-' * 80}\n{self.id.type}:\n{llm_result.content}", flush=True)
                except Exception as e:
                    print(f"Erro ao chamar o modelo após executar ferramentas: {e}")
                    return
            else:
                # A tarefa foi delegada e estamos finalizados
                return

        # Conclui a tarefa e publica o resultado final
        assert isinstance(llm_result.content, str)
        message.context.append(AssistantMessage(content=llm_result.content, source=self.id.type))
        await self.publish_message(
            AgentResponse(context=message.context, reply_to_topic_type=self._agent_topic_type),
            topic_id=TopicId(self._user_topic_type, source=self.id.key),
        )

class HumanAgent(RoutedAgent):
    def __init__(self, description: str, agent_topic_type: str, user_topic_type: str) -> None:
        super().__init__(description)
        self._agent_topic_type = agent_topic_type
        self._user_topic_type = user_topic_type

    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> None:
        human_input = input("Human agent input: ")
        print(f"{'-'*80}\n{self.id.type}:\n{human_input}", flush=True)
        message.context.append(AssistantMessage(content=human_input, source=self.id.type))
        await self.publish_message(
            AgentResponse(context=message.context, reply_to_topic_type=self._agent_topic_type),
            topic_id=TopicId(self._user_topic_type, source=self.id.key),
        )

class UserAgent(RoutedAgent):
    def __init__(self, description: str, user_topic_type: str, agent_topic_type: str) -> None:
        super().__init__(description)
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type

    @message_handler
    async def handle_user_login(self, message: UserLogin, ctx: MessageContext) -> None:
        print(f"{'-'*80}\nUser login, session ID: {self.id.key}.", flush=True)
        # Get the user's initial input after login.
        user_input = input("User: ")
        print(f"{'-'*80}\n{self.id.type}:\n{user_input}")
        await self.publish_message(
            UserTask(context=[UserMessage(content=user_input, source="User")]),
            topic_id=TopicId(self._agent_topic_type, source=self.id.key),
        )

    @message_handler
    async def handle_task_result(self, message: AgentResponse, ctx: MessageContext) -> None:
        # Get the user's input after receiving a response from an agent.
        user_input = input("User (type 'exit' to close the session): ")
        print(f"{'-'*80}\n{self.id.type}:\n{user_input}", flush=True)
        if user_input.strip().lower() == "exit":
            print(f"{'-'*80}\nUser session ended, session ID: {self.id.key}.")
            return
        message.context.append(UserMessage(content=user_input, source="User"))
        await self.publish_message(
            UserTask(context=message.context), topic_id=TopicId(message.reply_to_topic_type, source=self.id.key)
        )

def execute_order(product: str, price: int) -> str:
    print("\n\n=== Order Summary ===")
    print(f"Product: {product}")
    print(f"Price: ${price}")
    print("=================\n")
    confirm = input("Confirm order? y/n: ").strip().lower()
    if confirm == "y":
        print("Order execution successful!")
        return "Success"
    else:
        print("Order cancelled!")
        return "User cancelled order."

def look_up_item(search_query: str) -> str:
    item_id = "item_132612938"
    print("Found item:", item_id)
    return item_id

def execute_refund(item_id: str, reason: str = "not provided") -> str:
    print("\n\n=== Refund Summary ===")
    print(f"Item ID: {item_id}")
    print(f"Reason: {reason}")
    print("=================\n")
    print("Refund execution successful!")
    return "success"


execute_order_tool = FunctionTool(execute_order, description="Price should be in USD.")
search_tool = FunctionTool(search_tool, description="Price should be in USD.")
look_up_item_tool = FunctionTool(
    look_up_item, description="Use to find item ID.\nSearch query can be a description or keywords."
)
execute_refund_tool = FunctionTool(execute_refund, description="")

sales_agent_topic_type = "SalesAgent"
issues_and_repairs_agent_topic_type = "IssuesAndRepairsAgent"
triage_agent_topic_type = "TriageAgent"
human_agent_topic_type = "HumanAgent"
user_topic_type = "User"

def transfer_to_sales_agent() -> str:
    return sales_agent_topic_type


def transfer_to_issues_and_repairs() -> str:
    return issues_and_repairs_agent_topic_type


def transfer_back_to_triage() -> str:
    return triage_agent_topic_type


def escalate_to_human() -> str:
    return human_agent_topic_type


transfer_to_sales_agent_tool = FunctionTool(
    transfer_to_sales_agent, description="Use for anything sales or buying related."
)
transfer_to_issues_and_repairs_tool = FunctionTool(
    transfer_to_issues_and_repairs, description="Use for issues, repairs, or refunds."
)
transfer_back_to_triage_tool = FunctionTool(
    transfer_back_to_triage,
    description="Call this if the user brings up a topic outside of your purview,\nincluding escalating to human.",
)
escalate_to_human_tool = FunctionTool(escalate_to_human, description="Only call this if explicitly asked to.")


async def main():
    runtime = SingleThreadedAgentRuntime()

    model_client = get_model_client()

    # Register the triage agent.
    triage_agent_type = await AIAgent.register(
        runtime,
        type=triage_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(
            description="A triage agent.",

            system_message=SystemMessage(
                content="Você é um atendente de suporte ao cliente da Vivo. "
                        "Apresente-se brevemente perguntando o nome do cliente. "
                        "Sempre seja muito sucinto. "
                        "Use o nome do cliente durante a conversa para criar uma experiência mais personalizada. "
                        "Reúna informações para direcionar o cliente para o departamento correto. "
                        "Faça suas perguntas de forma sutil e natural."
                        "Execute buscas na internet usando search_tool pra buscar informações para cliente"
            )
            ,
            model_client=model_client,
            tools=[search_tool],
            delegate_tools=[
                transfer_to_issues_and_repairs_tool,
                transfer_to_sales_agent_tool,
                escalate_to_human_tool,
            ],
            agent_topic_type=triage_agent_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    # Add subscriptions for the triage agent: ele vai receber mensagens publicadas somente no tópico correspondente.
    await runtime.add_subscription(
        TypeSubscription(topic_type=triage_agent_topic_type, agent_type=triage_agent_type.type)
    )

    # Register the sales agent.
    sales_agent_type = await AIAgent.register(
        runtime,
        type=sales_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(

            description="Um agente de vendas.",

            system_message=SystemMessage(
                content="Você é um agente de vendas da Vivo."
                        "Sempre responda de forma sucinta e persuasiva."
                        "Siga esta rotina para fechar a venda de produtos da Vivo:"
                        "1. Identifique a necessidade exata do cliente relacionado aos serviços de telefonia ou internet.\n"
                        "2. Destaque um benefício exclusivo dos produtos da Vivo que atenda à necessidade mencionada.\n"
                        "3. Use a ferramenta search_tool para buscar dados atualizados para auxiliar na venda.\n"
                        "4. Ofereça uma solução personalizada e finalize a venda de forma clara e objetiva.\n"
                        "5. Certifique-se de que o cliente entende as vantagens e prossiga confirmando o pedido."
            )
            ,
            model_client=model_client,
            tools=[search_tool, execute_order_tool],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=sales_agent_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=sales_agent_topic_type, agent_type=sales_agent_type.type)
    )

    # Register the issues and repairs agent.
    issues_and_repairs_agent_type = await AIAgent.register(
        runtime,
        type=issues_and_repairs_agent_topic_type,  # Topic type como agent type.
        factory=lambda: AIAgent(
            description="An issues and repairs agent.",
            system_message=SystemMessage(
                content="You are a customer support agent for ACME Inc."
                        "Always answer in a sentence or less."
                        "Follow the following routine with the user:"
                        "1. First, ask probing questions and understand the user's problem deeper.\n"
                        " - unless the user has already provided a reason.\n"
                        "2. Propose a fix (make one up).\n"
                        "3. ONLY if not satisfied, offer a refund.\n"
                        "4. If accepted, search for the ID and then execute refund."
            ),
            model_client=model_client,
            tools=[
                execute_refund_tool,
                look_up_item_tool,
            ],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=issues_and_repairs_agent_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(
            topic_type=issues_and_repairs_agent_topic_type, agent_type=issues_and_repairs_agent_type.type
        )
    )

    # Register the human agent.
    human_agent_type = await HumanAgent.register(
        runtime,
        type=human_agent_topic_type,  # Topic type como agent type.
        factory=lambda: HumanAgent(
            description="A human agent.",
            agent_topic_type=human_agent_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=human_agent_topic_type, agent_type=human_agent_type.type)
    )

    # Register the user agent.
    user_agent_type = await UserAgent.register(
        runtime,
        type=user_topic_type,
        factory=lambda: UserAgent(
            description="A user agent.",
            user_topic_type=user_topic_type,
            agent_topic_type=triage_agent_topic_type,  # Start with the triage agent.
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type)
    )

    # Start the runtime.
    runtime.start()

    # Create a new session for the user.
    session_id = str(uuid.uuid4())
    await runtime.publish_message(UserLogin(), topic_id=TopicId(user_topic_type, source=session_id))

    # Run until completion.
    await runtime.stop_when_idle()

async def handle_agent_response(session_id, response, socket_io):
    """
    Envia a resposta do agente para o cliente.
    """
    socket_io.emit('message', {
        'content': response.content,
        'sender': 'Agente',
        'session_id': session_id
    })

# Coloque `main()` dentro de asyncio.run para assegurar o uso correto de await
if __name__ == "__main__":
    asyncio.run(main())