import random


class Game:
    def __init__(self, players: list, observers: list):
        self.players = players
        self.observers = observers
        self.current_player_index = 0
        self.game_state = "waiting"

    def add_observer(self, name):
        if name not in self.observers:
            self.observers.append(name)

    def remove_observer(self, name):
        if name in self.observers:
            self.observers.remove(name)

    def is_player(self, name):
        return name in self.players

    def start(self):
        random.shuffle(self.players)
        self.game_state = "started"
        print(f"\n=== Game started! ===")
        print(f"Player order: {self.players}")
        print(f"Current player: {self.players[self.current_player_index]}")
        print("=====================\n")
