from src.utils.config import Config
from src.game.game_engine import GameEngine

def main():
    """
    Main entry point for the Black Stories AI game.
    Initializes configuration and starts the game engine.
    """
    config_loader = Config()
    game_config = config_loader.get_config()

    game_engine = GameEngine(game_config)
    for output in game_engine.run(
        difficulty=game_config["difficulty"],
        narrator_model=game_config["narrator_model"],
        detective_model=game_config["detective_model"]
    ):
        print(output)

if __name__ == "__main__":
    main()
