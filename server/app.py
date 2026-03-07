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

    color = data.get('color', '')

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
        # Use provided color, or existing saved color, or random
        if not color:
            color = existing_user.get('color')
    
    if not color:
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
    
    # Don't allow manual turn advancement during setup phase
    if current_game.game_phase == "setup":
        emit('error', {'message': 'Cannot skip turn during setup phase'})
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
    
    # Don't allow dice rolling during setup phase
    if current_game.game_phase == "setup":
        emit('error', {'message': 'Cannot roll dice during setup phase'})
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
    
    # Get current player based on phase
    if current_game.game_phase == "setup":
        current_player = current_game.players[current_game._get_setup_player_index()]
    else:
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
    
    # Check if adjacent vertices have buildings (standard Catan rule)
    for adjacent_vertex_key in vertex.neighbors.get('vertices', []):
        if adjacent_vertex_key in current_game.vertices:
            adjacent_vertex = current_game.vertices[adjacent_vertex_key]
            if adjacent_vertex.building is not None:
                emit('error', {'message': 'Cannot place settlement next to another settlement'})
                return
    
    # Playing phase: check settlement is adjacent to player's own road
    if current_game.game_phase == "playing":
        has_adjacent_road = False
        vertex_edges = vertex.neighbors.get('edges', [])
        for edge_key_check in vertex_edges:
            edge_obj = current_game.edges.get(edge_key_check)
            if edge_obj and edge_obj.road is not None:
                if edge_obj.road.get('player') == name:
                    has_adjacent_road = True
                    break
        
        if not has_adjacent_road:
            emit('error', {'message': 'Settlement must be connected to your own road'})
            return
    
    # Playing phase: check and deduct cost
    if current_game.game_phase == "playing":
        if not current_game.can_afford(name, 'settlement'):
            cost = current_game.get_cost('settlement')
            cost_str = ', '.join(f"{v} {k}" for k, v in cost.items())
            emit('error', {'message': f'Not enough resources. Need: {cost_str}'})
            return
        current_game.deduct_cost(name, 'settlement')
    
    # Place settlement (store as settlement type with player name)
    vertex.building = {
        'type': 'settlement',
        'player': name
    }
    
    # Track settlement for starter resources
    current_game.track_settlement(name, vertex_key)
    
    print(f"Player {name} placed settlement at {vertex_key}")
    
    # Setup phase logic
    if current_game.game_phase == "setup":
        current_game.last_setup_settlement = vertex_key
        
        # Check if we need to place road next (during setup, settlement always followed by road)
        if current_game.setup_action == "settlement":
            current_game.setup_action = "road"
        else:
            # Already placing road, this shouldn't happen but handle it
            current_game.setup_action = "settlement"
    else:
        # Normal playing phase
        current_game.setup_action = "settlement"
    
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
    
    # Get current player based on phase
    if current_game.game_phase == "setup":
        current_player = current_game.players[current_game._get_setup_player_index()]
    else:
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
    
    # Setup phase: check road is adjacent to last settlement
    if current_game.game_phase == "setup" and current_game.last_setup_settlement:
        settlement_vertex = current_game.vertices.get(current_game.last_setup_settlement)
        if settlement_vertex:
            # Get vertices connected to this edge
            edge_vertices = edge.neighbors.get('vertices', [])
            if current_game.last_setup_settlement not in edge_vertices:
                emit('error', {'message': 'Road must be connected to your settlement'})
                return
    
    # Playing phase: check road is adjacent to player's own road
    if current_game.game_phase == "playing":
        has_adjacent_road = False
        edge_vertices = edge.neighbors.get('vertices', [])
        for vertex_key in edge_vertices:
            vertex = current_game.vertices.get(vertex_key)
            if vertex:
                for connected_edge_key in vertex.neighbors.get('edges', []):
                    if connected_edge_key != edge_key:
                        connected_edge = current_game.edges.get(connected_edge_key)
                        if connected_edge and connected_edge.road is not None:
                            # Check if it's the same player's road
                            if connected_edge.road.get('player') == name:
                                has_adjacent_road = True
                                break
            if has_adjacent_road:
                break
        
        if not has_adjacent_road:
            emit('error', {'message': 'Road must be connected to your own road'})
            return
    
    # Playing phase: check and deduct cost
    if current_game.game_phase == "playing":
        if not current_game.can_afford(name, 'road'):
            cost = current_game.get_cost('road')
            cost_str = ', '.join(f"{v} {k}" for k, v in cost.items())
            emit('error', {'message': f'Not enough resources. Need: {cost_str}'})
            return
        current_game.deduct_cost(name, 'road')
    
    # Place road (store with player name)
    edge.road = {'player': name}
    
    print(f"Player {name} placed road at {edge_key}")
    
    # Setup phase: advance to next player after road
    if current_game.game_phase == "setup":
        current_game._advance_setup_turn()
    
    # Broadcast updated board
    emit('board_updated', {
        'board': current_game.get_board_data()
    }, broadcast=True)


@socketio.on('upgrade_city')
def handle_upgrade_city(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    vertex_key = data.get('vertex', '')
    
    if not name or not vertex_key:
        return
    
    # Get current player based on phase
    if current_game.game_phase == "setup":
        emit('error', {'message': 'Cannot upgrade to city during setup phase'})
        return
    else:
        current_player = current_game.players[current_game.current_player_index]
    
    if current_player.name != name:
        emit('error', {'message': f'Only {current_player.name} can upgrade buildings'})
        return
    
    # Check if vertex exists
    if vertex_key not in current_game.vertices:
        emit('error', {'message': 'Invalid vertex'})
        return
    
    vertex = current_game.vertices[vertex_key]
    
    # Check if there's a building
    if vertex.building is None:
        emit('error', {'message': 'No building at this location'})
        return
    
    # Check if it's a settlement (not already a city)
    if vertex.building.get('type') != 'settlement':
        emit('error', {'message': 'Can only upgrade settlements to cities'})
        return
    
    # Check if it's the player's own settlement
    if vertex.building.get('player') != name:
        emit('error', {'message': 'Can only upgrade your own settlements'})
        return
    
    # Check and deduct city cost
    if not current_game.can_afford(name, 'city'):
        cost = current_game.get_cost('city')
        cost_str = ', '.join(f"{v} {k}" for k, v in cost.items())
        emit('error', {'message': f'Not enough resources. Need: {cost_str}'})
        return
    current_game.deduct_cost(name, 'city')
    
    # Upgrade to city
    vertex.building = {
        'type': 'city',
        'player': name
    }
    
    print(f"Player {name} upgraded settlement to city at {vertex_key}")
    
    # Broadcast updated board
    emit('board_updated', {
        'board': current_game.get_board_data()
    }, broadcast=True)


@socketio.on('propose_trade')
def handle_propose_trade(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    offered = data.get('offered', {})
    wanted = data.get('wanted', {})
    
    print(f"Received trade proposal from {name}: offered={offered}, wanted={wanted}")
    
    if not name or len(offered) == 0 or len(wanted) == 0:
        print("Trade rejected: empty name or resources")
        return
    
    # Check if it's this player's turn
    current_player = current_game.players[current_game.current_player_index]
    if current_player.name != name:
        emit('error', {'message': f'Only {current_player.name} can propose trades on their turn'})
        return
    
    # Check player has the offered resources
    player = current_game.get_player(name)
    if not player:
        print("Trade rejected: player not found")
        return
    
    print(f"Player {name} resources: {player.resources}")
    
    for resource, count in offered.items():
        available = player.resources.get(resource, 0)
        if available < count:
            emit('error', {'message': f'Not enough {resource}: have {available}, offering {count}'})
            return
    
    # Check if this is a bank trade (4:1 or better ratio)
    offered_total = sum(offered.values())
    wanted_total = sum(wanted.values())
    ratio = offered_total / wanted_total if wanted_total > 0 else 0
    
    if ratio >= current_game.trade_manager.bank_trade_ratio:
        # Execute bank trade immediately
        print(f"Auto-completing bank trade! Ratio: {ratio}:1")
        
        # Transfer resources from player to bank
        for resource, count in offered.items():
            player.resources[resource] = player.resources.get(resource, 0) - count
            for _ in range(count):
                current_game.bank.return_resources(resource)
        
        # Transfer resources from bank to player
        for resource, count in wanted.items():
            if current_game.bank.take(resource):
                player.resources[resource] = player.resources.get(resource, 0) + count
            else:
                # Bank doesn't have enough - reverse and error
                for r, c in offered.items():
                    player.resources[r] = player.resources.get(r, 0) + c
                    for _ in range(c):
                        current_game.bank.take(r)
                emit('error', {'message': 'Bank does not have enough resources'})
                return
        
        print(f"Bank trade completed for {name}")
        emit('bank_trade_completed', {
            'offered': offered,
            'wanted': wanted
        }, broadcast=True)
        emit('board_updated', {
            'board': current_game.get_board_data()
        }, broadcast=True)
    else:
        # Not a bank trade - create regular offer
        offer = current_game.propose_trade(name, offered, wanted)
        if offer:
            print(f"Trade proposed successfully! Offer ID: {offer['id']}")
            emit('trade_proposed', {'offer': offer}, broadcast=True)
            # Also emit board_updated to refresh everyone's trade lists
            emit('board_updated', {
                'board': current_game.get_board_data()
            }, broadcast=True)
        else:
            emit('error', {'message': 'Maximum number of trade offers reached'})


@socketio.on('accept_trade')
def handle_accept_trade(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    offer_id = data.get('offer_id', 0)
    
    if not name or not offer_id:
        return
    
    # Get offer first
    offer = current_game.trade_manager.offers.get(offer_id)
    if not offer:
        emit('error', {'message': 'Trade offer not found'})
        return
    
    # Check player has the wanted resources (what the proposer wants)
    player = current_game.get_player(name)
    if not player:
        return
    
    for resource, count in offer['wanted_resources'].items():
        if player.resources.get(resource, 0) < count:
            emit('error', {'message': f'Not enough {resource} to accept this trade'})
            return
    
    if current_game.accept_trade(offer_id, name):
        print(f"Player {name} accepted trade #{offer_id}")
        emit('trade_accepted', {'offer_id': offer_id, 'player': name}, broadcast=True)
        emit('board_updated', {
            'board': current_game.get_board_data()
        }, broadcast=True)
    else:
        emit('error', {'message': 'Could not accept trade'})


@socketio.on('decline_trade')
def handle_decline_trade(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    offer_id = data.get('offer_id', 0)
    
    if not name or not offer_id:
        return
    
    if current_game.decline_trade(offer_id, name):
        print(f"Player {name} declined trade #{offer_id}")
        emit('trade_declined', {'offer_id': offer_id, 'player': name}, broadcast=True)


@socketio.on('cancel_trade')
def handle_cancel_trade(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    offer_id = data.get('offer_id', 0)
    
    if not name or not offer_id:
        return
    
    if current_game.cancel_trade(offer_id, name):
        print(f"Player {name} cancelled trade #{offer_id}")
        emit('trade_cancelled', {'offer_id': offer_id}, broadcast=True)
        emit('board_updated', {
            'board': current_game.get_board_data()
        }, broadcast=True)


@socketio.on('refresh_board')
def handle_refresh_board():
    """Refresh board data (used for timer updates)."""
    if current_game is None or current_game.game_state != "started":
        return
    emit('board_updated', {
        'board': current_game.get_board_data()
    }, broadcast=True)


@socketio.on('complete_trade')
def handle_complete_trade(data):
    if current_game is None or current_game.game_state != "started":
        return
    
    name = data.get('name', '')
    offer_id = data.get('offer_id', 0)
    selected_responder = data.get('selected_responder', None)
    
    if not name or not offer_id:
        return
    
    result = current_game.complete_trade(offer_id, name, selected_responder)
    if not result:
        emit('error', {'message': 'Could not complete trade'})
        return
    
    # Execute the trade
    if result['type'] == 'bank':
        current_game.execute_bank_trade(offer_id, name)
        print(f"Player {name} completed bank trade #{offer_id}")
        emit('trade_completed', {'offer_id': offer_id, 'type': 'bank'}, broadcast=True)
    else:
        current_game.execute_trade_with_player(offer_id, name, result['responder'])
        print(f"Player {name} completed trade #{offer_id} with {result['responder']}")
        emit('trade_completed', {'offer_id': offer_id, 'type': 'player', 'with': result['responder']}, broadcast=True)
    
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
