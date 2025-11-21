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

app = Flask(__name__, template_folder='templates', static_folder='static')
game_engine_instance = None # For single player game
fight_engine_instance = None # For fight mode

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    global game_engine_instance
    data = request.json
    difficulty = data.get('difficulty')
    narrator_model = data.get('narrator_model')
    detective_model = data.get('detective_model')

    def generate():
        global game_engine_instance
        try:
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            game_engine_instance = GameEngine(config)
            for line in game_engine_instance.run(difficulty, narrator_model, detective_model):
                print(f"DEBUG: Yielding line: {line}") # Added for debugging
                yield line + '\n'
        except Exception as e:
            print(f"ERROR: An exception occurred in generate: {e}") # Added for debugging
            yield json.dumps({"type": "error", "content": f"An error occurred: {e}"})

    return Response(generate(), mimetype='application/x-ndjson')

@app.route('/start_fight', methods=['POST'])
async def start_fight():
    global fight_engine_instance
    data = request.json
    # Use the narrator model from the main game form as the default for fight mode
    # If the main form's narrator model is not provided, default to 'gpt-4'
    narrator_model = data.get('narrator_model', 'gpt-4') 
    detective_model_1 = data.get('detective_model_1')
    detective_model_2 = data.get('detective_model_2')

    def generate_fight_stream_sync():
        global fight_engine_instance
        
        async def stream_content():
            config_loader = Config(parse_cli=False)
            config = config_loader.get_config()
            fight_engine_instance = FightEngine(config)
            try:
                async for line in fight_engine_instance.run(narrator_model, detective_model_1, detective_model_2):
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

@app.route('/save_conversation', methods=['POST'])
def save_conversation():
    global game_engine_instance
    # In fight mode, we don't save individual conversations in the same way, 
    # but the Narrator might have its own save mechanism if needed.
    # For now, this route is mainly for the single-player game.
    if game_engine_instance:
        game_engine_instance.save_conversation()
        return {"status": "success"}, 200
    return {"status": "error", "message": "Game not started"}, 400


if __name__ == '__main__':
    app.run(debug=True)
