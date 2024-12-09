import os
import requests
import dotenv
from bs4 import BeautifulSoup
import json
import autogen
from langchain_community.chat_models import  AzureChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate

dotenv.load_dotenv()
BROWSERLESS_API_KEY = os.getenv("BROWSERLESS_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST.json"
)


def search(query):
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": query
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()


def scrape(url: str):
    """Scrape a website and summarize its content if it's too large."""
    print("Scraping website...")

    # Define the headers for the request
    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
        'apikey': os.getenv("SCRAPERAPI_KEY")
    }

    # Build the GET URL with ScraperAPI
    get_url = f"http://api.scraperapi.com?api_key={os.getenv('SCRAPERAPI_KEY')}&url={url}"

    # Send the GET request
    response = requests.get(get_url, headers=headers)

    # Check the response status code
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()
        print("CONTENT:", text)

        if len(text) > 8000:
            output = summary(text)
            return output
        else:
            return text
    else:
        print(f"HTTP request failed with status code {response.status_code}")


def summary(content):
    llm = AzureChatOpenAI(temperature=0, model="gpt-4o")
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"], chunk_size=10000, chunk_overlap=500)
    docs = text_splitter.create_documents([content])
    map_prompt = """
    Write a detailed summary of the following text for a research purpose:
    "{text}"
    SUMMARY:
    """
    map_prompt_template = PromptTemplate(
        template=map_prompt, input_variables=["text"])

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type='map_reduce',
        map_prompt=map_prompt_template,
        combine_prompt=map_prompt_template,
        verbose=True
    )

    output = summary_chain.run(input_documents=docs, )

    return output


def research(query):
    llm_config_researcher = {
        "functions": [
            {
                "name": "search",
                "description": "google search for relevant information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Google search query",
                        }
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "scrape",
                "description": "Scraping website content based on url",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website url to scrape",
                        }
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "flight",
                "description": "Search flights into api",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origem": {
                            "type": "string",
                            "description": "IATA code of the departure airport",
                        },
                        "destino": {
                            "type": "string",
                            "description": "IATA code of the arrival airport",
                        },
                        "data": {
                            "type": "string",
                            "description": "Date of the flight in YYYY-MM-DD format",
                        },
                    },
                    "required": ["origem", "destino", "data"],
                },
            }
        ],
        "config_list": config_list}

    researcher = autogen.AssistantAgent(
        name="researcher",
        system_message="Research about a given query, collect as many information as possible, and generate detailed research results with loads of technique details with all reference links attached; Add TERMINATE to the end of the research report;",
        llm_config=llm_config_researcher,
    )

    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        code_execution_config={
            "system_message": "last_n_messages",
            "max_consecutive_auto_reply": 2,
            "work_dir": "coding",
            "use_docker": False
        },
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="TERMINATE",
        function_map={
            "search": search,
            "scrape": scrape,
        }
    )

    user_proxy.initiate_chat(researcher, message=query)

    # set the receiver to be researcher, and get a summary of the research report
    user_proxy.stop_reply_at_receive(researcher)
    user_proxy.send(
        "Give me the research report that just generated again, return ONLY the report & reference links", researcher)

    # return the last message the expert received
    return user_proxy.last_message()["content"]


def write_content(research_material, topic):
    editor = autogen.AssistantAgent(
        name="editor",
        description="Seasoned editor skilled in structuring blog posts for clarity and coherence, using material from the Research Assistant.",
        system_message='''
        Welcome, Senior Editor.
        As a seasoned professional, you bring meticulous attention to detail, a deep appreciation for literary and cultural nuance, and a commitment to upholding the highest editorial standards. 
        Your role is to craft the structure of a short blog post using the material from the Research Assistant. Use your experience to ensure clarity, coherence, and precision. 
        Once structured, pass it to the Writer to pen the final piece.
        ''',
        llm_config={"config_list": config_list},
    )

    writer = autogen.AssistantAgent(
        name="writer",
        description="Blogger tasked with composing short blog posts using the structure from the Editor, embodying clear, concise, and journalistic style.",
        system_message='''
        Welcome, Blogger.
        Your task is to compose a short blog post using the structure given by the Editor and incorporating feedback from the Reviewer. 
        Embrace stylistic minimalism: be clear, concise, and direct. 
        Approach the topic from a journalistic perspective; aim to inform and engage the readers without adopting a sales-oriented tone. 
        After two rounds of revisions, conclude your post with "TERMINATE".
        ''',
        llm_config={"config_list": config_list},
    )

    reviewer = autogen.AssistantAgent(
        name="reviewer",
        description="Expert blog content critic focused on reviewing and providing feedback to ensure the highest standards of editorial excellence.",
        system_message='''
        As a distinguished blog content critic, you are known for your discerning eye, deep literary and cultural understanding, and an unwavering commitment to editorial excellence. 
        Your role is to meticulously review and critique the written blog, ensuring it meets the highest standards of clarity, coherence, and precision. 
        Provide invaluable feedback to the Writer to elevate the piece. After two rounds of content iteration, conclude with "TERMINATE".
        ''',
        llm_config={"config_list": config_list},
    )

    user_proxy = autogen.UserProxyAgent(
        name="admin",
        system_message="A human admin. Interact with editor to discuss the structure. Actual writing needs to be approved by this admin.",
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"] if msg["content"] else False,
        human_input_mode="TERMINATE",
    )

    groupchat = autogen.GroupChat(
        agents=[user_proxy, editor, writer, reviewer],
        messages=[],
        max_round=10)

    manager = autogen.GroupChatManager(groupchat=groupchat)
    user_proxy.initiate_chat(
        manager, message=f"Write a blog about {topic}, here are the material: {research_material}")

    user_proxy.stop_reply_at_receive(manager)
    user_proxy.send(
        "Give me the blog that just generated again, return ONLY the blog, and add TERMINATE in the end of the message",
        manager)

    # return the last message the expert received
    return user_proxy.last_message()["content"]


def flight(origem, destino, data):
    # Substitua 'YOUR_ACCESS_KEY' pela sua chave de acesso da API
    access_key = '80186ddb7932e0d80ecc0b0cea14659e'
    url = 'http://api.aviationstack.com/v1/flights'

    # Parâmetros da consulta
    params = {
        'access_key': access_key,
        'dep_iata': origem,
        'arr_iata': destino,
        'flight_date': data,
    }

    print(f"Parâmetros da requisição: origem={origem}, destino={destino}, data={data}")

    # Solicitação GET para a API
    response = requests.get(url, params=params)

    # Verifica se a resposta foi bem sucedida
    if response.status_code == 200:
        dados_voo = response.json()
        return dados_voo['data']  # Retorna os dados dos voos
    else:
        return f"Erro na solicitação: {response.status_code}"
