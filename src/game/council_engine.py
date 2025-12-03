import json
from typing import Dict, Any, Generator, Tuple, List

from src.models.game_state import GameState
from src.models.story import Story
from src.services.api_client import APIClient
from src.services.story_generator import StoryGenerator
from src.services.narrator import Narrator
from src.config.prompts import get_visionary_prompt, get_skeptic_prompt, get_leader_prompt, get_leader_final_guess_prompt

class CouncilEngine:
    """
    Orchestrates the 'Council of Detectives' game mode.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = APIClient(config)
        self.game_state: GameState | None = None
        self.narrator_ai: Narrator | None = None

    def _initialize_game(self, difficulty: str, narrator_model: str, visionary_model: str, skeptic_model: str, leader_model: str) -> Generator[str, None, None]:
        yield "Convocando al Consejo de Detectives..."
        story_generator = StoryGenerator(self.api_client, narrator_model)
        
        story: Story
        try:
            story = story_generator.generate_story(difficulty)
        except Exception as e:
            yield f"Error al generar la historia: {e}"
            raise

        self.game_state = GameState(
            narrator_model=narrator_model,
            detective_model=leader_model, # Leader is the primary 'detective' for state
            difficulty=difficulty,
            mystery_situation=story.mystery_situation,
            hidden_solution=story.hidden_solution,
        )

        yield "============================================================"
        yield "                  CONSEJO DE DETECTIVES"
        yield "============================================================"
        yield f"Narrador: {narrator_model}"
        yield f"Visionario: {visionary_model}"
        yield f"Escéptico: {skeptic_model}"
        yield f"Líder: {leader_model}"
        yield "------------------------------------------------------------"
        yield f"Misterio: {story.mystery_situation}"
        yield "============================================================"

    def _run_council_loop(self, visionary_model: str, skeptic_model: str, leader_model: str) -> Generator[str, None, None]:
        if not self.game_state:
            raise RuntimeError("Game not initialized.")

        self.narrator_ai = Narrator(
            self.api_client,
            self.game_state.narrator_model,
            Story(self.game_state.mystery_situation, self.game_state.hidden_solution),
            self.game_state.difficulty,
        )

        max_questions = self.config["question_limits"].get(self.game_state.difficulty, 10)

        while not self.game_state.detective_solved:
            current_questions = len(self.game_state.qa_history)
            is_final_turn = False

            if current_questions >= max_questions:
                yield json.dumps({"type": "system", "content": f"⚠️ ¡Límite de {max_questions} preguntas alcanzado! El Consejo debe arriesgar una solución final."})
                is_final_turn = True
            
            # 1. Visionary Phase
            yield json.dumps({"type": "system", "content": "🤔 El Visionario está pensando..."})
            visionary_prompt = get_visionary_prompt(self.game_state.mystery_situation, self.game_state.qa_history)
            visionary_thought = self.api_client.generate_text(visionary_model, visionary_prompt).strip()
            yield json.dumps({"type": "council_visionary", "content": visionary_thought})

            # 2. Skeptic Phase
            yield json.dumps({"type": "system", "content": "🤨 El Escéptico está analizando..."})
            skeptic_prompt = get_skeptic_prompt(self.game_state.mystery_situation, self.game_state.qa_history, visionary_thought)
            skeptic_thought = self.api_client.generate_text(skeptic_model, skeptic_prompt).strip()
            yield json.dumps({"type": "council_skeptic", "content": skeptic_thought})

            # 3. Leader Phase
            yield json.dumps({"type": "system", "content": "🫡 El Líder está decidiendo..."})
            
            if is_final_turn:
                leader_prompt = get_leader_final_guess_prompt(self.game_state.mystery_situation, self.game_state.qa_history, visionary_thought, skeptic_thought)
            else:
                leader_prompt = get_leader_prompt(self.game_state.mystery_situation, self.game_state.qa_history, visionary_thought, skeptic_thought)
            
            leader_action = self.api_client.generate_text(leader_model, leader_prompt).strip()

            # Check if Leader wants to solve OR if it's forced
            if "SOLUCIÓN:" in leader_action.upper() or is_final_turn:
                # If forced and missing prefix, assume the whole text is the solution
                if "SOLUCIÓN:" in leader_action.upper():
                    solution_text = leader_action.split(":", 1)[1].strip()
                else:
                    solution_text = leader_action

                self.game_state.detective_solution_attempt = solution_text
                self.game_state.detective_solved = True
                yield json.dumps({"type": "council_leader", "content": f"¡Tengo la solución! {solution_text}"})
                break
            else:
                question = leader_action
                yield json.dumps({"type": "council_leader", "content": question})

                # 4. Narrator Phase
                narrator_answer = self.narrator_ai.answer_question(question, self.game_state.qa_history)
                self.game_state.qa_history.append((question, narrator_answer))
                yield json.dumps({"type": "narrator", "content": narrator_answer})

    def _finalize_game(self) -> Generator[str, None, None]:
        if not self.game_state or not self.narrator_ai:
            raise RuntimeError("Game not initialized.")

        result = "DERROTA"
        verdict = "Incorrecto"
        analysis = "El Consejo no llegó a una conclusión."

        if self.game_state.detective_solution_attempt:
            verdict, analysis = self.narrator_ai.validate_solution(self.game_state.detective_solution_attempt)
            if verdict.lower() == "correcto":
                result = "VICTORIA"
            else:
                result = "DERROTA"
        
        yield json.dumps({"type": "summary", "content": f"""
        <h3>RESULTADO: {result}</h3>
        <p><strong>Solución Real:</strong> {self.game_state.hidden_solution}</p>
        <p><strong>Solución del Consejo:</strong> {self.game_state.detective_solution_attempt}</p>
        <p><strong>Veredicto:</strong> {verdict}</p>
        <p><strong>Análisis:</strong> {analysis}</p>
        """})

    def run(self, difficulty: str, narrator_model: str, visionary_model: str, skeptic_model: str, leader_model: str) -> Generator[str, None, None]:
        try:
            yield from self._initialize_game(difficulty, narrator_model, visionary_model, skeptic_model, leader_model)
            yield from self._run_council_loop(visionary_model, skeptic_model, leader_model)
            yield from self._finalize_game()
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"Error crítico en el Consejo: {e}"})
