from autogen_core import TypeSubscription

from src.agents.user_agent import UserAgent
from src.utils.topics import user_topic_type, triage_agent_topic_type


async def register_user_agent(runtime, websocket=None):
    user_agent_type = await UserAgent.register(
        runtime,
        type=user_topic_type,
        factory=lambda: UserAgent(
            description="A user agent.",
            user_topic_type=user_topic_type,
            agent_topic_type=triage_agent_topic_type,  # Start with the triage agent.
            websocket = websocket
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type)
    )
    return user_agent_type