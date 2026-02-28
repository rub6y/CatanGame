import json
import os
import random
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

COLOR_PALETTE = [
    '#3498db',  # Blue
    '#27ae60',  # Green
    '#f1c40f',  # Yellow
    '#e74c3c',  # Red
    '#9b59b6',  # Purple
    '#e67e22',  # Orange
    '#ff6b9d',  # Pink
    '#ecf0f1',  # White
    '#2c3e50',  # Black
]


def get_random_color():
    """Get a random color from the palette."""
    return random.choice(COLOR_PALETTE)


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return data.get('users', [])
    return []


def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump({'users': users}, f)


def get_user_by_name(users, name):
    for user in users:
        if user.get('name') == name:
            return user
    return None


def remove_user_by_name(users, name):
    return [u for u in users if u.get('name') != name]


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('join')
def handle_join(data):
    name = data.get('name', '').strip()
    role = data.get('role', 'observer')

    if not name:
        return

    reconnecting_to_game = False

    if current_game is not None and current_game.game_state == "started":
        if current_game.is_player(name):
            role = "player"
            reconnecting_to_game = True
        else:
            role = "observer"
            current_game.add_observer(name)
            reconnecting_to_game = True

    users = load_users()

    existing_user = get_user_by_name(users, name)
    if existing_user:
        users = remove_user_by_name(users, name)
        color = existing_user.get('color')
    else:
        color = get_random_color()

    if role == 'player':
        player_count = sum(1 for u in users if u.get('role') == 'player')
        if player_count >= MAX_PLAYERS:
            emit('error', {'message': f'Cannot join as player. Max {MAX_PLAYERS} players allowed.'})
            return

    users.append({'name': name, 'role': role, 'color': color})
    save_users(users)

    emit_user_list()

    if reconnecting_to_game:
        current_player = current_game.players[current_game.current_player_index]
        emit('game_state', {
            'players': current_game.get_player_names(),
            'observers': current_game.observers,
            'current_player': current_player.name if current_player else None,
            'board': current_game.get_board_data()
        })


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
    observers = [u.get('name') for u in users if u.get('role') == 'observer']
    
    # Build player colors dict from users
    player_colors = {}
    for u in users:
        if u.get('role') == 'player' and u.get('color'):
            player_colors[u.get('name')] = u.get('color')

    if len(players) < MIN_PLAYERS:
        emit('error', {'message': f'Need at least {MIN_PLAYERS} players to start'})
        return

    current_game = Game(players, observers, player_colors)
    current_game.start()

    current_player = current_game.players[current_game.current_player_index]
    emit('game_started', {
        'players': current_game.get_player_names(),
        'observers': current_game.observers,
        'current_player': current_player.name if current_player else None,
        'board': current_game.get_board_data()
    }, broadcast=True)


@socketio.on('next_turn')
def handle_next_turn(data):
    if current_game is None or current_game.game_state != "started":
        return

    current_player = current_game.players[current_game.current_player_index]
    current_player_name = current_player.name if current_player else None
    requester = data.get('name')

    if requester != current_player_name:
        emit('error', {'message': f'Only {current_player_name} can advance the turn'})
        return

    current_game.current_player_index = (current_game.current_player_index + 1) % len(current_game.players)
    new_current_player = current_game.players[current_game.current_player_index]
    new_current_player_name = new_current_player.name if new_current_player else None
    print(f"Turn changed. Current player: {new_current_player_name}")

    emit('turn_changed', {
        'players': current_game.get_player_names(),
        'observers': current_game.observers,
        'current_player': new_current_player_name
    }, broadcast=True)


@socketio.on('set_color')
def handle_set_color(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    color = data.get('color', '')
    
    if not name or not color:
        return
    
    if current_game.set_player_color(name, color):
        emit('player_color_changed', {
            'name': name,
            'color': color
        }, broadcast=True)
        
        # Save color to users.json
        users = load_users()
        for user in users:
            if user.get('name') == name:
                user['color'] = color
                break
        save_users(users)


@socketio.on('roll_dice')
def handle_roll_dice(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    
    if not name:
        return
    
    current_player = current_game.players[current_game.current_player_index]
    if current_player.name != name:
        emit('error', {'message': f'Only {current_player.name} can roll dice'})
        return
    
    import random
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2
    
    print(f"Player {name} rolled {dice1} + {dice2} = {total}")
    
    current_game.distribute_resources(total)
    
    emit('dice_rolled', {
        'player': name,
        'dice1': dice1,
        'dice2': dice2,
        'total': total
    }, broadcast=True)
    
    emit('board_updated', {
        'board': current_game.get_board_data(),
        'highlight': total
    }, broadcast=True)


@socketio.on('place_settlement')
def handle_place_settlement(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    vertex_key = data.get('vertex', '')
    
    if not name or not vertex_key:
        return
    
    # Check if it's this player's turn
    current_player = current_game.players[current_game.current_player_index]
    if current_player.name != name:
        emit('error', {'message': f'Only {current_player.name} can place buildings'})
        return
    
    # Check if vertex exists
    if vertex_key not in current_game.vertices:
        emit('error', {'message': 'Invalid vertex'})
        return
    
    vertex = current_game.vertices[vertex_key]
    
    # Check if vertex already has a building
    if vertex.building is not None:
        emit('error', {'message': 'This location already has a building'})
        return
    
    # Place settlement (store as settlement type with player name)
    vertex.building = {
        'type': 'settlement',
        'player': name
    }
    
    print(f"Player {name} placed settlement at {vertex_key}")
    
    # Broadcast updated board
    emit('board_updated', {
        'board': current_game.get_board_data()
    }, broadcast=True)


@socketio.on('place_road')
def handle_place_road(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    edge_key = data.get('edge', '')
    
    if not name or not edge_key:
        return
    
    # Check if it's this player's turn
    current_player = current_game.players[current_game.current_player_index]
    if current_player.name != name:
        emit('error', {'message': f'Only {current_player.name} can place buildings'})
        return
    
    # Check if edge exists
    if edge_key not in current_game.edges:
        emit('error', {'message': 'Invalid edge'})
        return
    
    edge = current_game.edges[edge_key]
    
    # Check if edge already has a road
    if edge.road is not None:
        emit('error', {'message': 'This location already has a road'})
        return
    
    # Place road (store with player name)
    edge.road = {'player': name}
    
    print(f"Player {name} placed road at {edge_key}")
    
    # Broadcast updated board
    emit('board_updated', {
        'board': current_game.get_board_data()
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
