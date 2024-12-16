
import asyncio
import json
from typing import List, Tuple

from autogen_core import (
    FunctionCall,
    MessageContext,
    RoutedAgent,
    TopicId,
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
from autogen_core.tools import Tool
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from pydantic import BaseModel


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