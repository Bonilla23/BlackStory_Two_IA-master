from typing import List, Tuple
from src.services.api_client import APIClient
from src.models.story import Story
from src.utils.display import display_error_and_retry

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
        history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
        if history_str:
            history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

        return f"""
        Eres la IA Detective en un interrogatorio policial formal.
        Tu objetivo es descubrir la solución a la siguiente situación misteriosa:
        Situación misteriosa: {self.mystery_situation}

        Mantén un tono profesional como un investigador experimentado.
        Puedes hacer preguntas al Narrador, quien solo responderá "sí", "no" o "no es relevante".
        Cuando creas que tienes la solución, indica explícitamente que estás listo para resolver
        usando frases como "Creo que ya lo tengo", "Voy a resolver", "Tengo la solución", etc.
        Después de indicar que estás listo, tu siguiente turno será para dar la solución final.
        Tienes UNA única oportunidad para dar la solución final.

        {history_str}

        Tu siguiente acción (pregunta o indicación de que estás listo para resolver).
        Asegúrate de que tu respuesta sea una pregunta directa o una de las frases para resolver.
        NO incluyas "Detective:" al inicio de tu pregunta.
        """

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
        history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
        if history_str:
            history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

        return f"""
        Eres la IA Detective. Has indicado que estás listo para resolver la situación misteriosa.
        Esta es tu ÚNICA oportunidad para dar la solución final.
        Basado en la siguiente situación misteriosa y el historial de preguntas y respuestas:
        Situación misteriosa: {self.mystery_situation}
        {history_str}

        Por favor, proporciona tu solución final de manera clara y concisa:
        """

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
