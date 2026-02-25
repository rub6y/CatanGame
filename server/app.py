import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'catan-secret-key'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
MAX_PLAYERS = 4


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return data.get('users', [])
    return []


def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump({'users': users}, f)


@app.route('/')
def index():
    return render_template('index.html')


def get_user_by_name(users, name):
    for user in users:
        if user.get('name') == name:
            return user
    return None


def remove_user_by_name(users, name):
    return [u for u in users if u.get('name') != name]


@socketio.on('join')
def handle_join(data):
    name = data.get('name', '').strip()
    role = data.get('role', 'observer')

    if not name:
        return

    users = load_users()

    existing_user = get_user_by_name(users, name)
    if existing_user:
        users = remove_user_by_name(users, name)

    if role == 'player':
        player_count = sum(1 for u in users if u.get('role') == 'player')
        if player_count >= MAX_PLAYERS:
            emit('error', {'message': f'Cannot join as player. Max {MAX_PLAYERS} players allowed.'})
            return

    users.append({'name': name, 'role': role})
    save_users(users)

    emit_user_list()


@socketio.on('request_users')
def handle_request_users():
    emit_user_list()


def emit_user_list():
    users = load_users()
    players = [u for u in users if u.get('role') == 'player']
    observers = [u for u in users if u.get('role') == 'observer']
    emit('user_list', {'players': players, 'observers': observers}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    pass


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
