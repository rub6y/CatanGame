import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from game.game import Game

app = Flask(__name__)
app.config['SECRET_KEY'] = 'catan-secret-key'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
MAX_PLAYERS = 4
MIN_PLAYERS = 2
current_game = None


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


@socketio.on('start_game')
def handle_start_game():
    global current_game

    if current_game is not None and current_game.game_state == "started":
        emit('error', {'message': 'A game is already in progress'})
        return

    users = load_users()
    players = [u.get('name') for u in users if u.get('role') == 'player']

    if len(players) < MIN_PLAYERS:
        emit('error', {'message': f'Need at least {MIN_PLAYERS} players to start'})
        return

    current_game = Game(players)
    current_game.start()

    emit('game_started', {
        'players': current_game.players,
        'current_player': current_game.players[current_game.current_player_index]
    }, broadcast=True)


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
