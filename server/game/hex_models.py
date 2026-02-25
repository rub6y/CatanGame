"""
Hex models for Catan board representation.

This module defines the three core classes for representing a Catan board:
- Hex: A single tile on the board (resource, desert, or ocean)
- Vertex: A corner where 3 hexes meet (can have settlement/city)
- Edge: An edge between two hexes (can have road)

Uses a cube coordinate system as described in hex.md for unique keys
and algebraic neighbor relationships.
"""


class Hex:
    """
    Represents a single hex tile on the Catan board.
    
    Attributes:
        key (str): Unique identifier in "x,y,z" format from cube coordinates.
                   Example: "3,-3,0" for the center hex in a radius-1 board.
        type (str): Resource type - "ore", "wheat", "sheep", "brick", "wood",
                    "desert", or "ocean".
        number (int or None): Dice number token (2-12) for resource hexes,
                              None for desert and ocean tiles.
        neighbors (list): List of adjacent hex keys.
    """
    
    def __init__(self, key: str, hex_type: str, number: int | None):
        """
        Initialize a Hex object.
        
        Args:
            key: Unique coordinate key in "x,y,z" format
            hex_type: Resource type or special tile type
            number: Dice number (2-12) or None for desert/ocean
        """
        self.key = key
        self.type = hex_type
        self.number = number
        self.neighbors = []


class Vertex:
    """
    Represents a corner where 3 hexes meet.
    
    Vertices are the positions where settlements and cities can be built.
    Each vertex touches exactly 3 hexes and has 3 adjacent edges.
    
    Attributes:
        key (str): Unique identifier in "x,y,z" cube coordinate format.
                   Note: Vertices have no coordinate divisible by 3.
        building (dict or None): Contains {"type": "settlement"/"city", 
                                    "player": player_name} if occupied.
        neighbors (dict): Dictionary with keys:
            - "hexes": List of 3 adjacent hex keys
            - "edges": List of 3 adjacent edge keys  
            - "vertices": List of adjacent vertex keys
    """
    
    def __init__(self, key: str):
        """
        Initialize a Vertex object.
        
        Args:
            key: Unique coordinate key in "x,y,z" format
        """
        self.key = key
        self.building = None  # {"type": "settlement"/"city", "player": name}
        self.neighbors = {
            "hexes": [],      # 3 adjacent hex keys
            "edges": [],      # 3 adjacent edge keys
            "vertices": []    # Adjacent vertex keys
        }


class Edge:
    """
    Represents an edge between two hexes.
    
    Edges are the positions where roads can be built.
    Each edge is shared by exactly 2 hexes and connects 2 vertices.
    
    Attributes:
        key (str): Unique identifier in "x,y,z" cube coordinate format.
                   Note: Edges have exactly one coordinate divisible by 3.
        road (dict or None): Contains {"player": player_name} if occupied.
        neighbors (dict): Dictionary with keys:
            - "hexes": List of 2 adjacent hex keys
            - "edges": List of adjacent edge keys
            - "vertices": List of 2 adjacent vertex keys
    """
    
    def __init__(self, key: str):
        """
        Initialize an Edge object.
        
        Args:
            key: Unique coordinate key in "x,y,z" format
        """
        self.key = key
        self.road = None  # {"player": name}
        self.neighbors = {
            "hexes": [],      # 2 adjacent hex keys
            "edges": [],      # Adjacent edge keys
            "vertices": []    # 2 adjacent vertex keys
        }
