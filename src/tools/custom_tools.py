import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated, List, Dict, Any

import mysql
import mysql.connector
from autogen_core.tools import FunctionTool
from dotenv import load_dotenv
from mysql.connector import Error
from tavily import TavilyClient

# Carregar variáveis do arquivo `.env`
load_dotenv()

tavily = TavilyClient(api_key="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")


def search(query: Annotated[str, "The search query"]) -> Annotated[str, "The search results"]:
    result = tavily.get_search_context(query=query, search_depth="advanced")
    print(f"Tavily response: {result}")
    return result

def execute_sql(
        reflection: Annotated[str, "Think about what to do"],
        sql: Annotated[str, "SQL query"]
) -> Annotated[Dict[str, Any], "Dicionário com os resultados ou o erro"]:
    """
    Executa uma consulta SQL em um banco de dados MySQL e retorna resultados ou mensagens de erro.

    Args:
        reflection: Reflexão para fins de compatibilidade de anotação.
        sql: A consulta SQL a ser executada.

    Returns:
        Um dicionário com 'result' (sucesso) ou 'error' (erro).
    """
    # Configuração do banco MySQL — ajuste as credenciais
    db_config = {
        "host": "127.0.0.1",
        "user": "root",
        "password": "senha123",
        "database": "VivoSimulacao"
    }

    try:
        # Conecta ao banco de dados
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Executa a consulta SQL e obtém os resultados
        cursor.execute(sql)

        # Se a consulta for SELECT, obtém os resultados
        if sql.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()  # Lista de tuplas com os resultados
            columns = [desc[0] for desc in cursor.description]  # Nomes das colunas
            result_with_columns = [
                dict(zip(columns, row)) for row in result
            ]  # Converte os resultados em lista de dicionários
        else:
            connection.commit()  # Confirma a transação para operações DML (INSERT, UPDATE, DELETE)
            result_with_columns = {"message": "Query executed successfully."}

        return {
            "result": result_with_columns,
            "error": None
        }

    except Error as e:
        # Retorna o erro se houver falha no SQL ou na conexão
        return {
            "result": None,
            "error": f"Erro ao executar SQL: {str(e)}"
        }

    finally:
        # Fecha a conexão com o banco de dados
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


def get_database_structure() -> Annotated[Dict[str, Any], "Estrutura do banco de dados MySQL"]:
    """
    Retorna a estrutura do banco de dados conectado (tabelas e colunas).

    Returns:
        Um dicionário detalhando tabelas e colunas no banco de dados.
    """
    db_config = {
        "host": "127.0.0.1",
        "user": "root",
        "password": "senha123",  # Evitar armazenar senhas diretamente no código
        "database": "VivoSimulacao"
    }

    connection = None  # Inicializar a conexão como None
    try:
        # Abrindo conexão com banco de dados
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Para armazenar os detalhes do banco
        database_structure = {}

        # Listando as tabelas do banco
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()

        if not tables:  # Verificar se nenhuma tabela foi encontrada
            return {
                "result": None,
                "error": "Nenhuma tabela encontrada no banco de dados."
            }

        for (table_name,) in tables:  # Cada resultado é retornado como uma tupla
            cursor.execute(f"DESCRIBE {table_name};")  # Obtêm colunas para cada tabela
            columns = cursor.fetchall()
            database_structure[table_name] = []

            for column in columns:
                column_details = {
                    "Field": column[0],  # Nome da coluna
                    "Type": column[1],  # Tipo de dado
                    "Null": column[2],  # Pode ser nulo?
                    "Key": column[3],  # Chave primária/secundária
                    "Default": column[4],  # Valor padrão
                    "Extra": column[5]  # Informação extra, como auto_increment
                }
                database_structure[table_name].append(column_details)

        return {
            "result": database_structure,
            "error": None
        }

    except mysql.connector.Error as e:
        # Capturar erros específicos de conexão e operação
        return {
            "result": None,
            "error": f"Erro ao introspectar o banco de dados: {str(e)}"
        }

    finally:
        # Fechar conexão com o banco de dados, se aberta
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def buscar_assinaturas_ativas(cpf: str) -> Annotated[
    Dict[str, Any], "Busca partes das assinaturas ativas de um cliente baseado no CPF"]:
    """
    Busca assinaturas ativas no banco de dados para um cliente pelo CPF.
    """
    sql = f"""SELECT a.id_assinatura, c.id_cliente, c.nome_cliente, a.data_inicio, a.status, p.id_plano, p.nome_plano
                FROM assinaturas a
                         INNER JOIN clientes c ON a.id_cliente = c.id_cliente
                         INNER JOIN planos p ON a.id_plano = p.id_plano
                WHERE a.status = 'Ativo' AND c.cpf = '{cpf}';
            """
    return execute_sql("Buscar assinaturas ativas", sql)

def listar_planos() -> Annotated[Dict[str, Any], "Lista todas as opções de planos disponíveis"]:
    """
    Obtém a lista completa dos planos disponíveis no sistema.
    """
    sql = "SELECT id_plano, nome_plano FROM planos;"
    return execute_sql("Listar planos disponíveis", sql)
def cadastrar_cliente(nome: str, email: str, telefone: str, cpf: str, cidade: str, estado: str) -> Annotated[
    Dict[str, Any], "Cadastra um novo cliente no sistema"]:
    """
    Adiciona um novo cliente ao banco de dados.
    """
    sql = f"""
    INSERT INTO clientes (nome_cliente, email, telefone, cpf, cidade, estado)
    VALUES ('{nome}', '{email}', '{telefone}', '{cpf}', '{cidade}', '{estado}');
    """
    return execute_sql("Cadastrar novo cliente", sql)

def cadastrar_assinatura(id_cliente: int, id_plano: int) -> Annotated[
    Dict[str, Any], "Cria uma nova assinatura usando ID do cliente e ID do plano"]:
    """
    Registra uma nova assinatura para um cliente pelo ID.
    """
    sql = f"""
    INSERT INTO assinaturas (id_cliente, id_plano, data_inicio, status)
    VALUES ({id_cliente}, {id_plano}, CURDATE(), 'Ativo');
    """
    return execute_sql("Cadastrar nova assinatura", sql)

def cancelar_assinatura(id_cliente: int, id_plano: int) -> Annotated[
    Dict[str, Any], "Cancela uma assinatura ativa de um determinado cliente"]:
    """
    Cancela uma assinatura ativa de um cliente específico.
    """
    sql = f"""
    UPDATE assinaturas SET status = 'Cancelado'
    WHERE id_cliente = {id_cliente} AND id_plano = {id_plano};
    """
    return execute_sql("Cancelar assinatura", sql)
def buscar_faturas_abertas(cpf: str) -> Annotated[Dict[str, Any], "Localiza todas as faturas em aberto por CPF"]:
    """
    Busca faturas pendentes ou atrasadas de um cliente com base no CPF.
    """
    sql = f"""
    SELECT
        f.id_fatura, c.nome_cliente, f.mes_referencia, f.valor_total, f.data_vencimento, f.status_pagamento
    FROM faturas f
    INNER JOIN clientes c ON f.id_cliente = c.id_cliente
    WHERE
        f.status_pagamento = 'Pendente'
        AND f.data_vencimento < CURDATE()
        AND c.cpf = '{cpf}';
    """
    return execute_sql("Buscar faturas atrasadas", sql)


def send_email(receiver_email: str, subject: str, body: str, ) -> Annotated[
    Dict[str, Any], "Envia um email pra um destinatário"]:
    """
    Função que envia um e-mail usando o serviço SMTP.

    :param receiver_email: Endereço de e-mail do destinatário.
    :param subject: Assunto do e-mail.
    :param body: Corpo do e-mail em formato HTML.
    """
    import threading

    def send_email_background():
        # Recupera as credenciais do remetente a partir de variáveis de ambiente (boa prática)
        sender_email = os.getenv("SENDER_EMAIL", "no-reply@eva.bot")  # E-mail padrão caso a variável não exista
        sender_password = os.getenv("SENDER_PASSWORD",
                                    "eva@2018")  # Senha padrão para teste (não recomendado em produção)

        # Exibe informações principais
        print(f"Receiver: {receiver_email}")
        print(f"Subject: {subject}")

        # Configurar o MIME Multipart
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))  # Adiciona o texto ao e-mail como HTML

        try:
            # Configura a conexão SMTP (Zoho no exemplo)
            with smtplib.SMTP('smtp.zoho.com', 587) as server:
                server.ehlo()  # Inicia a conexão SMTP
                server.starttls()  # Ativa TLS para segurança
                server.ehlo()
                server.login(sender_email, sender_password)  # Faz login na conta
                server.sendmail(sender_email, receiver_email, msg.as_string())  # Envia o e-mail
                print("Email sent successfully.")
        except smtplib.SMTPAuthenticationError:
            print("Failed to send email: Authentication error. Please verify your email and password.")
        except smtplib.SMTPException as smtp_error:
            print(f"Failed to send email: SMTP error: {smtp_error}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    threading.Thread(target=send_email_background).start()


def criar_template_html_protocolo(nome_cliente: str, protocolo: str, reclamacao: str) -> str:
    """
    Cria um template HTML contendo o protocolo da reclamação, o nome do cliente e a descrição da reclamação.
    """
    template = f"""<!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Protocolo de Reclamação</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            h1 {{
                color: #333;
                font-size: 24px;
            }}
            p {{
                font-size: 14px;
                line-height: 1.6;
                color: #555;
            }}
            .highlight {{
                font-weight: bold;
                color: #000;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0;">
        <table align="center" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f9f9f9; padding: 20px 0;">
            <tr>
                <td>
                    <table cellpadding="0" cellspacing="0" width="600" align="center" style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                        <tr>
                            <td style="text-align: center;">
                                <h1 style="margin: 0;">Protocolo de Reclamação</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 0; font-size: 14px; color: #555;">
                                <p>Prezado(a) <span class="highlight">{nome_cliente}</span>,</p>
                                <p>Este é o seu protocolo referente à reclamação registrada:</p>
                                <p class="highlight" style="font-size: 16px;">Protocolo: {protocolo}</p>
                                <p>Descrição da reclamação:</p>
                                <p style="font-size: 14px; color: #333;">{reclamacao}</p>
                                <p>Agradecemos por entrar em contato conosco. Nossa equipe está trabalhando para resolver sua solicitação o mais breve possível.</p>
                                <p>Atenciosamente,</p>
                                <p>Equipe de Suporte</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>"""
    return template


def gerar_numero_protocolo() -> str:
    """
    Gera um número de protocolo único baseado no timestamp atual.

    :return: Número de protocolo no formato 'PROT-YYYYMMDD-HHMMSS-XXXX', onde 'XXXX' é um número aleatório de 4 dígitos.
    """
    from datetime import datetime
    import random

    # Obtém o timestamp atual
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Gera um número aleatório de 4 dígitos
    numero_aleatorio = random.randint(1000, 9999)
    # Monta o número do protocolo
    numero_protocolo = f"PROT-{timestamp}-{numero_aleatorio}"

    return numero_protocolo

import requests


def cancelar_assinatura_api(id_cliente: Annotated[int, "O id do cliente"], id_plano: Annotated[int, "O id do plano"]):
    url = "http://localhost:3000/assinaturas/cancelar"
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "Python Client"
    }
    data = {
        "clientId": id_cliente,
        "planId": id_plano
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Lança uma exceção para status de erro HTTP
        return response.json()  # Retorna a resposta em formato JSON
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consumir a API: {e}")
        return None

def buscar_assinaturas_ativas_api(cpf: str):
    url = f"http://localhost:3000/assinaturas?cpf={cpf}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "Python Client"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lança uma exceção para status de erro HTTP
        return response.json()  # Retorna a resposta em formato JSON
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consumir a API: {e}")
        return None

buscar_assinaturas_ativas_tool = FunctionTool(
    buscar_assinaturas_ativas,
    description="Encontra as assinaturas ativas de um cliente baseado no CPF fornecido.")

listar_planos_tool = FunctionTool(
    listar_planos,
    description="Lista todos os planos disponíveis no sistema Vivo.")

cadastrar_cliente_tool = FunctionTool(
    cadastrar_cliente,
    description="Cadastra um novo cliente no banco de dados com as informações fornecidas.")

cadastrar_assinatura_tool = FunctionTool(
    cadastrar_assinatura,
    description="Registra um novo contrato de assinatura para um cliente específico usando ID do cliente e do plano."
)

cancelar_assinatura_tool = FunctionTool(
    cancelar_assinatura,
    description="Cancela uma assinatura ativa de um cliente baseado nos IDs.")

buscar_faturas_abertas_tool = FunctionTool(
    buscar_faturas_abertas,
    description="Busca faturas atrasadas ou pendentes de clientes pelo CPF.")

search_tool = FunctionTool(search, description="Busca informações na internet.")
execute_sql_tool = FunctionTool(
    execute_sql,
    description="Ferramenta para executar consultas SQL em um banco MySQL."
)

execute_instrospect_tool = FunctionTool(
    get_database_structure,
    description="Ferramenta para introspect a base de dados."
)

send_email_tool = FunctionTool(
    send_email,
    description="Enviar um email com o protocolo da reclamação"
)

create_template = FunctionTool(
    criar_template_html_protocolo,
    description="Criar o body html com o protocolo da reclamação"
)
protocolo_tool = FunctionTool(
    gerar_numero_protocolo,
    description="Gera um protocolo de reclamação"
)

cancelar_assinatura_api_tool = FunctionTool(
    cancelar_assinatura_api,
    description="Cancela uma assinatura, deve ser passado id_cliente e id_plano"
)

busca_assinatura_api_tool = FunctionTool(
    buscar_assinaturas_ativas_api,
    description="Busca as assinaturas de um cliente passando seu cpf"
)