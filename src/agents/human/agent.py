from autogen_core import TypeSubscription

from src.agents.human_agent import HumanAgent
from src.utils.topics import human_agent_topic_type, user_topic_type


async def register_human_agent(runtime):
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
