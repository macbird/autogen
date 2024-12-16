import asyncio
import uuid

from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)
import websockets
from langtrace_python_sdk import langtrace

from src.agents.ai_agents.cancellation_agent import register_cancellation_agent
from src.agents.ai_agents.issu_repair_agent import register_issues_and_repairs_agent
from src.agents.ai_agents.sales_agent import register_sales_agent
from src.agents.ai_agents.triage_agent import register_triage_agent
from src.agents.human.agent import register_human_agent
from src.agents.responses import UserLogin
from src.agents.user.agent import register_user_agent
from src.common.websockt_manager import WebSocketManager
from src.config import get_model_client
from src.utils.topics import user_topic_type


async def start(websocket):
    runtime = SingleThreadedAgentRuntime()

    model_client = get_model_client()

    await register_triage_agent(runtime, model_client, websocket)
    await register_sales_agent(runtime, model_client, websocket)
    await register_issues_and_repairs_agent(runtime, model_client, websocket)
    await register_cancellation_agent(runtime, model_client, websocket)

    # Register the human agent.
    await register_human_agent(runtime)

    # Register the user agent.
    await register_user_agent(runtime, websocket)

    # Start the runtime.
    runtime.start()

    # Create a new session for the user.
    session_id = str(uuid.uuid4())
    await runtime.publish_message(UserLogin(), topic_id=TopicId(user_topic_type, source=session_id))

    # Run until completion.
    await runtime.stop_when_idle()


async def main():
    async with websockets.serve(start, "localhost", 5000):
        print("WebSocket server running on ws://localhost:5000")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())