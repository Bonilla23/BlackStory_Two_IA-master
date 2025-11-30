import json
import asyncio
from typing import Dict, Any, AsyncGenerator

from src.models.game_state import GameState
from src.models.story import Story
from src.services.api_client import APIClient
from src.services.story_generator import StoryGenerator
from src.services.narrator import Narrator
from src.services.detective import Detective

class FightEngine:
    """
    Orchestrates the Black Stories AI fight mode, managing two independent detective AIs
    against a single narrator.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = APIClient(config)
        self.game_state_det1: GameState | None = None
        self.game_state_det2: GameState | None = None
        self.narrator_ai: Narrator | None = None
        self.story: Story | None = None

    async def _initialize_fight(self, narrator_model: str, detective_model_1: str, detective_model_2: str) -> AsyncGenerator[str, None]:
        """
        Initializes the fight by generating a story and setting up AI roles.
        """
        yield json.dumps({"type": "narrator", "content": "Narrador: Iniciando la generación de la historia..."})
        story_generator = StoryGenerator(self.api_client, narrator_model)
        
        retries = 3
        for attempt in range(retries):
            try:
                print(f"DEBUG: Attempt {attempt + 1}/{retries} - Calling story_generator.generate_story (wrapped in asyncio.to_thread)...")
                self.story = await asyncio.to_thread(story_generator.generate_story, "fight_mode") # Use a generic difficulty for story generation
                print(f"DEBUG: Attempt {attempt + 1}/{retries} - Returned from story_generator.generate_story.")
                
                # Explicit check and logging for story content
                if self.story and self.story.mystery_situation and self.story.hidden_solution:
                    yield json.dumps({"type": "narrator", "content": "Narrador: ¡Historia generada con éxito!"})
                    yield json.dumps({"type": "narrator", "content": f"Misterio para los Detectives: {self.story.mystery_situation}"})
                    print(f"DEBUG: Story generated: Mystery='{self.story.mystery_situation[:50]}...', Solution='{self.story.hidden_solution[:50]}...'")
                else:
                    error_msg = "Narrador: Error: La historia se generó, pero el contenido está vacío o incompleto."
                    yield json.dumps({"type": "error", "content": error_msg})
                    print(f"ERROR: {error_msg} Story object: {self.story}")
                    # If story is empty/incomplete, we should retry or raise
                    if attempt + 1 == retries:
                        raise ValueError("Story content is empty or incomplete after generation.")
                    continue # Try again if content is bad but no exception was raised
                break # Exit loop if story is successfully generated and valid
            except Exception as e:
                error_msg = f"Error al generar la historia (intento {attempt + 1}/{retries}): {e}"
                yield json.dumps({"type": "error", "content": error_msg})
                print(f"ERROR in _initialize_fight: {error_msg}") # Added more specific debug
                if attempt + 1 == retries:
                    raise
        
        # After the loop, if self.story is still None or invalid, raise an error
        if not self.story or not self.story.mystery_situation or not self.story.hidden_solution:
            print("ERROR: Final check - Story generation failed or content is invalid after all attempts.")
            raise RuntimeError("La generación de la historia falló o el contenido no es válido después de varios intentos.")

        self.game_state_det1 = GameState(
            narrator_model=narrator_model,
            detective_model=detective_model_1,
            difficulty=self.config["difficulty"],
            mystery_situation=self.story.mystery_situation,
            hidden_solution=self.story.hidden_solution,
        )
        self.game_state_det2 = GameState(
            narrator_model=narrator_model,
            detective_model=detective_model_2,
            difficulty=self.config["difficulty"],
            mystery_situation=self.story.mystery_situation,
            hidden_solution=self.story.hidden_solution,
        )

        yield json.dumps({"type": "narrator", "content": "============================================================"})
        yield json.dumps({"type": "narrator", "content": "                  BLACK STORIES AI - MODO PELEA"})
        yield json.dumps({"type": "narrator", "content": "============================================================"})
        yield json.dumps({"type": "narrator", "content": f"Narrador: {narrator_model}"})
        yield json.dumps({"type": "narrator", "content": f"Detective 1: {detective_model_1}"})
        yield json.dumps({"type": "narrator", "content": f"Detective 2: {detective_model_2}"})
        yield json.dumps({"type": "narrator", "content": "------------------------------------------------------------"})
        yield json.dumps({"type": "narrator", "content": "============================================================"})

    async def _perform_detective_turn(self, detective_id: int, detective_ai: Detective, narrator_ai: Narrator, game_state: GameState, max_questions: int) -> AsyncGenerator[str, None]:
        """
        Performs a single question-and-answer turn for a detective.
        """
        if len(game_state.qa_history) >= max_questions:
            yield json.dumps({"type": f"detective{detective_id}_question", "content": f"¡Se ha alcanzado el límite de {max_questions} preguntas para el Detective {detective_id}!"})
            # Optionally, force a final solution attempt here if not already done
            if not game_state.detective_solution_attempt:
                solution_attempt = detective_ai.provide_final_solution(game_state.qa_history)
                game_state.detective_solution_attempt = solution_attempt
                game_state.detective_solved = True # Mark as solved for completion logic
                yield json.dumps({"type": f"detective{detective_id}_question", "content": f"Detective {detective_id} presenta su solución final: {solution_attempt}"})
            return

        detective_response = detective_ai.ask_question_or_solve(game_state.qa_history)

        if detective_ai.is_ready_to_solve(detective_response):
            game_state.detective_solution_attempt = detective_ai.provide_final_solution(game_state.qa_history)
            game_state.detective_solved = True
            yield json.dumps({"type": f"detective{detective_id}_question", "content": f"Detective {detective_id} dice: ¡Estoy listo para resolver! Mi solución es: {game_state.detective_solution_attempt}"})
            return

        narrator_answer = await asyncio.to_thread(narrator_ai.answer_question, detective_response, game_state.qa_history) # Run sync in thread
        game_state.qa_history.append((detective_response, narrator_answer))
        
        yield json.dumps({"type": f"detective{detective_id}_question", "content": f"Detective {detective_id} pregunta: {detective_response}"})
        yield json.dumps({"type": "narrator", "content": f"Narrador responde a Detective {detective_id}: {narrator_answer}"})
        
        await asyncio.sleep(0.5) # Small delay for readability

    async def _run_fight_loop(self) -> AsyncGenerator[str, None]:
        """
        Runs the main fight loop where two detectives take turns asking questions.
        """
        if not self.game_state_det1 or not self.game_state_det2 or not self.story:
            raise RuntimeError("Fight not initialized.")

        self.narrator_ai = Narrator(
            self.api_client,
            self.game_state_det1.narrator_model, # Narrator model is same for both
            self.story,
            self.game_state_det1.difficulty,
        )

        detective1_ai = Detective(
            self.api_client, self.game_state_det1.detective_model, self.game_state_det1.mystery_situation
        )
        detective2_ai = Detective(
            self.api_client, self.game_state_det2.detective_model, self.game_state_det2.mystery_situation
        )

        max_questions = self.config["question_limits"].get(self.game_state_det1.difficulty, 10)

        turn_counter = 0
        while not self.game_state_det1.detective_solved and not self.game_state_det2.detective_solved and \
              (len(self.game_state_det1.qa_history) < max_questions or len(self.game_state_det2.qa_history) < max_questions):

            turn_counter += 1
            yield json.dumps({"type": "narrator", "content": f"--- Ronda {turn_counter} ---"})
            
            # Detective 1's turn
            if not self.game_state_det1.detective_solved:
                yield json.dumps({"type": "narrator", "content": "Turno del Detective 1:"})
                async for msg in self._perform_detective_turn(1, detective1_ai, self.narrator_ai, self.game_state_det1, max_questions):
                    yield msg
                if self.game_state_det1.detective_solved:
                    yield json.dumps({"type": "narrator", "content": f"Detective 1 ha finalizado."})
            
            # Detective 2's turn
            if not self.game_state_det2.detective_solved:
                yield json.dumps({"type": "narrator", "content": "Turno del Detective 2:"})
                async for msg in self._perform_detective_turn(2, detective2_ai, self.narrator_ai, self.game_state_det2, max_questions):
                    yield msg
                if self.game_state_det2.detective_solved:
                    yield json.dumps({"type": "narrator", "content": f"Detective 2 ha finalizado."})

            if self.game_state_det1.detective_solved and self.game_state_det2.detective_solved:
                break # Both have solved or reached limits

            if len(self.game_state_det1.qa_history) >= max_questions and len(self.game_state_det2.qa_history) >= max_questions:
                yield json.dumps({"type": "narrator", "content": "Ambos detectives han alcanzado el límite de preguntas."})
                break

        # Ensure final solution attempts are recorded if they haven't already
        if not self.game_state_det1.detective_solved and len(self.game_state_det1.qa_history) >= max_questions:
            self.game_state_det1.detective_solution_attempt = detective1_ai.provide_final_solution(self.game_state_det1.qa_history)
            self.game_state_det1.detective_solved = True
        if not self.game_state_det2.detective_solved and len(self.game_state_det2.qa_history) >= max_questions:
            self.game_state_det2.detective_solution_attempt = detective2_ai.provide_final_solution(self.game_state_det2.qa_history)
            self.game_state_det2.detective_solved = True


    async def _finalize_fight(self) -> AsyncGenerator[str, None]:
        """
        Finalizes the fight by validating each detective's solution and determining the winner.
        """
        if not self.game_state_det1 or not self.game_state_det2 or not self.narrator_ai:
            raise RuntimeError("Fight not initialized or narrator_ai not set.")

        summary_messages = []
        
        # Finalize Detective 1
        verdict1, analysis1 = "No solution provided", ""
        if self.game_state_det1.detective_solution_attempt:
            # Validate solution without passing qa_history, as Narrator.validate_solution does not accept it.
            verdict1, analysis1 = await asyncio.to_thread(self.narrator_ai.validate_solution, self.game_state_det1.detective_solution_attempt)
        
        # Finalize Detective 2
        verdict2, analysis2 = "No solution provided", ""
        if self.game_state_det2.detective_solution_attempt:
            # Validate solution without passing qa_history, as Narrator.validate_solution does not accept it.
            verdict2, analysis2 = await asyncio.to_thread(self.narrator_ai.validate_solution, self.game_state_det2.detective_solution_attempt)

        # Determine Winner
        winner = None
        winner_rationale = ""

        # Case 1: Both correct
        if verdict1.lower() == "correcto" and verdict2.lower() == "correcto":
            if len(self.game_state_det1.qa_history) <= len(self.game_state_det2.qa_history):
                winner = self.game_state_det1.detective_model
                winner_rationale = f"Ambos Detectives resolvieron correctamente. Detective 1 ({self.game_state_det1.detective_model}) ganó por resolver en menos preguntas ({len(self.game_state_det1.qa_history)} vs {len(self.game_state_det2.qa_history)})."
            else:
                winner = self.game_state_det2.detective_model
                winner_rationale = f"Ambos Detectives resolvieron correctamente. Detective 2 ({self.game_state_det2.detective_model}) ganó por resolver en menos preguntas ({len(self.game_state_det2.qa_history)} vs {len(self.game_state_det1.qa_history)})."
        # Case 2: Only Detective 1 correct
        elif verdict1.lower() == "correcto":
            winner = self.game_state_det1.detective_model
            winner_rationale = f"Detective 1 ({self.game_state_det1.detective_model}) resolvió correctamente. Detective 2 ({self.game_state_det2.detective_model}) no lo hizo."
        # Case 3: Only Detective 2 correct
        elif verdict2.lower() == "correcto":
            winner = self.game_state_det2.detective_model
            winner_rationale = f"Detective 2 ({self.game_state_det2.detective_model}) resolvió correctamente. Detective 1 ({self.game_state_det1.detective_model}) no lo hizo."
        # Case 4: Neither correct, compare closeness (simplified)
        else:
            # For simplicity, if neither is correct, we'll just say no winner, or could implement a more complex closeness metric
            winner = "Ninguno"
            winner_rationale = "Ningún Detective logró resolver la historia correctamente."
            # A more advanced comparison could involve analyzing the "analysis" from the narrator.

        summary_messages.append(f"<h2>Resultados Finales del Modo Pelea</h2>")
        summary_messages.append(f"<p><strong>Historia Original:</strong><br>{self.story.mystery_situation}<br>Solución: {self.story.hidden_solution}</p>")
        
        summary_messages.append(f"<h3>Detective 1: {self.game_state_det1.detective_model}</h3>")
        summary_messages.append(f"<p><strong>Versión:</strong> {self.game_state_det1.detective_model}</p>") # Using model name as version
        summary_messages.append(f"<p><strong>Preguntas realizadas:</strong> {len(self.game_state_det1.qa_history)}</p>")
        summary_messages.append(f"<p><strong>Intento de Solución:</strong> {self.game_state_det1.detective_solution_attempt if self.game_state_det1.detective_solution_attempt else 'No proporcionó solución.'}</p>")
        summary_messages.append(f"<p><strong>Veredicto:</strong> {verdict1}</p>")
        summary_messages.append(f"<p><strong>Análisis:</strong> {analysis1}</p>")

        summary_messages.append(f"<h3>Detective 2: {self.game_state_det2.detective_model}</h3>")
        summary_messages.append(f"<p><strong>Versión:</strong> {self.game_state_det2.detective_model}</p>") # Using model name as version
        summary_messages.append(f"<p><strong>Preguntas realizadas:</strong> {len(self.game_state_det2.qa_history)}</p>")
        summary_messages.append(f"<p><strong>Intento de Solución:</strong> {self.game_state_det2.detective_solution_attempt if self.game_state_det2.detective_solution_attempt else 'No proporcionó solución.'}</p>")
        summary_messages.append(f"<p><strong>Veredicto:</strong> {verdict2}</p>")
        summary_messages.append(f"<p><strong>Análisis:</strong> {analysis2}</p>")
        
        summary_messages.append(f"<h3>GANADOR: {winner}</h3>")
        summary_messages.append(f"<p><strong>Razón:</strong> {winner_rationale}</p>")

        yield json.dumps({"type": "summary", "content": "".join(summary_messages)})

    async def run(self, narrator_model: str, detective_model_1: str, detective_model_2: str) -> AsyncGenerator[str, None]:
        """
        Runs the complete Black Stories AI fight mode.
        """
        try:
            async for msg in self._initialize_fight(narrator_model, detective_model_1, detective_model_2):
                yield msg
            async for msg in self._run_fight_loop():
                yield msg
            async for msg in self._finalize_fight():
                yield msg
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"El modo pelea ha terminado debido a un error crítico: {e}. Asegúrate de que tus claves de API y la URL de Ollama estén configuradas correctamente."})
