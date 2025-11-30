from typing import List, Tuple
from src.services.api_client import APIClient
from src.models.story import Story
from src.utils.display import display_error_and_retry
from src.config.prompts import get_detective_prompt, get_detective_final_solution_prompt

class Detective:
    """
    Manages the Detective AI's role in the Black Stories game.
    Asks questions and attempts to solve the mystery.
    """

    def __init__(self, api_client: APIClient, detective_model: str, mystery_situation: str):
        self.api_client = api_client
        self.detective_model = detective_model
        self.mystery_situation = mystery_situation
        self.ready_to_solve_phrases = [
            "creo que ya lo tengo",
            "voy a resolver",
            "tengo la solución",
            "estoy listo para resolver",
            "es hora de la solución",
            "solución final"
        ]

    def _get_detective_prompt(self, qa_history: List[Tuple[str, str]]) -> str:
        """
        Constructs the prompt for the Detective AI to ask a question or attempt a solution.
        """
        return get_detective_prompt(self.mystery_situation, qa_history)

    def ask_question_or_solve(self, qa_history: List[Tuple[str, str]]) -> str:
        """
        Gets a question or a solution attempt from the Detective AI.
        The response will be cleaned to remove any leading "Detective: " if present.
        Gets a question or a solution attempt from the Detective AI.
        The response will be cleaned to remove any leading "Detective: " if present.
        Handles connection errors with retry mechanism.
        """
        prompt = self._get_detective_prompt(qa_history)
        while True:
            try:
                response = self.api_client.generate_text(self.detective_model, prompt).strip()
                # Clean the response to remove any leading "Detective: "
                if response.lower().startswith("detective:"):
                    response = response[len("detective:"):].strip()
                return response
            except ConnectionError as e:
                if not display_error_and_retry(f"Error de conexión con el Detective: {e}"):
                    raise

    def is_ready_to_solve(self, response: str) -> bool:
        """
        Checks if the detective's response indicates readiness to solve.
        """
        return any(phrase in response.lower() for phrase in self.ready_to_solve_phrases)

    def get_final_solution_prompt(self, qa_history: List[Tuple[str, str]]) -> str:
        """
        Constructs a prompt specifically for the Detective to provide the final solution.
        """
        return get_detective_final_solution_prompt(self.mystery_situation, qa_history)

    def provide_final_solution(self, qa_history: List[Tuple[str, str]]) -> str:
        """
        Gets the final solution from the Detective AI.
        Handles connection errors with retry mechanism.
        """
        prompt = self.get_final_solution_prompt(qa_history)
        while True:
            try:
                response = self.api_client.generate_text(self.detective_model, prompt).strip()
                return response
            except ConnectionError as e:
                if not display_error_and_retry(f"Error de conexión al obtener la solución final del Detective: {e}"):
                    raise
