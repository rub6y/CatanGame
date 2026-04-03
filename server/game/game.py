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
        self.player_settlements = {}  # player_name -> list of settlement vertex keys (for tracking first/second)
        
        # Board configuration
        # hex_radius=2 gives us 19 land hexes (standard Catan)
        # edge_radius=3 adds one ring of ocean tiles around the land
        self.hex_radius = 2
        self.edge_radius = 3
        
        # Robber
        self.robber_hex = None  # Hex key where robber is located
        self.must_move_robber = False  # Set to true when 7 is rolled
        self.must_choose_victim = False  # Set to true when need to pick victim
        self.robber_victims = []  # List of players with settlements near robber hex
        
        # Discard half mechanic
        self.players_needing_discard = {}  # player_name -> amount to discard
        
        # Timer settings (in seconds)
        self.dice_roll_time_limit = 15
        self.round_time_limit = 120
        self.turn_start_time = None  # timestamp when turn started
        self.dice_rolled_time = None  # timestamp when dice was rolled
        self.has_rolled_dice = False  # whether player has rolled in current turn
        
        # Game turn counter
        self.turn_count = 0  # Increments after each player's turn ends
        
        # Free roads from Two Roads development card
        self.free_roads_remaining = 0  # Number of free roads player can place
        
        # Longest Road and Largest Army
        self.longest_road_holder = None  # Player name with longest road
        self.largest_army_holder = None  # Player name with largest army
        self.longest_road_length = {}  # player_name -> longest road length
        self.knights_played = {}  # player_name -> knight cards played
        
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
    
    def track_settlement(self, player_name: str, vertex_key: str):
        """Track a settlement placement for starter resources."""
        if player_name not in self.player_settlements:
            self.player_settlements[player_name] = []
        self.player_settlements[player_name].append(vertex_key)
    
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
            # Setup complete - distribute starter resources from second settlements
            print("=== Distributing starter resources from second settlements ===")
            for player in self.players:
                settlements = self.player_settlements.get(player.name, [])
                if len(settlements) >= 2:
                    # Second settlement is at index 1
                    second_settlement = settlements[1]
                    self.distribute_from_settlement(second_settlement, player.name)
            
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
        
        # Step 5: Assign ports to edge vertices
        self._assign_ports()
        
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
            
            # Place robber on desert tile
            if hex_type == "desert" and self.robber_hex is None:
                self.robber_hex = key
    
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
    
    def _assign_ports(self):
        """Assign ports to 9 vertices on the edge of the map (evenly distributed)."""
        import random
        
        # Find all edge vertices - vertices that don't have 3 adjacent hexes
        edge_vertices = []
        for vertex_key, vertex_obj in self.vertices.items():
            hex_neighbors = vertex_obj.neighbors.get("hexes", [])
            if len(hex_neighbors) < 3:
                edge_vertices.append(vertex_key)
        
        edge_vertices = list(set(edge_vertices))
        
        if len(edge_vertices) < 9:
            print(f"Warning: Only {len(edge_vertices)} edge vertices found")
            port_vertices = edge_vertices[:9] if edge_vertices else []
        else:
            # Sort edge vertices by angle to distribute evenly around the board
            def get_vertex_angle(vertex_key):
                """Get approximate angle for sorting vertices."""
                coords = self._parse_key(vertex_key)
                x, y, z = coords
                # Use atan2 to get angle from center
                # Project 3D coord to 2D
                px = x + 0.5 * z
                py = 0.866 * z  # sqrt(3)/2
                import math
                return math.atan2(py, px)
            
            # Sort by angle
            edge_vertices.sort(key=get_vertex_angle)
            
            # Select 9 evenly spaced vertices
            step = len(edge_vertices) / 9
            port_vertices = [edge_vertices[int(i * step)] for i in range(9)]
        
        random.shuffle(port_vertices)
        
        # Port types: 4 generic (3:1), 5 resource-specific (2:1)
        port_types = ["generic"] * 4 + ["wood", "brick", "sheep", "wheat", "ore"]
        random.shuffle(port_types)
        
        # Assign ports to vertices
        for i, vertex_key in enumerate(port_vertices):
            if vertex_key in self.vertices:
                vertex_obj = self.vertices[vertex_key]
                resource_type = port_types[i]
                
                if resource_type == "generic":
                    vertex_obj.port = {"type": "generic"}
                else:
                    vertex_obj.port = {"type": "resource", "resource": resource_type}
        
        # Count ports for debug
        generic_count = sum(1 for v in self.vertices.values() if v.port and v.port.get("type") == "generic")
        resource_count = sum(1 for v in self.vertices.values() if v.port and v.port.get("type") == "resource")
        print(f"Ports assigned: {generic_count} generic (3:1), {resource_count} resource (2:1)")
    
    def get_player_ports(self, player_name: str) -> dict:
        """Get all ports accessible to a player based on their settlements/cities."""
        player = self.get_player(player_name)
        if not player:
            return {}
        
        ports = {}
        for vertex_key in player.settlements + player.cities:
            vertex = self.vertices.get(vertex_key)
            if vertex and vertex.port:
                port_type = vertex.port.get("type")
                if port_type == "generic":
                    ports["generic"] = True
                elif port_type == "resource":
                    resource = vertex.port.get("resource")
                    ports[resource] = True
        
        return ports
    
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
            vertex_data = {
                'building': vertex_obj.building,
                'neighbors': vertex_obj.neighbors
            }
            if vertex_obj.port:
                vertex_data['port'] = vertex_obj.port
            vertices[key] = vertex_data
        
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
            'players': [p.to_dict(self.longest_road_holder, self.largest_army_holder) for p in self.players],
            'bank': self.bank.get_all(),
            'dev_card_deck': self.bank.get_dev_card_counts(),
            'trades': {
                'active': self.trade_manager.get_all_active(),
                'my_offers': my_offers
            },
            'game_phase': self.game_phase,
            'setup_action': self.setup_action,
            'current_player': self.players[self._get_setup_player_index()].name if self.game_phase == "setup" else self.players[self.current_player_index].name,
            'robber_hex': self.robber_hex,
            'must_move_robber': self.must_move_robber,
            'must_choose_victim': self.must_choose_victim,
            'robber_victims': self.robber_victims,
            'players_needing_discard': self.players_needing_discard,
            'dice_roll_time': self.get_dice_roll_time_remaining(),
            'round_time': self.get_round_time_remaining(),
            'has_rolled_dice': self.has_rolled_dice,
            'turn_count': self.turn_count,
            'free_roads_remaining': self.free_roads_remaining,
            'longest_road_holder': self.longest_road_holder,
            'largest_army_holder': self.largest_army_holder,
            'longest_road_length': self.longest_road_length,
            'knights_played': {p.name: p.knights_played for p in self.players}
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
                # Skip robber hex and non-matching numbers
                if hex_key == self.robber_hex:
                    continue
                if hex_obj.number != dice_total or hex_obj.type in ('desert', 'ocean'):
                    continue
                
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
    
    def distribute_from_settlement(self, vertex_key: str, player_name: str):
        """Give resources from a specific settlement's adjacent hexes (for starter resources)."""
        vertex = self.vertices.get(vertex_key)
        if not vertex:
            return
        
        player = self.get_player(player_name)
        if not player:
            return
        
        gained = {}
        
        for hex_key in vertex.neighbors.get('hexes', []):
            hex_obj = self.hexes.get(hex_key)
            if hex_obj and hex_obj.type not in ('desert', 'ocean'):
                if self.bank.take(hex_obj.type):
                    player.resources[hex_obj.type] = player.resources.get(hex_obj.type, 0) + 1
                    gained[hex_obj.type] = gained.get(hex_obj.type, 0) + 1
        
        if gained:
            print(f"Starter resources for {player_name} from {vertex_key}: {gained}")
    
    def check_discard_required(self):
        """Check which players need to discard half their resources (7 rolled)."""
        self.players_needing_discard = {}
        
        for player in self.players:
            total_cards = sum(player.resources.values())
            if total_cards > 7:
                discard_amount = total_cards // 2
                self.players_needing_discard[player.name] = discard_amount
        
        if self.players_needing_discard:
            print(f"Players needing to discard: {self.players_needing_discard}")
    
    def discard_resources(self, player_name: str, resources: dict) -> bool:
        """Process resource discard from a player.
        
        Args:
            player_name: Name of player discarding
            resources: Dict of resource_type -> count to discard
            
        Returns:
            bool: True if discard was successful
        """
        if player_name not in self.players_needing_discard:
            return False
        
        player = self.get_player(player_name)
        if not player:
            return False
        
        required = self.players_needing_discard[player_name]
        discard_total = sum(resources.values())
        
        if discard_total != required:
            return False
        
        for resource_type, count in resources.items():
            current = player.resources.get(resource_type, 0)
            if current < count:
                return False
        
        for resource_type, count in resources.items():
            player.resources[resource_type] = player.resources.get(resource_type, 0) - count
            self.bank.return_resources(resource_type, count)
        
        del self.players_needing_discard[player_name]
        print(f"Player {player_name} discarded {resources}")
        return True
    
    def get_robber_victims(self) -> list:
        """Get list of players with settlements/cities adjacent to robber hex.
        
        Returns:
            list: List of player names who can be stolen from
        """
        if not self.robber_hex or self.robber_hex not in self.hexes:
            return []
        
        victim_names = set()
        
        for vertex_key, vertex in self.vertices.items():
            if not vertex.building:
                continue
            if vertex.building.get('type') not in ('settlement', 'city'):
                continue
            
            if self.robber_hex in vertex.neighbors.get('hexes', []):
                player_name = vertex.building.get('player')
                if player_name:
                    victim_names.add(player_name)
        
        return list(victim_names)
    
    def steal_resource(self, victim_name: str, thief_name: str, resource_type: str = None) -> str | None:
        """Steal a random resource from a victim and give to thief.
        
        Args:
            victim_name: Name of player to steal from
            thief_name: Name of player to receive stolen resource
            resource_type: If provided, steal this specific type (for UI choice)
            
        Returns:
            str: Resource type stolen, or None if no resources to steal
        """
        victim = self.get_player(victim_name)
        if not victim:
            return None
        
        thief = self.get_player(thief_name)
        if not thief:
            return None
        
        available_resources = [r for r, count in victim.resources.items() if count > 0]
        if not available_resources:
            return None
        
        if resource_type and resource_type in available_resources:
            stolen = resource_type
        else:
            stolen = random.choice(available_resources)
        
        victim.resources[stolen] = victim.resources[stolen] - 1
        thief.resources[stolen] = thief.resources.get(stolen, 0) + 1
        return stolen
    
    def give_resource(self, player_name: str, resource_type: str) -> bool:
        """Give a resource to a player.
        
        Args:
            player_name: Name of player to receive resource
            resource_type: Resource type to give
            
        Returns:
            bool: True if resource was given
        """
        player = self.get_player(player_name)
        if not player:
            return False
        
        if self.bank.take(resource_type):
            player.resources[resource_type] = player.resources.get(resource_type, 0) + 1
            return True
        return False
    
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
    
    def buy_dev_card(self, player_name: str) -> dict:
        """Buy a development card from the bank. Returns result dict."""
        player = self.get_player(player_name)
        if not player:
            return {'success': False, 'error': 'Player not found'}
        
        if not self.can_afford(player_name, 'knight'):
            return {'success': False, 'error': 'Cannot afford development card'}
        
        card_type = self.bank.draw_dev_card()
        if not card_type:
            return {'success': False, 'error': 'No development cards left'}
        
        if not self.deduct_cost(player_name, 'knight'):
            self.bank.return_dev_card(card_type)
            return {'success': False, 'error': 'Failed to deduct cost'}
        
        player.dev_cards[card_type]['count'] += 1
        player.dev_cards[card_type]['purchase_turn'] = self.turn_count
        return {'success': True, 'card_type': card_type}
    
    def get_dev_cards_for_player(self, player_name: str) -> dict:
        """Get development cards for a specific player."""
        player = self.get_player(player_name)
        if not player:
            return {}
        return player.dev_cards.copy()
    
    def use_monopoly(self, player_name: str, resource_type: str) -> dict:
        """Use monopoly card - steal ALL of specified resource from all other players."""
        player = self.get_player(player_name)
        if not player:
            return {'success': False, 'error': 'Player not found'}
        
        if resource_type not in self.bank.resources:
            return {'success': False, 'error': 'Invalid resource type'}
        
        stolen_count = 0
        stolen_from = []
        
        for other_player in self.players:
            if other_player.name == player_name:
                continue
            
            other_resources = other_player.resources.get(resource_type, 0)
            if other_resources > 0:
                other_player.resources[resource_type] = 0
                player.resources[resource_type] = player.resources.get(resource_type, 0) + other_resources
                stolen_count += other_resources
                stolen_from.append(f"{other_player.name}({other_resources})")
        
        print(f"Player {player_name} used Monopoly on {resource_type}: stole {stolen_count} from {stolen_from}")
        return {'success': True, 'stolen_count': stolen_count, 'stolen_from': stolen_from}
    
    def can_play_dev_card(self, player_name: str, card_type: str) -> tuple:
        """Check if player can play a development card. Returns (can_play: bool, error: str)."""
        player = self.get_player(player_name)
        if not player:
            return (False, 'Player not found')
        
        card_data = player.dev_cards.get(card_type)
        if not card_data or card_data['count'] <= 0:
            return (False, 'You do not have this card')
        
        if not self.has_rolled_dice and card_type != 'knight':
            return (False, 'You must roll the dice first')
        
        if card_data['purchase_turn'] is not None and self.turn_count - card_data['purchase_turn'] < 1:
            return (False, 'Cannot play card in the same turn it was purchased')
        
        return (True, '')
    
    def start(self):
        """Start the game and shuffle player order."""
        random.shuffle(self.players)
        self.game_state = "started"
        self.start_turn()
        print(f"\n=== Game started! ===")
        print(f"Player order: {self.players}")
        print(f"Current player: {self.players[self.current_player_index]}")
        print("=====================\n")
    
    def start_turn(self):
        """Start a new turn and reset timers."""
        import time
        self.turn_start_time = time.time()
        self.dice_rolled_time = None
        self.has_rolled_dice = False
        self.free_roads_remaining = 0  # Reset free roads at start of turn
    
    def get_dice_roll_time_remaining(self) -> int:
        """Get seconds remaining for dice roll."""
        import time
        if self.turn_start_time is None or self.has_rolled_dice:
            return self.dice_roll_time_limit
        elapsed = time.time() - self.turn_start_time
        return max(0, self.dice_roll_time_limit - int(elapsed))
    
    def get_round_time_remaining(self) -> int:
        """Get seconds remaining for round (starts after dice roll)."""
        import time
        if self.turn_start_time is None:
            return self.round_time_limit
        # If dice not rolled yet, return full time (will be shown as "-")
        if not self.has_rolled_dice:
            return self.round_time_limit
        # Calculate from dice roll time
        if self.dice_rolled_time is None:
            return self.round_time_limit
        elapsed = time.time() - self.dice_rolled_time
        return max(0, self.round_time_limit - int(elapsed))
    
    def is_dice_roll_expired(self) -> bool:
        """Check if dice roll time has expired."""
        if self.has_rolled_dice:
            return False
        return self.get_dice_roll_time_remaining() <= 0
    
    def is_round_expired(self) -> bool:
        """Check if round time has expired."""
        return self.get_round_time_remaining() <= 0
    
    def set_dice_rolled(self):
        """Mark that dice has been rolled."""
        import time
        self.has_rolled_dice = True
        self.dice_rolled_time = time.time()
    
    def calculate_longest_road(self, player_name: str) -> int:
        """Calculate longest road for a player, respecting road blocks."""
        player = self.get_player(player_name)
        if not player:
            return 0
        
        player_roads = [edge_key for edge_key, edge in self.edges.items() 
                       if edge.road and edge.road.get('player') == player_name]
        
        if not player_roads:
            return 0
        
        def has_other_player_building(vertex_key):
            """Check if vertex has another player's building."""
            vertex = self.vertices.get(vertex_key)
            if vertex and vertex.building:
                building_player = vertex.building.get('player')
                if building_player and building_player != player_name:
                    return True
            return False
        
        def find_road_endpoints():
            """Find vertices that are endpoints of player's roads (have exactly 1 road connected).
            Also filter out vertices blocked by other player's buildings."""
            vertex_road_count = {}
            for edge_key in player_roads:
                edge = self.edges[edge_key]
                for vertex_key in edge.neighbors.get('vertices', []):
                    vertex_road_count[vertex_key] = vertex_road_count.get(vertex_key, 0) + 1
            
            # Endpoints have exactly 1 road AND no other player's building at the start
            return [v for v, count in vertex_road_count.items() 
                    if count == 1 and not has_other_player_building(v)]
        
        def dfs(vertex_key, visited_edges):
            """DFS to find longest path from current vertex."""
            max_length = len(visited_edges)
            
            # Get all connected edges
            vertex = self.vertices.get(vertex_key)
            if not vertex:
                return max_length
            
            for edge_key in vertex.neighbors.get('edges', []):
                if edge_key in visited_edges:
                    continue
                
                # Check if this is player's road
                edge = self.edges.get(edge_key)
                if not edge or not edge.road or edge.road.get('player') != player_name:
                    continue
                
                # Find the next vertex
                edge_vertices = edge.neighbors.get('vertices', [])
                next_vertex = None
                for v in edge_vertices:
                    if v != vertex_key:
                        next_vertex = v
                        break
                
                if not next_vertex:
                    continue
                
                # Check if blocked by other player's building at the next vertex
                if has_other_player_building(next_vertex):
                    # Blocked - can't pass through another player's building
                    # But can count the road leading TO it
                    max_length = max(max_length, len(visited_edges) + 1)
                    continue
                
                # Continue through empty vertices or player's own buildings
                result = dfs(next_vertex, visited_edges + [edge_key])
                max_length = max(max_length, result)
            
            return max_length
        
        # Find longest path from each valid endpoint
        endpoints = find_road_endpoints()
        
        # If no valid endpoints (all blocked), try finding any starting point
        if not endpoints:
            for edge_key in player_roads:
                edge = self.edges[edge_key]
                for v in edge.neighbors.get('vertices', []):
                    if not has_other_player_building(v):
                        endpoints.append(v)
                        break
                if endpoints:
                    break
        
        max_length = 0
        for endpoint in endpoints:
            length = dfs(endpoint, [])
            max_length = max(max_length, length)
        
        return max_length
    
    def update_longest_road(self):
        """Update longest road holder after road placement."""
        max_length = 0
        longest_holder = None
        
        for player in self.players:
            length = self.calculate_longest_road(player.name)
            self.longest_road_length[player.name] = length
            
            if length > max_length:
                max_length = length
                longest_holder = player.name
        
        # Only update if someone has 5+ roads
        if max_length >= 5:
            if self.longest_road_holder != longest_holder:
                old_holder = self.longest_road_holder
                self.longest_road_holder = longest_holder
                if longest_holder:
                    print(f"Longest Road! {longest_holder} now has {max_length} roads (took from {old_holder})")
    
    def update_largest_army(self):
        """Update largest army holder after playing knight."""
        max_knights = 0
        army_holder = None
        
        for player in self.players:
            knights = player.knights_played
            self.knights_played[player.name] = knights
            
            if knights > max_knights:
                max_knights = knights
                army_holder = player.name
        
        # Only update if someone has 3+ knights
        if max_knights >= 3:
            if self.largest_army_holder != army_holder:
                old_holder = self.largest_army_holder
                self.largest_army_holder = army_holder
                if army_holder:
                    print(f"Largest Army! {army_holder} now has {max_knights} knights (took from {old_holder})")

