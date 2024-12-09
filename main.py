import logging

from autogen import GroupChatManager
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from agents import agent_manager
from websocket_handler import start

app = Flask(__name__)
CORS(app)
socket_io = SocketIO(app)


def new_print_receveid_messages(self, message, sender):
    logging.info(f"Message received: {message}")

    content = message.get('content', 'No content') if isinstance(message, dict) else message

    # Verifica se 'sender' tem o atributo 'name', caso contrário assume que 'sender' é uma string
    sender_name = sender.name if hasattr(sender, 'name') else sender
    print(f"PATCHED {sender_name}: {content}")

    # Assume que 'agent_manager.get_agent_data_by_name' aceita 'sender_name' como argumento
    agent_info = agent_manager.get_agent_data_by_name(sender_name)
    print(f"agent {agent_info}")

    if agent_info is not None:
        socket_io.emit('message', {
            "sender": {
                "name": agent_info['nome'],  # Ajustado para acessar a propriedade 'nome' correta
                "image": agent_info['image']
            },
            "content": content
        })
    else:
        print(f"Agent with name {sender_name} not found. Cannot access agent's name.")
        socket_io.emit('message', {
            "sender": {
                "name": "Unknown"
            },
            "content": content
        })


GroupChatManager._print_received_message = new_print_receveid_messages


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def run():
    input_data = request.json.get('input')
    start(input_data)  # Ensure the start function uses input_data if applicable
    return jsonify({'message': 'Started'}), 201


app.run(debug=True, port=8080)