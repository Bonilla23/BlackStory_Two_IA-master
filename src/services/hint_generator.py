from typing import List, Tuple
from src.services.api_client import APIClient
from src.config.prompts import get_hint_prompt

class HintGenerator:
    """
    Generates hints for the player using an AI model.
    """

    def __init__(self, api_client: APIClient, model: str):
        self.api_client = api_client
        self.model = model

    def generate_hint(self, mystery_situation: str, hidden_solution: str, qa_history: List[Tuple[str, str]]) -> str:
        """
        Generates a hint based on the current game state.
        """
        prompt = get_hint_prompt(mystery_situation, hidden_solution, qa_history)
        try:
            hint = self.api_client.generate_text(self.model, prompt).strip()
            # Clean up if the model adds quotes or prefixes
            if hint.startswith('"') and hint.endswith('"'):
                hint = hint[1:-1]
            if hint.lower().startswith("pista:"):
                hint = hint[6:].strip()
            return hint
        except Exception as e:
            return f"Lo siento, no puedo generar una pista en este momento. Error: {e}"
