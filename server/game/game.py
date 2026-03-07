import random
import os
import json

from game.hex_models import Hex, Vertex, Edge
from game.player import Player
from game.bank import Bank
from game.trade import TradeManager


class Game:
    """
    Represents a Catan game session.
    
    Manages players, turn order, game state, and the board layout.
    The board is generated using a cube coordinate system (see hex.md).
    
    Attributes:
        players (list): List of Player objects in turn order.
        observers (list): List of observer names.
        current_player_index (int): Index of current player in players list.
        game_state (str): "waiting" or "started".
        hex_radius (int): Radius for land hexes (2 = standard 19-hex Catan).
        edge_radius (int): Radius for ocean tiles (3 = one ring around land).
        hexes (dict): Map of hex key -> Hex object.
        vertices (dict): Map of vertex key -> Vertex object.
        edges (dict): Map of edge key -> Edge object.
    """
    
    # Predefined colors for up to 4 players
    PLAYER_COLORS = ['#e74c3c', '#3498db', '#f39c12', '#9b59b6']
    
    # Direction vectors for generating neighbors (from hex.md)
    # Used to find adjacent hexes from any given hex
    HEX_DIRECTIONS = [
        (3, -3, 0),   # Right
        (3, 0, -3),   # Upper right
        (0, 3, -3),   # Upper left
        (-3, 3, 0),   # Left
        (-3, 0, 3),   # Lower left
        (0, -3, 3),   # Lower right
    ]
    
    # Vertex direction vectors from hex center (from hex.md)
    # Used to find the 6 vertices surrounding each hex
    VERTEX_DIRECTIONS = [
        (1, -2, 1),   # Top-right
        (2, -1, -1),  # Right
        (1, 1, -2),   # Bottom-right
        (-1, 2, -1),  # Bottom-left
        (-2, 1, 1),   # Left
        (-1, -1, 2),  # Top-left
    ]
    
    # Edge direction vectors from hex center (from hex.md)
    # Used to find the 6 edges surrounding each hex
    EDGE_DIRECTIONS = [
        (1, -1, 0),   # Right
        (1, 0, -1),   # Upper right
        (0, 1, -1),   # Upper left
        (-1, 1, 0),   # Left
        (-1, 0, 1),   # Lower left
        (0, -1, 1),   # Lower right
    ]
    
    def __init__(self, player_names: list, observers: list, player_colors: dict = None):
        # Create Player objects with colors
        if player_colors is None:
            player_colors = {}
        
        # Initialize bank
        self.bank = Bank()
        
        self.players = []
        for i, name in enumerate(player_names):
            color = player_colors.get(name) or (self.PLAYER_COLORS[i] if i < len(self.PLAYER_COLORS) else '#ffffff')
            player = Player(name, color)
            # No starting resources - players get resources from dice rolls
            self.players.append(player)
        
        self.observers = observers
        self.current_player_index = 0
        self.game_state = "waiting"
        
        # Setup phase variables
        self.game_phase = "setup"  # "setup" or "playing"
        self.setup_turn = 0  # 0-7 for 8 setup turns
        self.setup_action = "settlement"  # "settlement" or "road"
        self.last_setup_settlement = None  # vertex key of last placed settlement
        
        # Board configuration
        # hex_radius=2 gives us 19 land hexes (standard Catan)
        # edge_radius=3 adds one ring of ocean tiles around the land
        self.hex_radius = 2
        self.edge_radius = 3
        
        # Load building costs from JSON file
        costs_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'costs.json')
        with open(costs_file, 'r') as f:
            self.building_costs = json.load(f)
        
        # Board data structures
        self.hexes = {}    # key -> Hex object
        self.vertices = {} # key -> Vertex object
        self.edges = {}    # key -> Edge object
        
        # Generate the complete board
        self._generate_board()
        
        # Trade manager
        self.trade_manager = TradeManager()
    
    def add_observer(self, name: str):
        """Add an observer to the game."""
        if name not in self.observers:
            self.observers.append(name)
    
    def remove_observer(self, name: str):
        """Remove an observer from the game."""
        if name in self.observers:
            self.observers.remove(name)
    
    def is_player(self, name: str) -> bool:
        """Check if a name is a player in this game."""
        return any(p.name == name for p in self.players)
    
    def get_player(self, name: str) -> Player | None:
        """Get Player object by name."""
        for p in self.players:
            if p.name == name:
                return p
        return None
    
    def set_player_color(self, name: str, color: str) -> bool:
        """Set or update a player's color. Returns True if successful."""
        player = self.get_player(name)
        if player:
            player.set_color(color)
            return True
        return False
    
    def get_player_names(self) -> list:
        """Get list of player names (for compatibility)."""
        return [p.name for p in self.players]
    
    def _get_setup_player_index(self) -> int:
        """Get player index based on setup turn order.
        
        Setup order: 0,1,2,3,3,2,1,0 (A->B->C->D->D->C->B->A)
        """
        num_players = len(self.players)
        if self.setup_turn < num_players:
            # First round: forward (0,1,2,3)
            return self.setup_turn
        else:
            # Second round: reverse (3,2,1,0)
            return (2 * num_players - 1) - self.setup_turn
    
    def _advance_setup_turn(self):
        """Advance to next setup turn. Returns True if setup complete."""
        self.setup_turn += 1
        self.setup_action = "settlement"
        self.last_setup_settlement = None
        
        num_players = len(self.players)
        if self.setup_turn >= num_players * 2:
            # Setup complete - switch to playing phase
            self.game_phase = "playing"
            self.current_player_index = 0
            print(f"=== Setup complete! Starting normal play. ===")
            return True
        return False
    
    def propose_trade(self, proposer: str, offered_resources: dict, wanted_resources: dict):
        """Propose a new trade offer."""
        return self.trade_manager.propose(proposer, offered_resources, wanted_resources)
    
    def accept_trade(self, offer_id: int, player_name: str) -> bool:
        """Accept a trade offer. Returns True if successful."""
        player = self.get_player(player_name)
        if not player:
            return False
        return self.trade_manager.accept(offer_id, player_name, player.resources)
    
    def decline_trade(self, offer_id: int, player_name: str) -> bool:
        """Decline a trade offer."""
        return self.trade_manager.decline(offer_id, player_name)
    
    def cancel_trade(self, offer_id: int, player_name: str) -> bool:
        """Cancel a trade offer (proposer only)."""
        return self.trade_manager.cancel(offer_id, player_name)
    
    def complete_trade(self, offer_id: int, proposer: str, selected_responder: str = None) -> dict | None:
        """Complete a trade. If 4:1 or better, auto-trade with bank."""
        return self.trade_manager.complete(offer_id, proposer, selected_responder)
    
    def execute_trade_with_player(self, offer_id: int, proposer: str, responder: str):
        """Execute a player-to-player trade."""
        offer = self.trade_manager.offers.get(offer_id)
        if not offer or offer['status'] != 'completed':
            return False
        
        proposer_player = self.get_player(proposer)
        responder_player = self.get_player(responder)
        
        if not proposer_player or not responder_player:
            return False
        
        # Transfer offered resources FROM proposer TO responder
        for resource, count in offer['offered_resources'].items():
            proposer_player.resources[resource] = proposer_player.resources.get(resource, 0) - count
            responder_player.resources[resource] = responder_player.resources.get(resource, 0) + count
        
        # Transfer wanted resources FROM responder TO proposer
        for resource, count in offer['wanted_resources'].items():
            responder_player.resources[resource] = responder_player.resources.get(resource, 0) - count
            proposer_player.resources[resource] = proposer_player.resources.get(resource, 0) + count
        
        return True
    
    def execute_bank_trade(self, offer_id: int, proposer: str):
        """Execute a bank trade (4:1 or better ratio)."""
        offer = self.trade_manager.offers.get(offer_id)
        if not offer or offer['status'] != 'completed':
            return False
        
        proposer_player = self.get_player(proposer)
        if not proposer_player:
            return False
        
        # Transfer offered resources to bank
        for resource, count in offer['offered_resources'].items():
            for _ in range(count):
                self.bank.return_resources(resource)
        
        # Transfer wanted resources from bank to player
        for resource, count in offer['wanted_resources'].items():
            for _ in range(count):
                self.bank.take(resource)
            proposer_player.resources[resource] = proposer_player.resources.get(resource, 0) + count
        
        return True
    
    def _hex_key(self, x: int, y: int, z: int) -> str:
        """
        Create a hex key string from cube coordinates.
        
        Args:
            x, y, z: Cube coordinates (must satisfy x + y + z = 0)
            
        Returns:
            String in format "x,y,z"
        """
        return f"{x},{y},{z}"
    
    def _parse_key(self, key: str) -> tuple:
        """
        Parse a coordinate key string into (x, y, z) tuple.
        
        Args:
            key: String in format "x,y,z"
            
        Returns:
            Tuple of (x, y, z) integers
        """
        parts = key.split(',')
        return int(parts[0]), int(parts[1]), int(parts[2])
    
    def _is_valid_hex(self, x: int, y: int, z: int) -> bool:
        """
        Check if coordinates represent a valid hex within the board.
        
        A hex is valid if:
        1. x + y + z = 0 (cube coordinate invariant)
        2. All coordinates are divisible by 3 (hex classification rule)
        3. The hex is within the land radius
        
        Args:
            x, y, z: Cube coordinates
            
        Returns:
            True if valid land hex, False otherwise
        """
        # Check cube coordinate invariant
        if x + y + z != 0:
            return False
        
        # Check hex classification (all divisible by 3)
        if x % 3 != 0 or y % 3 != 0 or z % 3 != 0:
            return False
        
        # Check if within land radius (using max coordinate as distance metric)
        max_coord = max(abs(x // 3), abs(y // 3), abs(z // 3))
        return max_coord <= self.hex_radius
    
    def _is_ocean(self, x: int, y: int, z: int) -> bool:
        """
        Check if coordinates represent an ocean (edge) tile.
        
        Ocean tiles are within edge_radius but outside hex_radius.
        
        Args:
            x, y, z: Cube coordinates
            
        Returns:
            True if ocean tile, False otherwise
        """
        if x + y + z != 0:
            return False
        
        # Must have exactly one coordinate divisible by 3 (edge classification)
        coords_divisible = sum(1 for c in (x, y, z) if c % 3 == 0)
        if coords_divisible != 1:
            return False
        
        # Check if within edge radius but outside land
        max_coord = max(abs(x), abs(y), abs(z))
        return max_coord <= self.edge_radius * 3 and not self._is_valid_hex(x, y, z)
    
    def _generate_board(self):
        """
        Generate the complete Catan board.
        
        This method:
        1. Creates all hexes within hex_radius (land) and edge_radius (ocean)
        2. Generates all vertices and edges for each hex
        3. Builds neighbor relationships algebraically
        4. Assigns resource types and numbers randomly
        """
        # Step 1: Generate all hex keys
        all_hex_keys = set()
        
        # Generate all possible coordinates within edge_radius
        # We iterate through a cube and filter based on our rules
        r = self.edge_radius * 3
        for x in range(-r, r + 1, 3):
            for y in range(-r, r + 1, 3):
                z = -x - y
                if -r <= z <= r:
                    if self._is_valid_hex(x, y, z):
                        all_hex_keys.add(self._hex_key(x, y, z))
                    elif self._is_ocean(x, y, z):
                        all_hex_keys.add(self._hex_key(x, y, z))
        
        # Step 2: Create hex objects with resource types and numbers
        self._create_hexes(all_hex_keys)
        
        # Step 3: Generate vertices and edges from hexes
        self._generate_vertices_and_edges(all_hex_keys)
        
        # Step 4: Build all neighbor relationships
        self._build_neighbor_relationships()
        
        print(f"\n=== Board Generated ===")
        print(f"Total hexes: {len(self.hexes)}")
        print(f"Total vertices: {len(self.vertices)}")
        print(f"Total edges: {len(self.edges)}")
        
        # Count hex types for debugging
        hex_types = {}
        for hex_obj in self.hexes.values():
            hex_types[hex_obj.type] = hex_types.get(hex_obj.type, 0) + 1
        print(f"Hex distribution: {hex_types}")
        print("=======================\n")
    
    def _create_hexes(self, hex_keys: set):
        """
        Create Hex objects with random resource types and numbers.
        
        Standard Catan distribution (19 hexes):
        - 4 Wheat, 4 Sheep, 4 Ore, 4 Brick, 3 Wood, 1 Desert
        
        Args:
            hex_keys: Set of all hex coordinate keys
        """
        # Define resource types and their counts (standard Catan)
        resource_types = (
            ["wheat"] * 4 +
            ["sheep"] * 4 +
            ["ore"] * 4 +
            ["brick"] * 4 +
            ["wood"] * 3 +
            ["desert"] * 1
        )
        
        # Shuffle for random placement
        random.shuffle(resource_types)
        
        # Number tokens (2-12, excluding 7)
        # Each number appears with frequency based on real dice probability:
        # 2,12: 1 each, 3,11: 2 each, 4,10: 3 each, 5,9: 4 each, 6,8: 5 each
        number_tokens = (
            [2, 12] * 1 +
            [3, 11] * 2 +
            [4, 10] * 3 +
            [5, 9] * 4 +
            [6, 8] * 5
        )
        random.shuffle(number_tokens)
        number_tokens_stack = list(number_tokens)  # Copy for popping
        
        # Create hex objects
        for key in hex_keys:
            x, y, z = self._parse_key(key)
            
            # Determine if ocean or land
            if self._is_ocean(x, y, z):
                hex_type = "ocean"
                number = None
            else:
                # Assign resource type
                hex_type = resource_types.pop() if resource_types else "wheat"
                
                # Desert gets no number
                if hex_type == "desert":
                    number = None
                else:
                    number = number_tokens_stack.pop() if number_tokens_stack else None
            
            hex_obj = Hex(key, hex_type, number)
            self.hexes[key] = hex_obj
    
    def _generate_vertices_and_edges(self, hex_keys: set):
        """
        Generate all vertices and edges from hex coordinates.
        
        For each hex, we calculate its 6 vertices and 6 edges using
        the direction vectors from hex.md.
        
        Args:
            hex_keys: Set of all hex coordinate keys
        """
        vertex_keys = set()
        edge_keys = set()
        
        for hex_key in hex_keys:
            hx, hy, hz = self._parse_key(hex_key)
            
            # Generate 6 vertices for this hex
            for vx, vy, vz in self.VERTEX_DIRECTIONS:
                vertex_key = self._hex_key(hx + vx, hy + vy, hz + vz)
                vertex_keys.add(vertex_key)
            
            # Generate 6 edges for this hex
            for ex, ey, ez in self.EDGE_DIRECTIONS:
                edge_key = self._hex_key(hx + ex, hy + ey, hz + ez)
                edge_keys.add(edge_key)
        
        # Create Vertex objects
        for key in vertex_keys:
            self.vertices[key] = Vertex(key)
        
        # Create Edge objects
        for key in edge_keys:
            self.edges[key] = Edge(key)
    
    def _build_neighbor_relationships(self):
        """
        Build all neighbor relationships between hexes, vertices, and edges.
        
        Uses algebraic rules from hex.md to derive neighbors without lookup tables.
        """
        # Build hex -> hex neighbors
        for hex_key, hex_obj in self.hexes.items():
            hx, hy, hz = self._parse_key(hex_key)
            
            for dx, dy, dz in self.HEX_DIRECTIONS:
                neighbor_key = self._hex_key(hx + dx, hy + dy, hz + dz)
                if neighbor_key in self.hexes:
                    hex_obj.neighbors.append(neighbor_key)
        
        # Build hex -> vertices and hex -> edges neighbors
        for hex_key, hex_obj in self.hexes.items():
            hx, hy, hz = self._parse_key(hex_key)
            
            # Vertices
            for vx, vy, vz in self.VERTEX_DIRECTIONS:
                vertex_key = self._hex_key(hx + vx, hy + vy, hz + vz)
                if vertex_key in self.vertices:
                    self.vertices[vertex_key].neighbors["hexes"].append(hex_key)
            
            # Edges
            for ex, ey, ez in self.EDGE_DIRECTIONS:
                edge_key = self._hex_key(hx + ex, hy + ey, hz + ez)
                if edge_key in self.edges:
                    self.edges[edge_key].neighbors["hexes"].append(hex_key)
        
        # Build edge -> vertices neighbors using brute force
        # For each edge, find the 2 vertices by checking which vertices are at either end
        # An edge at (ex,ey,ez) has vertices at (ex±1, ey∓1, ez) etc.
        for edge_key, edge_obj in self.edges.items():
            ex, ey, ez = self._parse_key(edge_key)
            
            # The 6 edge directions tell us how to move from edge to vertex
            # Try each direction: edge +/- direction gives a vertex coordinate
            candidates = []
            for dx, dy, dz in self.EDGE_DIRECTIONS:
                # Positive direction
                v1 = (ex + dx, ey + dy, ez + dz)
                v2 = (ex - dx, ey - dy, ez - dz)
                candidates.extend([v1, v2])
            
            for cx, cy, cz in candidates:
                if cx + cy + cz != 0:
                    continue
                # Check if this is a valid vertex (none divisible by 3)
                if cx % 3 == 0 or cy % 3 == 0 or cz % 3 == 0:
                    continue
                vertex_key = self._hex_key(cx, cy, cz)
                if vertex_key in self.vertices:
                    if vertex_key not in edge_obj.neighbors["vertices"]:
                        edge_obj.neighbors["vertices"].append(vertex_key)
        
        # Build vertex -> edges neighbors (vertices connect to 3 edges each)
        for vertex_key, vertex_obj in self.vertices.items():
            vx, vy, vz = self._parse_key(vertex_key)
            
            # A vertex connects to edges that have the vertex at one end
            # Try each edge direction from the vertex
            candidates = []
            for dx, dy, dz in self.EDGE_DIRECTIONS:
                # Edge = vertex +/- direction
                e1 = (vx + dx, vy + dy, vz + dz)
                e2 = (vx - dx, vy - dy, vz - dz)
                candidates.extend([e1, e2])
            
            for cx, cy, cz in candidates:
                if cx + cy + cz != 0:
                    continue
                # Check if this is a valid edge (exactly one divisible by 3)
                div_count = sum(1 for c in (cx, cy, cz) if c % 3 == 0)
                if div_count != 1:
                    continue
                edge_key = self._hex_key(cx, cy, cz)
                if edge_key in self.edges:
                    if edge_key not in vertex_obj.neighbors["edges"]:
                        vertex_obj.neighbors["edges"].append(edge_key)
        
        # Build edge -> edges neighbors (edges sharing a vertex)
        for edge_key, edge_obj in self.edges.items():
            for vertex_key in edge_obj.neighbors["vertices"]:
                vertex_obj = self.vertices[vertex_key]
                for neighbor_edge_key in vertex_obj.neighbors["edges"]:
                    if neighbor_edge_key != edge_key and neighbor_edge_key not in edge_obj.neighbors["edges"]:
                        edge_obj.neighbors["edges"].append(neighbor_edge_key)
        
        # Build vertex -> vertices neighbors (vertices connected by an edge)
        for vertex_key, vertex_obj in self.vertices.items():
            for edge_key in vertex_obj.neighbors["edges"]:
                edge_obj = self.edges[edge_key]
                for connected_vertex_key in edge_obj.neighbors["vertices"]:
                    if connected_vertex_key != vertex_key and connected_vertex_key not in vertex_obj.neighbors["vertices"]:
                        vertex_obj.neighbors["vertices"].append(connected_vertex_key)
    
    def get_board_data(self) -> dict:
        """
        Serialize board data for sending to client.
        
        Returns:
            dict: Board data including hexes, vertices, and edges
        """
        hexes = {}
        for key, hex_obj in self.hexes.items():
            hexes[key] = {
                'type': hex_obj.type,
                'number': hex_obj.number,
                'neighbors': hex_obj.neighbors
            }
        
        vertices = {}
        for key, vertex_obj in self.vertices.items():
            vertices[key] = {
                'building': vertex_obj.building,
                'neighbors': vertex_obj.neighbors
            }
        
        edges = {}
        for key, edge_obj in self.edges.items():
            edges[key] = {
                'road': edge_obj.road,
                'neighbors': edge_obj.neighbors
            }
        
        # Clean up expired trades
        self.trade_manager.cleanup_expired()
        
        # Build my_offers for each player
        my_offers = {}
        for player in self.players:
            my_offers[player.name] = self.trade_manager.get_my_offers(player.name)
        
        return {
            'hexes': hexes,
            'vertices': vertices,
            'edges': edges,
            'players': [p.to_dict() for p in self.players],
            'bank': self.bank.get_all(),
            'trades': {
                'active': self.trade_manager.get_all_active(),
                'my_offers': my_offers
            },
            'game_phase': self.game_phase,
            'setup_action': self.setup_action,
            'current_player': self.players[self._get_setup_player_index()].name if self.game_phase == "setup" else self.players[self.current_player_index].name
        }
    
    def distribute_resources(self, dice_total: int):
        """Distribute resources to players based on dice roll.
        
        Each settlement adjacent to a hex with matching number receives 1 resource.
        Skips distribution for 7 (robber not implemented).
        
        Args:
            dice_total: The sum of the two dice rolled
        """
        if dice_total == 7:
            return
        
        gained_resources = {}
        
        for vertex_key, vertex in self.vertices.items():
            if not vertex.building or vertex.building.get('type') not in ('settlement', 'city'):
                continue
            
            building_type = vertex.building.get('type')
            resource_amount = 2 if building_type == 'city' else 1
            
            player_name = vertex.building.get('player')
            if not player_name:
                continue
            
            player = self.get_player(player_name)
            if not player:
                continue
            
            for hex_key in vertex.neighbors.get('hexes', []):
                if hex_key not in self.hexes:
                    continue
                
                hex_obj = self.hexes[hex_key]
                if hex_obj.number == dice_total and hex_obj.type not in ('desert', 'ocean'):
                    # Try to take resource(s) from bank
                    for _ in range(resource_amount):
                        if self.bank.take(hex_obj.type):
                            player.resources[hex_obj.type] = player.resources.get(hex_obj.type, 0) + 1
                            
                            if player_name not in gained_resources:
                                gained_resources[player_name] = {}
                            gained_resources[player_name][hex_obj.type] = gained_resources[player_name].get(hex_obj.type, 0) + 1
        
        if gained_resources:
            print(f"Resources distributed (rolled {dice_total}):")
            for player_name, resources in gained_resources.items():
                resource_str = ', '.join(f"+{count} {resource}" for resource, count in resources.items())
                print(f"  {player_name}: {resource_str}")
            print(f"  Bank: {self.bank}")
    
    def get_cost(self, building_type: str) -> dict:
        """Get the cost for a building type."""
        return self.building_costs.get(building_type, {})
    
    def can_afford(self, player_name: str, building_type: str) -> bool:
        """Check if player can afford the building cost."""
        player = self.get_player(player_name)
        if not player:
            return False
        
        cost = self.get_cost(building_type)
        for resource, amount in cost.items():
            if player.resources.get(resource, 0) < amount:
                return False
        return True
    
    def deduct_cost(self, player_name: str, building_type: str) -> bool:
        """Deduct building cost from player's resources and return to bank. Returns True if successful."""
        player = self.get_player(player_name)
        if not player:
            return False
        
        if not self.can_afford(player_name, building_type):
            return False
        
        cost = self.get_cost(building_type)
        for resource, amount in cost.items():
            player.resources[resource] -= amount
            self.bank.return_resources(resource, amount)
        return True
    
    def start(self):
        """Start the game and shuffle player order."""
        random.shuffle(self.players)
        self.game_state = "started"
        print(f"\n=== Game started! ===")
        print(f"Player order: {self.players}")
        print(f"Current player: {self.players[self.current_player_index]}")
        print("=====================\n")
