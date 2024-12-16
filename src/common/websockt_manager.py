import uuid
from typing import List

from autogen_core import TopicId
from fastapi import WebSocket

from src.agents.responses import UserLogin
from src.utils.topics import user_topic_type


class WebSocketManager:
    def __init__(self, runtime):
        self.active_connections: List[WebSocket] = []
        self.runtime = runtime

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        session_id = str(uuid.uuid4())
        await self.runtime.publish_message(UserLogin(), topic_id=TopicId(user_topic_type, source=session_id))

        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        """Envie mensagem para um WebSocket específico."""
        print(f"try send message by user {message}")
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        print(f"try send message by broadcast {message}")

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Erro ao enviar mensagem para cliente: {e}")

