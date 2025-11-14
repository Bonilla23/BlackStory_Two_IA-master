import json
from typing import List, Tuple
from src.services.api_client import APIClient
from src.models.story import Story
from src.utils.display import display_error_and_retry

class Narrator:
    """
    Manages the Narrator AI's role in the Black Stories game.
    Responds to questions and validates the detective's solution.
    """

    def __init__(self, api_client: APIClient, narrator_model: str, story: Story, difficulty: str):
        self.api_client = api_client
        self.narrator_model = narrator_model
        self.story = story
        self.difficulty = difficulty

    def _get_narrator_prompt(self, question: str, qa_history: List[Tuple[str, str]]) -> str:
        """
        Constructs the prompt for the Narrator AI to answer a question.
        """
        history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
        if history_str:
            history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

        return f"""
        Eres la IA Narrador en un interrogatorio policial formal.
        Conoces la siguiente historia completa:
        Situación misteriosa: {self.story.mystery_situation}
        Solución oculta: {self.story.hidden_solution}

        Tu rol es responder ESTRICTAMENTE solo con "sí", "no" o "no es relevante" a las preguntas del Detective.
        Mantén un tono profesional y formal. No des pistas adicionales ni explicaciones.

        {history_str}

        Pregunta del Detective: "{question}"
        Tu respuesta (sí/no/no es relevante):
        """

    def answer_question(self, question: str, qa_history: List[Tuple[str, str]]) -> str:
        """
        Gets an answer from the Narrator AI for a given question.
        Handles connection errors with retry mechanism.
        """
        prompt = self._get_narrator_prompt(question, qa_history)
        while True:
            try:
                response = self.api_client.generate_text(self.narrator_model, prompt).strip().lower()
                # Clean the response to remove any leading "narrador:" and punctuation
                if response.startswith("narrador:"):
                    response = response[len("narrador:"):].strip()
                response = response.rstrip('.,!?;')

                if response in ["sí", "si", "no", "no es relevante"]:
                    return response
                else:
                    # If the AI doesn't follow the rules, try again with a stricter prompt
                    print(f"DEBUG: Narrator gave an invalid response: '{response}'. Retrying...")
                    prompt += "\n\nADVERTENCIA: Debes responder ESTRICTAMENTE solo 'sí', 'no' o 'no es relevante'."
            except ConnectionError as e:
                if not display_error_and_retry(f"Error de conexión con el Narrador: {e}"):
                    raise

    def _get_validation_prompt(self, detective_solution: str) -> str:
        """
        Constructs the prompt for the Narrator AI to validate the detective's solution.
        """
        difficulty_criteria = {
            "facil": "La evaluación es flexible; capturar el concepto principal es suficiente.",
            "media": "La evaluación es moderada; debe capturar la esencia de lo que pasó.",
            "dificil": "La evaluación es estricta; debe mencionar todos los elementos clave de la solución.",
        }

        return f"""
        Eres la IA Narrador y tu tarea es validar la solución propuesta por el Detective.
        Conoces la historia completa:
        Situación misteriosa: {self.story.mystery_situation}
        Solución oculta: {self.story.hidden_solution}

        El Detective ha propuesto la siguiente solución:
        "{detective_solution}"

        Criterio de dificultad para la validación ({self.difficulty}): {difficulty_criteria[self.difficulty]}

        Por favor, evalúa la solución del Detective y proporciona tu veredicto y un análisis detallado en formato JSON:
        {{
            "veredicto": "Correcto" o "Incorrecto",
            "analisis": "Explicación detallada de por qué la solución es correcta o incorrecta,
                         incluyendo elementos que acertó, elementos que falló,
                         elementos que le faltaron, y cómo se aplica el criterio de dificultad."
        }}
        """

    def validate_solution(self, detective_solution: str) -> Tuple[str, str]:
        """
        Validates the detective's final solution using the Narrator AI.
        Returns a tuple: (verdict, analysis).
        Handles connection errors with retry mechanism.
        """
        prompt = self._get_validation_prompt(detective_solution)
        while True:
            try:
                response_text = self.api_client.generate_text(self.narrator_model, prompt)
                
                # Clean the response to remove markdown code blocks if present
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[len("```json"):].strip()
                    if response_text.endswith("```"):
                        response_text = response_text[:-len("```")].strip()

                validation_data = json.loads(response_text)
                verdict = validation_data.get("veredicto", "Incorrecto")
                analysis = validation_data.get("analisis", "No se pudo generar un análisis detallado.")
                return verdict, analysis
            except json.JSONDecodeError as e:
                print(f"DEBUG: Narrator gave an invalid JSON response during validation. Raw response: '{response_text}'. Retrying...")
                prompt += "\n\nADVERTENCIA: Debes responder ESTRICTAMENTE en formato JSON como se especificó, SIN bloques de código markdown (```json ... ```)."
            except (ConnectionError, ValueError, KeyError) as e:
                if not display_error_and_retry(f"Error al validar la solución con el Narrador: {e}"):
                    raise
