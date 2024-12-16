import json

from autogen_core import RoutedAgent, message_handler, MessageContext, TopicId
from autogen_core.models import UserMessage

from src.agents.responses import UserTask, UserLogin, AgentResponse
from flask_socketio import emit


class UserAgent(RoutedAgent):
    def __init__(self, description: str, user_topic_type: str, agent_topic_type: str, websocket=None) -> None:
        """
        Inicializa o UserAgent.
        :param description: Descrição do agente
        :param user_topic_type: Tipo de tópico para mensagens do usuário
        :param agent_topic_type: Tipo de tópico para mensagens do agente
        :param websocket: Instância opcional para eventos WebSocket em tempo real
        """
        super().__init__(description)
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type
        self.websocket = websocket  # WebSocket opcional para comunicação em tempo real

    @message_handler
    async def handle_user_login(self, message: UserLogin, ctx: MessageContext) -> None:
        """
        Lida com o evento de login do usuário, simulando a primeira mensagem inicial
        ou recebendo-a quando enviada por um WebSocket.
        """
        try:
            # Log de início de sessão
            print(f"{'-' * 80}\nUser login - session ID: {self.id.key}.", flush=True)

            if self.websocket:
                try:
                    # Recebe mensagem via WebSocket, caso disponível
                    user_input = await self.websocket.recv()
                    print(f"{'-' * 80}\n{self.id.type} recebeu uma mensagem:\n{user_input}")
                except Exception as ws_error:
                    print(f"Erro ao receber mensagem via WebSocket: {ws_error}")
                    user_input = "Mensagem inicial do usuário (fallback)"  # Define fallback em caso de erro no WebSocket


            # Publica a mensagem inicial no tópico apropriado
            await self.publish_message(
                UserTask(context=[UserMessage(content=user_input, source="User")]),
                topic_id=TopicId(self._agent_topic_type, source=self.id.key),
            )
            await self.sendMessage(user_input)

        except Exception as e:
            # Tratamento e notificação de erros
            print(f"❌ Ocorreu um erro: {e}")
            if self.websocket:
                try:
                    await self.websocket.send("Erro ao processar sua entrada. Tente novamente mais tarde.")
                except Exception as send_error:
                    print(f"Erro ao enviar mensagem de erro via WebSocket: {send_error}")
            # Fallback de notificação usando o Flask-SocketIO

    async def sendMessage(self, user_input):
        response = {
            "sender": {
                "type": "user",
                "name": "Voce",
                "image": "https://png.pngtree.com/png-vector/20210604/ourmid/pngtree-gray-avatar-placeholder-png-image_3416697.jpg"
            },
            "content": user_input
        }
        try:
            await self.websocket.send(json.dumps(response))
        except self.websocket.ConnectionClosed:
            print("Conexão Websocket fechada")

    @message_handler
    async def handle_task_result(self, message: AgentResponse, ctx: MessageContext) -> None:
        """
        Processa a resposta retornada por outro agente e solicita uma nova entrada do usuário
        em looping, até que a palavra-chave 'exit' seja recebida.
        """
        try:
            if self.websocket:
                try:
                    # Recebe mensagem via WebSocket, caso disponível
                    user_input = await self.websocket.recv()
                    print(f"{'-' * 80}\n{self.id.type} recebeu uma mensagem:\n{user_input}")
                except Exception as ws_error:
                    print(f"Erro ao receber mensagem via WebSocket: {ws_error}")
                    user_input = "Mensagem inicial do usuário (fallback)"  # Define fallback em caso de erro no WebSocket

            # Verifica a condição para encerrar a sessão
            if user_input.strip().lower() == "exit":
                print(f"{'-' * 80}\nUser session ended, session ID: {self.id.key}.")
                return

            # Adiciona a entrada do usuário ao contexto da mensagem
            message.context.append(UserMessage(content=user_input, source="User"))

            # Publica a mensagem atualizada no tópico relevante
            await self.publish_message(
                UserTask(context=message.context),
                topic_id=TopicId(message.reply_to_topic_type, source=self.id.key),
            )
            await self.sendMessage(user_input)
        except Exception as e:
            print(f"❌ Erro durante o processamento da tarefa: {e}")
            if self.websocket:
                await self.websocket.send("Erro interno ao processar sua mensagem. Tente novamente.")