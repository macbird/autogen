import json
import autogen
from autogen import config_list_from_json
from jinja2 import Environment, FileSystemLoader

from functions import get_tool_function

env = Environment(loader=FileSystemLoader('prompts'))


class AgentManager:
    def __init__(self, config_path="OAI_CONFIG_LIST.json", agents_json_path="agents.json"):
        self.agents_json_path = agents_json_path
        self.agents_data = None
        self.user_agent = None
        self.assistant_agents = None
        self.agents = None
        self.llm_config = None

        self.agents_data = self.load_agents_json(self.agents_json_path)

        # Certifique-se de que `config_list` seja uma lista de dicionários
        config_list = config_list_from_json(env_or_file=config_path)
        if not isinstance(config_list, list) or not all(isinstance(cfg, dict) for cfg in config_list):
            raise ValueError("config_list_from_json must return a list of dictionaries.")

        self.llm_config = {
            "cache_seed": 47,
            "temperature": 0,
            "config_list": config_list,
            "timeout": 120,
        }

        # Assegurando que o método possui o argumento necessário
        if self.agents_data and len(self.agents_data) > 0:
            self.user_agent = self.create_user_proxy(self.agents_data[0])
        self.assistant_agents = self.create_assistant_agents()
        self.agents = self.user_agent_as_list(self.user_agent) + self.assistant_agents

    def load_agents_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_agents_json(self):
        return self.agents_data

    def get_prompt(self, template_name):
        template = env.get_template(template_name)
        return template.render()

    def create_assistant_agents(self):
        agents = []
        for agent_data in self.agents_data:
            if agent_data["type"] == "AssistantAgent":
                agents.append(self.create_assistant_agent(agent_data))
        return agents

    def create_user_proxy(self, data):
        return autogen.UserProxyAgent(
            name="user_proxy",
            is_termination_msg=lambda msg: "TERMINATE" in msg["content"] if msg["content"] else False,
            human_input_mode="TERMINATE",
            code_execution_config=False,
            system_message="A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
        )

    def create_assistant_agent(self, data):
        agt = autogen.AssistantAgent(name=data["name"], llm_config=self.llm_config, system_message=data['prompt'],
                                     human_input_mode=data['human_input_mode'])

        tools = data.get("tools", [])
        for tool in tools:
            print(f"Registrando ferramenta: {tool}")
            tool_function = get_tool_function(tool['name'])
            if tool_function:  # Certifique-se de que a função existe antes de registrar
                agt.register_for_llm(name=tool['name'], description=tool['description'])(tool_function)
            else:
                print(f"Função para a ferramenta '{tool['name']}' não encontrada.")
        return agt

    def user_agent_as_list(self, user_agent):
        return [user_agent] if user_agent is not None else []

    def get_agent_data_by_name(self, name):
        for agent_data in self.agents_data:
            if agent_data["name"] == name:
                return agent_data
        return None

    def get_agent_by_name(self, name):
        agent_data = self.get_agent_data_by_name(name)
        if agent_data:
            if agent_data["type"] == "UserProxyAgent":
                return self.create_user_proxy(agent_data)
            elif agent_data["type"] == "AssistantAgent":
                return self.create_assistant_agent(agent_data)
        return None


# Uso do Manager
agent_manager = AgentManager()

# Acessar o UserAgent
user_agent = agent_manager.user_agent
if user_agent:
    print(f"User Agent criado: {user_agent.name}")

# Acessar a lista de Assistant Agents
assistant_agents = agent_manager.assistant_agents
print("Assistente Agents criados:")
for agent in assistant_agents:
    print(f"- {agent.name}")