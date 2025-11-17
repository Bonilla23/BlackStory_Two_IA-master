from src.models.game_state import GameState
from src.models.story import Story
from src.services.api_client import APIClient
from src.services.story_generator import StoryGenerator
from src.services.narrator import Narrator
from src.services.detective import Detective
from src.utils.display import display_initial_screen, display_qa_pair, display_final_screen, display_error_and_retry
from typing import Dict, Any

class GameEngine:
    """
    Orchestrates the Black Stories AI game, managing the flow between different components.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = APIClient(config)
        self.game_state: GameState | None = None
        self.narrator_ai: Narrator | None = None # Add narrator_ai as a member variable

    def _initialize_game(self) -> None:
        """
        Initializes the game by generating a story and setting up AI roles.
        """
        narrator_model = self.config["narrator_model"]
        detective_model = self.config["detective_model"]
        difficulty = self.config["difficulty"]

        print("Generando una nueva historia de Black Stories...")
        story_generator = StoryGenerator(self.api_client, narrator_model)
        
        story: Story
        while True:
            try:
                story = story_generator.generate_story(difficulty)
                break
            except Exception as e:
                print(f"Error crítico al generar la historia: {e}")
                if not display_error_and_retry("Error al generar la historia. ¿Desea reintentar?"):
                    raise

        self.game_state = GameState(
            narrator_model=narrator_model,
            detective_model=detective_model,
            difficulty=difficulty,
            mystery_situation=story.mystery_situation,
            hidden_solution=story.hidden_solution,
        )

        display_initial_screen(
            title="Black Stories AI",
            narrator_model=narrator_model,
            detective_model=detective_model,
            difficulty=difficulty,
            mystery_situation=story.mystery_situation,
        )

    def _run_game_loop(self) -> None:
        """
        Runs the main game loop where the detective asks questions and the narrator responds.
        """
        if not self.game_state:
            raise RuntimeError("Game not initialized.")

        self.narrator_ai = Narrator( # Assign to self.narrator_ai
            self.api_client,
            self.game_state.narrator_model,
            Story(self.game_state.mystery_situation, self.game_state.hidden_solution),
            self.game_state.difficulty,
        )
        detective_ai = Detective(
            self.api_client, self.game_state.detective_model, self.game_state.mystery_situation
        )

        detective_ready_to_solve = False
        
        max_questions = self.config["question_limits"].get(self.game_state.difficulty, 10) # Default to 10 if difficulty not found

        while not self.game_state.detective_solved:
            current_questions = len(self.game_state.qa_history)

            if current_questions >= max_questions and not detective_ready_to_solve:
                print(f"\n¡Se ha alcanzado el límite de {max_questions} preguntas!")
                print("El Detective tiene UNA ÚLTIMA OPORTUNIDAD para dar su solución final.")
                print("Presiona ENTER para que el Detective dé su solución final...")
                input()
                detective_ready_to_solve = True
                # Continue to the next iteration to allow the detective to provide the solution
                # The next block will handle the solution attempt
            
            if detective_ready_to_solve:
                self.game_state.detective_solution_attempt = detective_ai.provide_final_solution(self.game_state.qa_history)
                self.game_state.detective_solved = True
                break # Exit loop after solution attempt
            
            # Only ask a question if not already in "ready to solve" state due to question limit
            if not detective_ready_to_solve:
                detective_response = detective_ai.ask_question_or_solve(self.game_state.qa_history)

                if detective_ai.is_ready_to_solve(detective_response): # No need for 'and not detective_ready_to_solve' here
                    detective_ready_to_solve = True
                    print("\nDetective: ¡Estoy listo para resolver!")
                    print("Presiona ENTER para que el Detective dé su solución final...")
                    input()
                    continue # Skip to the next iteration to get the actual solution

                narrator_answer = self.narrator_ai.answer_question(detective_response, self.game_state.qa_history)
                self.game_state.qa_history.append((detective_response, narrator_answer))
                display_qa_pair(detective_response, narrator_answer)
        
        # If the game ended without a solution attempt (e.g., user quit or critical error)
        # This block is mostly for robustness, as the loop should now handle solution attempts
        if not self.game_state.detective_solved and not self.game_state.detective_solution_attempt:
            self.game_state.detective_solved = True # Ensure game ends

    def _finalize_game(self) -> None:
        """
        Finalizes the game by validating the detective's solution and displaying the results.
        """
        if not self.game_state or not self.narrator_ai: # Check self.narrator_ai as well
            raise RuntimeError("Game not initialized or narrator_ai not set.")

        result = "DERROTA"
        verdict = "Incorrecto"
        analysis = "El Detective no proporcionó una solución."

        if self.game_state.detective_solution_attempt:
            verdict, analysis = self.narrator_ai.validate_solution(self.game_state.detective_solution_attempt) # Corrected to use self.narrator_ai
            if verdict.lower() == "correcto":
                result = "VICTORIA"
            else:
                result = "DERROTA"
        
        self.narrator_ai.save_full_conversation() # Save the full conversation here

        display_final_screen(
            result=result,
            original_story=f"Situación misteriosa: {self.game_state.mystery_situation}\nSolución oculta: {self.game_state.hidden_solution}",
            detective_solution=self.game_state.detective_solution_attempt if self.game_state.detective_solution_attempt else "No se proporcionó una solución final.",
            verdict=verdict,
            analysis=analysis,
        )

    def run(self) -> None:
        """
        Runs the complete Black Stories AI game.
        """
        try:
            self._initialize_game()
            self._run_game_loop()
            self._finalize_game()
        except Exception as e:
            print(f"\nEl juego ha terminado debido a un error crítico: {e}")
            print("Asegúrate de que tus claves de API y la URL de Ollama estén configuradas correctamente.")
