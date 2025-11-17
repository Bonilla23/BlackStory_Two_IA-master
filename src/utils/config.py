import os
import argparse
from typing import Dict, Any

class Config:
    """
    Handles configuration loading from environment variables and CLI arguments.
    """

    def __init__(self):
        self.narrator_model: str = "gemini:gemini-2.5-flash"
        self.detective_model: str = "gemini:gemini-2.5-flash"
        self.difficulty: str = "media"
        self.question_limits: Dict[str, int] = {
            "facil": 20,
            "media": 10,
            "dificil": 5,
        }
        self.gemini_api_key: str | None = None
        self.ollama_host: str = "http://localhost:11434" # Changed to ollama_host
        self._load_env_vars()
        self._parse_cli_args()

    def _load_env_vars(self) -> None:
        """
        Loads environment variables from a .env file if it exists, then from the system.
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("Warning: python-dotenv not installed. Environment variables must be set manually.")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.ollama_host = os.getenv("OLLAMA_HOST", self.ollama_host) # Changed to OLLAMA_HOST

    def _parse_cli_args(self) -> None:
        """
        Parses command-line arguments and updates configuration.
        """
        parser = argparse.ArgumentParser(description="Black Stories AI Game")
        parser.add_argument(
            "-narrador",
            type=str,
            default=self.narrator_model,
            help="Provider and model for the Narrator AI (e.g., gemini:gemini-2.0-flash)",
        )
        parser.add_argument(
            "-detective",
            type=str,
            default=self.detective_model,
            help="Provider and model for the Detective AI (e.g., ollama:llama2)",
        )
        parser.add_argument(
            "-dificultad",
            type=str,
            default=self.difficulty,
            choices=["facil", "media", "dificil"],
            help="Difficulty level (facil, media, dificil)",
        )

        args = parser.parse_args()

        if args.narrador != self.narrator_model:
            self.narrator_model = args.narrador
            print(f"INFO: Narrator model set to: {self.narrator_model}")
        else:
            print(f"INFO: Using default Narrator model: {self.narrator_model}")

        if args.detective != self.detective_model:
            self.detective_model = args.detective
            print(f"INFO: Detective model set to: {self.detective_model}")
        else:
            print(f"INFO: Using default Detective model: {self.detective_model}")

        if args.dificultad != self.difficulty:
            self.difficulty = args.dificultad
            print(f"INFO: Difficulty set to: {self.difficulty}")
        else:
            print(f"INFO: Using default difficulty: {self.difficulty}")

    def get_config(self) -> Dict[str, Any]:
        """
        Returns the current configuration as a dictionary.
        """
        return {
            "narrator_model": self.narrator_model,
            "detective_model": self.detective_model,
            "difficulty": self.difficulty,
            "question_limits": self.question_limits,
            "gemini_api_key": self.gemini_api_key,
            "ollama_host": self.ollama_host,
        }
