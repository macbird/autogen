from autogen import config_list_from_json, GroupChatManager, GroupChat
from agents import AgentManager


def start(initial_msg) -> None:
    agent_manager = AgentManager()  # Inicializa o AgentManager

    # Obter o UserAgent
    user_proxy = agent_manager.user_agent

    # Obter a lista de AssistantAgents
    agents = agent_manager.agents

    # Verifica se o user_proxy foi criado
    if not user_proxy:
        print("Error: UserProxyAgent não encontrado.")
        return

    # Cria o GroupChat e o GroupChatManager usando o UserAgent e a lista de AssistantAgents
    groupchat = GroupChat(
        agents=agents,  # Combina o UserAgent com os AssistantAgents
        messages=[],
        max_round=20,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False
    )

    manager = GroupChatManager(groupchat=groupchat, llm_config=agent_manager.llm_config)

    # Inicia a conversa com o agente user_proxy
    user_proxy.initiate_chat(manager, message=initial_msg, silent=True, summary_method="reflection_with_llm")
