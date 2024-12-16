from flask import Flask, render_template
from flask_socketio import SocketIO
import uuid
import eventlet  # Adicionado para evitar o uso do servidor Werkzeug em execução

# Configuração do servidor Flask e SocketIO
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"
socket_io = SocketIO(app, cors_allowed_origins="*")

# Variáveis Globais
active_sessions = {}  # Mapeia session_id -> contexto do usuário


@app.route("/")
def index():
    """
    Rota principal que carrega uma página HTML simples.
    """
    return render_template("index.html")


@socket_io.on("connect")
def handle_connect():
    """
    Lida com a conexão do cliente.
    """
    # Gera um identificador único para a sessão
    session_id = str(uuid.uuid4())
    # Inicializa o contexto vazio para a sessão conectada
    active_sessions[session_id] = {"context": []}
    print(f"[INFO] Cliente conectado. Session ID: {session_id}")

    # Envia a mensagem inicial de boas-vindas para o cliente
    socket_io.emit("message", {
        "session_id": session_id,
        "content": "Bem-vindo ao atendimento! Envie sua primeira mensagem para começar.",
        "sender": {
            "name": "Sistema",
            "image": "https://via.placeholder.com/40?text=Sistema",
        },
    })


@socket_io.on("disconnect")
def handle_disconnect():
    """
    Lida com a desconexão do cliente.
    """
    print("[INFO] Cliente desconectado.")


@socket_io.on("start_session")
def handle_start_session(data):
    """
    Inicia uma nova sessão de usuário e armazena a mensagem inicial.
    """
    # Extraia os dados da mensagem para iniciar a sessão
    session_id = data.get("session_id")
    user_input = data.get("input", "Olá!")

    print(f"[INFO] Sessão iniciada com Session ID: {session_id}")

    # Verifica se o session_id existe no dicionário active_sessions
    if session_id not in active_sessions:
        # Inicializa a chave session_id caso não exista
        active_sessions[session_id] = {"context": []}

    # Inicializa o contexto do usuário com a mensagem inicial
    active_sessions[session_id]["context"] = [{"content": user_input, "source": "User"}]

    # Envia uma mensagem de confirmação ao cliente
    socket_io.emit("message", {
        "session_id": session_id,
        "content": f"Você disse: {user_input}",
        "sender": {
            "name": "Sistema",
            "image": "https://via.placeholder.com/40?text=Sistema",
        },
    })


@socket_io.on("user_message")
def handle_user_message(data):
    """
    Processa mensagens subsequentes enviadas pelo cliente.
    """
    # Extraia os dados da mensagem recebida
    session_id = data.get("session_id")
    user_input = data.get("message")

    if not session_id or session_id not in active_sessions:
        print(f"[ERRO] Session ID inválido: {session_id}")
        socket_io.emit("error", {"message": "Sessão inválida ou não iniciada."})
        return

    print(f"[INFO] Mensagem recebida da sessão {session_id}: {user_input}")

    # Obtém o contexto atual do usuário
    user_context = active_sessions[session_id]["context"]

    # Atualiza o contexto do usuário
    user_context.append({"content": user_input, "source": "User"})
    active_sessions[session_id]["context"] = user_context  # Reatribuição após a atualização

    # Gera uma resposta simples para o cliente
    response = generate_response(user_input)

    # Adiciona a resposta ao contexto
    user_context.append({"content": response, "source": "Bot"})
    active_sessions[session_id]["context"] = user_context

app.run(debug=True, port=8080)