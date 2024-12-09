import os

import autogen

from tools import research, write_content

config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST.json"
)

brand_task = input("Por favor, insira o nome da marca ou empresa: ")
user_task = input("Por favor, insira seu objetivo, resumo ou declaração do problema: ")

llm_config_content_assistant = {
    "functions": [
        {
            "name": "research",
            "description": "research about a given topic, return the research material including reference links",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The topic to be researched about",
                        }
                    },
                "required": ["query"],
            },
        },
        {
            "name": "write_content",
            "description": "Write content based on the given research material & topic",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "research_material": {
                            "type": "string",
                            "description": "research material of a given topic, including reference links when available",
                        },
                        "topic": {
                            "type": "string",
                            "description": "The topic of the content",
                        }
                    },
                "required": ["research_material", "topic"],
            },
        },
    ],
    "config_list": config_list,
    "timeout": 120,
}

agency_manager = autogen.AssistantAgent(
    name="Agency_Manager",
    llm_config={"config_list": config_list},
    system_message=f'''
    Descreva passo a passo as tarefas para {brand_task} e {user_task} com a equipe.
    Atue como um centro de comunicação, mantendo entregas de alta qualidade e atualizando regularmente todos os stakeholders sobre o progresso.
    Encerre a conversa com "TERMINATE" quando todas as tarefas estiverem concluídas e nenhuma ação adicional for necessária.
    '''
)

agency_researcher = autogen.AssistantAgent(
    name="Agency_Researcher",
    llm_config=llm_config_content_assistant,
    system_message=f'''
    Utilize a função de pesquisa para reunir insights sobre {user_task}, tendências de mercado, pontos problemáticos dos usuários e dinâmicas culturais relevantes para o nosso projeto. 
    Concentre-se em fornecer informações claras e acionáveis. 
    Conclua sua participação com "TERMINATE" assim que toda a pesquisa relevante tiver sido fornecida e nenhuma análise adicional for necessária.
    ''',
)

agency_researcher.register_function(
    function_map={
        "research": research
    }
)

agency_strategist = autogen.AssistantAgent(
    name="Agency_Strategist",
    llm_config={"config_list": config_list},
    system_message=f'''
    Como Estrategista Chefe, sua principal tarefa é desenvolver briefings estratégicos para {brand_task}, guiado pelos objetivos de {user_task}.
    Utilize as percepções da Agency_Researcher para informar suas estratégias, concentrando-se no posicionamento da marca, mensagem principal e segmentação de público. 
    Garanta que seus briefings ofereçam perspectivas únicas e direção clara.
    Coordene-se de perto com o Agency_Manager para alinhamento com os objetivos do projeto. 
    Conclua com "TERMINATE" assim que a direção estratégica for estabelecida e comunicada.
    '''
)

agency_writer = autogen.AssistantAgent(
    name="Agency_Copywriter",
    llm_config={"config_list": config_list},
    system_message="""
    Como Redator Líder, sua função é criar narrativas e conteúdos atraentes.
    Concentre-se em entregar mensagens claras, envolventes e relevantes que ressoem com nosso público-alvo.
    Use sua criatividade para transformar insights estratégicos e achados de pesquisa em conteúdos impactantes.
    Certifique-se de que sua escrita mantenha a voz da marca e esteja alinhada com a estratégia geral do projeto.
    Seu objetivo é criar conteúdo que comunique efetivamente nossa mensagem e engaje o público.
    """
    ,
    function_map={
        "write_content": write_content,
    },
)

writing_assistant = autogen.AssistantAgent(
    name="writing_assistant",
    llm_config=llm_config_content_assistant,
    system_message="""
    Como assistente de escrita, seu papel envolve o uso da função de pesquisa para se manter atualizado sobre diversos tópicos e empregar a função write_content para produzir textos bem elaborados.  
    Garanta que seu material escrito seja informativo e bem estruturado, atendendo às necessidades específicas do tópico.  
    Conclua suas contribuições com "TERMINATE" após completar as tarefas de escrita conforme necessário.
    """
    ,
    function_map={
        "research": research,
        "write_content": write_content,
    },
)

agency_marketer = autogen.AssistantAgent(
    name="Agency_Marketer",
    llm_config={"config_list": config_list},
    system_message=f'''
    Como Líder de Marketing, utilize insights e estratégias para desenvolver ideias de marketing que envolvam nosso público-alvo.
    Para {user_task}, crie campanhas e iniciativas que transmitam claramente o valor da nossa marca.
    Concilie estratégia e execução, garantindo que nossa mensagem seja impactante e alinhada com nossa visão.
    Colabore com as equipes para uma abordagem unificada e coordene com o Gerente da Agência para alinhamento do projeto.
    Conclua com "TERMINATE" quando suas contribuições de marketing estiverem completas.
    '''
)

agency_mediaplanner = autogen.AssistantAgent(
    name="Agency_Media_Planner",
    llm_config={"config_list": config_list},
    system_message=f'''
    Como Planejador de Mídia Líder, sua tarefa é identificar o mix de mídia ideal para entregar nossas mensagens publicitárias, visando o público do cliente.
    Utilize a função de pesquisa para se manter atualizado sobre canais e táticas de mídia atuais e eficazes.
    Aplique insights de {user_task} para formular estratégias que alcancem efetivamente o público através de vários meios, tanto tradicionais quanto digitais.
    Colabore de perto com o Gerente da Agência para garantir que seus planos estejam alinhados com a estratégia mais ampla do usuário.
    Conclua seu papel com "TERMINATE" uma vez que o planejamento de mídia esteja completo e alinhado.
    '''
)

agency_director = autogen.AssistantAgent(
    name="Agency_Director",
    llm_config={"config_list": config_list},
    system_message="""
    Como Diretor Criativo, sua função é supervisionar os aspectos criativos do projeto. 
    Avalie criticamente todo o trabalho, garantindo que cada ideia não seja apenas única, mas também alinhada com nossos padrões de excelência. 
    Incentive a equipe a inovar e explorar novos caminhos criativos. 
    Colabore de perto com o Gerente da Agência para consistência de alinhamento com o representante do usuário. 
    Conclua sua orientação com "TERMINATE" assim que você tenha garantido a integridade criativa e o alinhamento do projeto.
    """
    ,
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"] if msg["content"] else False,
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=1,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False
    },
    system_message='Be a helpful assistant.',
)

groupchat = autogen.GroupChat(agents=[
    user_proxy, agency_manager, agency_researcher, agency_strategist, agency_writer, writing_assistant, agency_marketer, agency_mediaplanner, agency_director],
    messages=[],
    max_round=20
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config={"config_list": config_list}
)
user_proxy.initiate_chat(
    manager,
    message=user_task,
)