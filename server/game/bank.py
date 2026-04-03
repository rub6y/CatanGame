class Bank:
    """Manages the resource bank for Catan game."""
    
    def __init__(self, resource_limit: int = 19):
        self.resource_limit = resource_limit
        self.resources = {
            'wood': resource_limit,
            'brick': resource_limit,
            'sheep': resource_limit,
            'wheat': resource_limit,
            'ore': resource_limit
        }
        self.dev_cards_deck = {
            'knight': 14,
            'two_roads': 2,
            'invention': 2,
            'monopoly': 2,
            'victory_point': 5
        }
    
    def take(self, resource_type: str, amount: int = 1) -> bool:
        """Take resources from bank. Returns True if successful, False if insufficient."""
        if self.resources.get(resource_type, 0) >= amount:
            self.resources[resource_type] -= amount
            return True
        return False
    
    def return_resources(self, resource_type: str, amount: int = 1):
        """Return resources to bank (up to resource_limit)."""
        self.resources[resource_type] = min(
            self.resources.get(resource_type, 0) + amount,
            self.resource_limit
        )
    
    def get_all(self) -> dict:
        """Get copy of all bank resources."""
        return self.resources.copy()
    
    def draw_dev_card(self) -> str | None:
        """Draw a development card from the deck. Returns card type or None if deck empty."""
        available_cards = [card_type for card_type, count in self.dev_cards_deck.items() if count > 0]
        if not available_cards:
            return None
        
        import random
        card_type = random.choice(available_cards)
        self.dev_cards_deck[card_type] -= 1
        return card_type
    
    def return_dev_card(self, card_type: str):
        """Return a development card to the deck."""
        if card_type in self.dev_cards_deck:
            self.dev_cards_deck[card_type] += 1
    
    def get_dev_card_counts(self) -> dict:
        """Get copy of dev card deck counts."""
        return self.dev_cards_deck.copy()
    
    def __str__(self) -> str:
        """String representation for logging."""
        return ', '.join(f"{count} {resource}" 
                        for resource, count in self.resources.items())
