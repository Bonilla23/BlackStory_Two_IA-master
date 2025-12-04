import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from flask import Flask, render_template, request, Response
from src.utils.config import Config
import asyncio
from src.game.game_engine import GameEngine
from src.game.fight_engine import FightEngine # Import FightEngine
from src.game.council_engine import CouncilEngine # Import CouncilEngine
from src.game.inverse_engine import InverseEngine # Import InverseEngine
from src.services.hint_generator import HintGenerator # Import HintGenerator

app = Flask(__name__, template_folder='templates', static_folder='static')
active_games = {} # Dictionary to store game instances by session_id

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.json
    difficulty = data.get('difficulty')
    narrator_model = data.get('narrator_model')
    detective_model = data.get('detective_model')
    session_id = data.get('session_id')

    if not session_id:
        return Response(json.dumps({"type": "error", "content": "Session ID required"}), mimetype='application/x-ndjson')

    def generate():
        try:
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            game_engine = GameEngine(config)
            active_games[session_id] = game_engine # Store instance
            
            for line in game_engine.run(difficulty, narrator_model, detective_model):
                print(f"DEBUG: Yielding line: {line}") # Added for debugging
                yield line + '\n'
        except Exception as e:
            print(f"ERROR: An exception occurred in generate: {e}") # Added for debugging
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')

@app.route('/start_fight', methods=['POST'])
async def start_fight():
    data = request.json
    # Use the narrator model from the main game form as the default for fight mode
    # If the main form's narrator model is not provided, default to 'gpt-4'
    narrator_model = data.get('narrator_model', 'gpt-4')
    detective_model_1 = data.get('detective_model_1')
    detective_model_2 = data.get('detective_model_2')
    difficulty = data.get('difficulty') # Get difficulty from frontend
    session_id = data.get('session_id')

    if not session_id:
        return Response(json.dumps({"type": "error", "content": "Session ID required"}), mimetype='application/x-ndjson')

    def generate_fight_stream_sync():
        
        async def stream_content():
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            
            # Override default difficulty with the one from the frontend
            if difficulty:
                config["difficulty"] = difficulty
                print(f"DEBUG: Fight mode difficulty set to: {difficulty}")

            fight_engine = FightEngine(config)
            active_games[session_id] = fight_engine # Store instance

            try:
                async for line in fight_engine.run(narrator_model, detective_model_1, detective_model_2):
                    print(f"DEBUG: Yielding fight line: {line}")
                    yield line + '\n'
            except Exception as e:
                print(f"ERROR: An exception occurred in stream_content: {e}")
                yield json.dumps({"type": "error", "content": f"An error occurred in fight mode: {e}"}) + '\n'

        # This runs the entire async generator in a dedicated event loop
        # and allows it to be consumed synchronously by Flask's Response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Create an iterator from the async generator
            async_iter = stream_content().__aiter__()
            while True:
                try:
                    # Get the next item from the async generator
                    yield loop.run_until_complete(async_iter.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    return Response(generate_fight_stream_sync(), mimetype='application/x-ndjson')

@app.route('/start_council', methods=['POST'])
async def start_council():
    data = request.json
    narrator_model = data.get('narrator_model', 'gpt-4')
    visionary_model = data.get('visionary_model')
    skeptic_model = data.get('skeptic_model')
    leader_model = data.get('leader_model')
    difficulty = data.get('difficulty')
    session_id = data.get('session_id')

    if not session_id:
        return Response(json.dumps({"type": "error", "content": "Session ID required"}), mimetype='application/x-ndjson')

    def generate_council_stream_sync():
        async def stream_content():
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            
            if difficulty:
                config["difficulty"] = difficulty

            council_engine = CouncilEngine(config)
            active_games[session_id] = council_engine

            try:
                for line in council_engine.run(difficulty, narrator_model, visionary_model, skeptic_model, leader_model):
                    print(f"DEBUG: Yielding council line: {line}")
                    yield line + '\n'
            except Exception as e:
                print(f"ERROR: An exception occurred in council stream: {e}")
                yield json.dumps({"type": "error", "content": f"An error occurred in council mode: {e}"}) + '\n'

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async_iter = stream_content().__aiter__()
            while True:
                try:
                    yield loop.run_until_complete(async_iter.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    return Response(generate_council_stream_sync(), mimetype='application/x-ndjson')

@app.route('/save_conversation', methods=['POST'])
def save_conversation():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return {"status": "error", "message": "Session ID required"}, 400

    game_instance = active_games.get(session_id)

    # In fight mode, we don't save individual conversations in the same way, 
    # but the Narrator might have its own save mechanism if needed.
    # For now, this route is mainly for the single-player game.
    if game_instance:
        if hasattr(game_instance, 'save_conversation'):
             game_instance.save_conversation()
             return {"status": "success"}, 200
        else:
             return {"status": "error", "message": "Save not supported for this mode"}, 400
            
    return {"status": "error", "message": "Game not started for this session"}, 400

@app.route('/get_hint', methods=['POST'])
def get_hint():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return {"status": "error", "message": "Session ID required"}, 400

    game_instance = active_games.get(session_id)
    
    # Check if it is a single player game instance
    if not game_instance or not isinstance(game_instance, GameEngine):
        return {"status": "error", "message": "Pista solo disponible en modo Single Player"}, 400
        
    if not game_instance.game_state:
        return {"status": "error", "message": "Game state not initialized"}, 400

    # Use the narrator model for generating hints
    hint_model = game_instance.game_state.narrator_model
    
    hint_generator = HintGenerator(game_instance.api_client, hint_model)
    hint = hint_generator.generate_hint(
        game_instance.game_state.mystery_situation,
        game_instance.game_state.hidden_solution,
        game_instance.game_state.qa_history
    )
    
    return {"status": "success", "hint": hint}, 200

@app.route('/start_interactive', methods=['POST'])
def start_interactive():
    data = request.json
    difficulty = data.get('difficulty')
    narrator_model = data.get('narrator_model')
    session_id = data.get('session_id')

    if not session_id:
        return Response(json.dumps({"type": "error", "content": "Session ID required"}), mimetype='application/x-ndjson')

    def generate():
        try:
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            game_engine = GameEngine(config)
            active_games[session_id] = game_engine
            
            for line in game_engine.start_interactive_game(difficulty, narrator_model):
                print(f"DEBUG: Yielding interactive line: {line}")
                yield line + '\n'
        except Exception as e:
            print(f"ERROR: An exception occurred in start_interactive: {e}")
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')

@app.route('/ask_narrator', methods=['POST'])
def ask_narrator():
    data = request.json
    session_id = data.get('session_id')
    question = data.get('question')

    if not session_id or not question:
        return {"status": "error", "message": "Session ID and question required"}, 400

    game_instance = active_games.get(session_id)
    if not game_instance or not isinstance(game_instance, GameEngine):
        return {"status": "error", "message": "Game not found"}, 404

    try:
        answer = game_instance.ask_question(question)
        return {"status": "success", "answer": answer}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/solve_mystery', methods=['POST'])
def solve_mystery():
    data = request.json
    session_id = data.get('session_id')
    solution = data.get('solution')

    if not session_id or not solution:
        return Response(json.dumps({"type": "error", "content": "Session ID and solution required"}), mimetype='application/x-ndjson')

    game_instance = active_games.get(session_id)
    if not game_instance or not isinstance(game_instance, GameEngine):
        return Response(json.dumps({"type": "error", "content": "Game not found"}), mimetype='application/x-ndjson')

    def generate():
        try:
            for line in game_instance.submit_solution(solution):
                yield line + '\n'
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')




@app.route('/start_inverse', methods=['POST'])
def start_inverse():
    data = request.json
    difficulty = data.get('difficulty')
    detective_model = data.get('detective_model')
    session_id = data.get('session_id')

    if not session_id:
        return Response(json.dumps({"type": "error", "content": "Session ID required"}), mimetype='application/x-ndjson')

    def generate():
        try:
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            inverse_engine = InverseEngine(config)
            active_games[session_id] = inverse_engine
            
            for line in inverse_engine.start_game(difficulty, detective_model):
                print(f"DEBUG: Yielding inverse line: {line}")
                yield line + '\n'
        except Exception as e:
            print(f"ERROR: An exception occurred in start_inverse: {e}")
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')

@app.route('/inverse_answer', methods=['POST'])
def inverse_answer():
    data = request.json
    session_id = data.get('session_id')
    answer = data.get('answer')

    if not session_id or not answer:
        return Response(json.dumps({"type": "error", "content": "Session ID and answer required"}), mimetype='application/x-ndjson')

    game_instance = active_games.get(session_id)
    if not game_instance or not isinstance(game_instance, InverseEngine):
        return Response(json.dumps({"type": "error", "content": "Game not found"}), mimetype='application/x-ndjson')

    def generate():
        try:
            for line in game_instance.handle_answer(answer):
                yield line + '\n'
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')

if __name__ == '__main__':
    app.run(debug=True)
