from autogen import config_list_from_json


def load_config():
    return config_list_from_json(env_or_file="OAI_CONFIG_LIST.json")