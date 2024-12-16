import asyncio
import uuid

from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

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


async def main():
    runtime = SingleThreadedAgentRuntime()

    model_client = get_model_client()

    await register_triage_agent(runtime, model_client, None)
    await register_sales_agent(runtime, model_client, None)
    await register_issues_and_repairs_agent(runtime, model_client, None)
    await register_cancellation_agent(runtime, model_client, None)

    # Register the human agent.
    await register_human_agent(runtime)

    # Register the user agent.
    await register_user_agent(runtime)

    # Start the runtime.
    runtime.start()

    # Create a new session for the user.
    session_id = str(uuid.uuid4())
    await runtime.publish_message(UserLogin(), topic_id=TopicId(user_topic_type, source=session_id))

    # Run until completion.
    await runtime.stop_when_idle()


# Ensure `main()` is correctly executed with asyncio.
if __name__ == "__main__":
    asyncio.run(main())