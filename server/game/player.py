"""
Player class for Catan game.
"""


class Player:
    """
    Represents a player in the game.
    
    Attributes:
        name (str): Player's unique identifier.
        color (str): Hex color code for visual representation.
        resources (dict): Resource cards held {resource_type: count}.
        settlements (list): Vertex keys where settlements are built.
        cities (list): Vertex keys where cities are built.
        roads (list): Edge keys where roads are built.
        victory_points (int): Total victory points.
    """
    
    def __init__(self, name: str, color: str = None):
        self.name = name
        self.color = color
        self.resources = {}
        self.settlements = []
        self.cities = []
        self.roads = []
        self.victory_points = 0
    
    def set_color(self, color: str):
        """Set or update the player's color."""
        self.color = color
    
    def to_dict(self) -> dict:
        """Convert player to dictionary for serialization."""
        return {
            'name': self.name,
            'color': self.color,
            'resources': self.resources,
            'settlements': self.settlements,
            'cities': self.cities,
            'roads': self.roads,
            'victory_points': self.victory_points
        }
