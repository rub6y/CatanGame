import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'catan-secret-key'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f).get('users', [])
    return []


def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump({'users': users}, f)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('join')
def handle_join(data):
    name = data.get('name', '')
    if not name:
        return

    users = load_users()
    if name not in users:
        users.append(name)
        save_users(users)

    emit('user_list', {'users': users}, broadcast=True)


@socketio.on('request_users')
def handle_request_users():
    users = load_users()
    emit('user_list', {'users': users})


@socketio.on('disconnect')
def handle_disconnect():
    pass


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
