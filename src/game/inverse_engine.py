import json
from typing import Dict, Any, Generator, List, Tuple

from src.models.game_state import GameState
from src.models.story import Story
from src.services.api_client import APIClient
from src.services.story_generator import StoryGenerator
from src.services.detective import Detective

class InverseEngine:
    """
    Orchestrates the Inverse Black Stories AI game.
    User = Narrator (knows the solution).
    AI = Detective (asks questions).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = APIClient(config)
        self.game_state: GameState | None = None
        self.detective_ai: Detective | None = None

    def start_game(self, difficulty: str, detective_model: str) -> Generator[str, None, None]:
        """
        Initializes the inverse game.
        """
        yield "Generando una nueva historia para que TÚ seas el Narrador..."
        
        # We still use StoryGenerator to create the scenario for the user
        story_generator = StoryGenerator(self.api_client, detective_model) # Model doesn't matter much here for generation
        
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
            narrator_model="User",
            detective_model=detective_model,
            difficulty=difficulty,
            mystery_situation=story.mystery_situation,
            hidden_solution=story.hidden_solution,
        )

        self.detective_ai = Detective(
            self.api_client,
            self.game_state.detective_model,
            self.game_state.mystery_situation
        )

        yield "============================================================"
        yield "                  BLACK STORIES AI (MODO INVERSO)"
        yield "============================================================"
        yield "Narrador: TÚ"
        yield f"Detective: {detective_model}"
        yield f"Dificultad: {difficulty}"
        yield "------------------------------------------------------------"
        yield f"Misterio: {story.mystery_situation}"
        yield "------------------------------------------------------------"
        yield f"Solución (SOLO PARA TUS OJOS): {story.hidden_solution}"
        yield "============================================================"
        
        # Send initial game state with solution to frontend
        yield json.dumps({
            "type": "inverse_init",
            "mystery": story.mystery_situation,
            "solution": story.hidden_solution
        })

        # Detective asks the first question immediately? 
        # Usually in Black Stories the narrator reads the mystery and asks "What happened?"
        # The detective then starts asking.
        
        yield from self._detective_turn()

    def _detective_turn(self) -> Generator[str, None, None]:
        """
        Executes the AI Detective's turn to ask a question or solve.
        """
        if not self.game_state or not self.detective_ai:
            raise RuntimeError("Game not initialized.")

        yield json.dumps({"type": "status", "content": "El Detective está pensando..."})

        response = self.detective_ai.ask_question_or_solve(self.game_state.qa_history)
        
        if self.detective_ai.is_ready_to_solve(response):
             yield json.dumps({"type": "status", "content": "El Detective está formulando su solución final..."})
             # Get the actual solution
             solution = self.detective_ai.provide_final_solution(self.game_state.qa_history)
             
             self.current_question = solution # Store as current "question" for history
             self.is_solution_attempt = True # Flag to know this is a solution
             
             yield f"Detective (PROPONE SOLUCIÓN): {solution}"
             
             yield json.dumps({
                "type": "inverse_solution",
                "content": solution
             })
        else:
             self.current_question = response
             self.is_solution_attempt = False
             
             yield f"Detective: {response}"
             
             yield json.dumps({
                "type": "inverse_question",
                "content": response
             })

    def handle_answer(self, answer: str) -> Generator[str, None, None]:
        """
        Called when user clicks Yes/No/etc.
        """
        if not hasattr(self, 'current_question'):
             raise RuntimeError("No active question.")
        
        yield f"Narrador (Tú): {answer}"
        
        self.game_state.qa_history.append((self.current_question, answer))
        
        # Check if it was a solution attempt
        if getattr(self, 'is_solution_attempt', False):
            if answer.lower() in ["sí", "si", "correcto", "exacto", "¡correcto!"]:
                yield "¡El Detective ha resuelto el caso!"
                yield json.dumps({"type": "game_over", "result": "AI_WINS"})
                # End game
            else:
                yield "El Detective falló en su solución. El juego continúa."
                yield from self._detective_turn()
        else:
            # Normal question flow
            # If user says "Correcto" to a normal question, it might be weird, but let's treat it as "Yes"
            yield from self._detective_turn()

