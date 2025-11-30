import json
import os
from json_repair import repair_json
from datetime import datetime
from typing import List, Tuple
from src.services.api_client import APIClient
from src.models.story import Story
from src.config.prompts import get_narrator_prompt, get_narrator_validation_prompt
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
        self.log_dir = "logs" # Directory to save conversation logs
        self.conversation_history: List[str] = [] # Stores the full conversation history

    def _get_narrator_prompt(self, question: str, qa_history: List[Tuple[str, str]]) -> str:
        """
        Constructs the prompt for the Narrator AI to answer a question.
        """
        return get_narrator_prompt(
            self.story.mystery_situation,
            self.story.hidden_solution,
            qa_history,
            question
        )

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
                    self.conversation_history.append(f"Detective: {question}\nNarrador: {response}")
                    return response
                else:
                    # If the AI doesn't follow the rules, try again with a stricter prompt
                    # In web context, we'll just raise an error to be caught by the game engine
                    raise ValueError(f"Narrator gave an invalid response: '{response}'. Expected 'sí', 'no', or 'no es relevante'.")
            except ConnectionError as e:
                raise ConnectionError(f"Error de conexión con el Narrador: {e}")

    def _get_validation_prompt(self, detective_solution: str) -> str:
        """
        Constructs the prompt for the Narrator AI to validate the detective's solution.
        """
        return get_narrator_validation_prompt(
            self.story.mystery_situation,
            self.story.hidden_solution,
            detective_solution,
            self.difficulty
        )

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

                try:
                    validation_data = json.loads(response_text)
                except json.JSONDecodeError:
                     # If standard parsing fails, try to repair it
                    repaired_json = repair_json(response_text)
                    validation_data = json.loads(repaired_json)

                verdict = validation_data.get("veredicto", "Incorrecto")
                analysis = validation_data.get("analisis", "No se pudo generar un análisis detallado.")
                
                validation_log = (
                    f"Detective's Solution: {detective_solution}\n"
                    f"Narrator's Verdict: {verdict}\n"
                    f"Narrator's Analysis: {analysis}"
                )
                self.conversation_history.append(validation_log)
                
                return verdict, analysis
            except json.JSONDecodeError as e:
                # In web context, we'll just raise an error to be caught by the game engine
                raise ValueError(f"Narrator gave an invalid JSON response during validation. Raw response: '{response_text}'. Error: {e}")
            except (ConnectionError, ValueError, KeyError) as e:
                raise type(e)(f"Error al validar la solución con el Narrador: {e}")

    def save_full_conversation(self) -> None:
        """
        Saves the entire accumulated conversation history to a single file.
        """
        if not self.conversation_history:
            print("No hay conversación para guardar.")
            return

        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.log_dir, f"full_conversation_{timestamp}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self.conversation_history))
            print(f"Conversación completa guardada en {filename}")
            self.conversation_history = [] # Clear history after saving
        except IOError as e:
            print(f"Error al guardar la conversación completa en {filename}: {e}")
