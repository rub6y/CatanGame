import random


class Game:
    def __init__(self, players: list):
        self.players = players
        self.current_player_index = 0
        self.game_state = "waiting"

    def start(self):
        random.shuffle(self.players)
        self.game_state = "started"
        print(f"\n=== Game started! ===")
        print(f"Player order: {self.players}")
        print(f"Current player: {self.players[self.current_player_index]}")
        print("=====================\n")
