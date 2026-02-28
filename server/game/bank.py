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
    
    def __str__(self) -> str:
        """String representation for logging."""
        return ', '.join(f"{count} {resource}" 
                        for resource, count in self.resources.items())
