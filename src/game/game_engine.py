import json
from typing import Dict, Any, Generator

from src.models.game_state import GameState
from src.models.story import Story
from src.services.api_client import APIClient
from src.services.story_generator import StoryGenerator
from src.services.narrator import Narrator
from src.services.detective import Detective

class GameEngine:
    """
    Orchestrates the Black Stories AI game, managing the flow between different components.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = APIClient(config)
        self.game_state: GameState | None = None
        self.narrator_ai: Narrator | None = None

    def _initialize_game(self, difficulty: str, narrator_model: str, detective_model: str) -> Generator[str, None, None]:
        """
        Initializes the game by generating a story and setting up AI roles.
        """
        yield "Generando una nueva historia de Black Stories..."
        story_generator = StoryGenerator(self.api_client, narrator_model)
        
        story: Story
        retries = 3
        for attempt in range(retries):
            try:
                story = story_generator.generate_story(difficulty)
                break
            except Exception as e:
                yield f"Error al generar la historia (intento {attempt + 1}/{retries}): {e}"
                if attempt + 1 == retries:
                    raise
        
        self.game_state = GameState(
            narrator_model=narrator_model,
            detective_model=detective_model,
            difficulty=difficulty,
            mystery_situation=story.mystery_situation,
            hidden_solution=story.hidden_solution,
        )

        yield "============================================================"
        yield "                  BLACK STORIES AI"
        yield "============================================================"
        yield f"Narrador: {narrator_model}"
        yield f"Detective: {detective_model}"
        yield f"Dificultad: {difficulty}"
        yield "------------------------------------------------------------"
        yield f"Misterio: {story.mystery_situation}"
        yield "============================================================"

    def _run_game_loop(self) -> Generator[str, None, None]:
        """
        Runs the main game loop where the detective asks questions and the narrator responds.
        """
        if not self.game_state:
            raise RuntimeError("Game not initialized.")

        self.narrator_ai = Narrator(
            self.api_client,
            self.game_state.narrator_model,
            Story(self.game_state.mystery_situation, self.game_state.hidden_solution),
            self.game_state.difficulty,
        )
        detective_ai = Detective(
            self.api_client, self.game_state.detective_model, self.game_state.mystery_situation
        )

        detective_ready_to_solve = False
        max_questions = self.config["question_limits"].get(self.game_state.difficulty, 10)

        while not self.game_state.detective_solved:
            current_questions = len(self.game_state.qa_history)

            if current_questions >= max_questions and not detective_ready_to_solve:
                yield f"¡Se ha alcanzado el límite de {max_questions} preguntas!"
                yield "El Detective tiene UNA ÚLTIMA OPORTUNIDAD para dar su solución final."
                detective_ready_to_solve = True
            
            if detective_ready_to_solve:
                self.game_state.detective_solution_attempt = detective_ai.provide_final_solution(self.game_state.qa_history)
                self.game_state.detective_solved = True
                break
            
            if not detective_ready_to_solve:
                detective_response = detective_ai.ask_question_or_solve(self.game_state.qa_history)

                if detective_ai.is_ready_to_solve(detective_response):
                    detective_ready_to_solve = True
                    yield "Detective: ¡Estoy listo para resolver!"
                    continue

                narrator_answer = self.narrator_ai.answer_question(detective_response, self.game_state.qa_history)
                self.game_state.qa_history.append((detective_response, narrator_answer))
                
                yield f"Detective: {detective_response}"
                yield f"Narrador: {narrator_answer}"

        if not self.game_state.detective_solved and not self.game_state.detective_solution_attempt:
            self.game_state.detective_solved = True

    def _finalize_game(self) -> Generator[str, None, None]:
        """
        Finalizes the game by validating the detective's solution and displaying the results.
        """
        if not self.game_state or not self.narrator_ai:
            raise RuntimeError("Game not initialized or narrator_ai not set.")

        result = "DERROTA"
        verdict = "Incorrecto"
        analysis = "El Detective no proporcionó una solución."

        if self.game_state.detective_solution_attempt:
            verdict, analysis = self.narrator_ai.validate_solution(self.game_state.detective_solution_attempt)
            if verdict.lower() == "correcto":
                result = "VICTORIA"
            else:
                result = "DERROTA"
        
        # Construct HTML Summary
        summary_html = f"""
        <div class="game-result {result.lower()}">
            <h2>RESULTADO: {result}</h2>
        </div>
        
        <div class="summary-section">
            <h3>📜 Historia Original</h3>
            <p><strong>Situación:</strong> {self.game_state.mystery_situation}</p>
        </div>

        <div class="summary-section hidden-solution">
            <h3>🕵️ Solución Oculta</h3>
            <div class="solution-text">{self.game_state.hidden_solution}</div>
        </div>

        <div class="summary-section">
            <h3>📝 Solución del Detective</h3>
            <p>{self.game_state.detective_solution_attempt if self.game_state.detective_solution_attempt else "No se proporcionó una solución final."}</p>
        </div>

        <div class="summary-section verdict">
            <h3>⚖️ Veredicto del Narrador</h3>
            <p><strong>Veredicto:</strong> {verdict}</p>
            <p><strong>Análisis:</strong> {analysis}</p>
        </div>
        """

        # Yield as a single JSON message
        yield json.dumps({"type": "summary", "content": summary_html})
        yield "save_conversation"

    def run(self, difficulty: str, narrator_model: str, detective_model: str) -> Generator[str, None, None]:
        """
        Runs the complete Black Stories AI game.
        """
        try:
            yield from self._initialize_game(difficulty, narrator_model, detective_model)
            yield from self._run_game_loop()
            yield from self._finalize_game()
        except Exception as e:
            yield f"El juego ha terminado debido a un error crítico: {e}"
            yield "Asegúrate de que tus claves de API y la URL de Ollama estén configuradas correctamente."
    
    def save_conversation(self):
        if self.narrator_ai:
            self.narrator_ai.save_full_conversation()
