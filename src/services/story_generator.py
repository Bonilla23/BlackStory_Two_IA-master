import json
import re # Import the re module for regex operations
from json_repair import repair_json
from typing import Dict, Any
from src.services.api_client import APIClient
from src.models.story import Story
from src.config.prompts import get_story_generation_prompt
class StoryGenerator:
    """
    Generates Black Stories using an LLM.
    """

    def __init__(self, api_client: APIClient, narrator_model: str):
        self.api_client = api_client
        self.narrator_model = narrator_model

    def _get_story_generation_prompt(self, difficulty: str) -> str:
        """
        Returns the prompt for generating a Black Story based on difficulty.
        """
        return get_story_generation_prompt(difficulty)

    def generate_story(self, difficulty: str) -> Story:
        """
        Generates a new Black Story using the Narrator AI.
        Handles connection errors with retry mechanism.
        """
        prompt = self._get_story_generation_prompt(difficulty)
        while True:
            try:
                response_text = self.api_client.generate_text(self.narrator_model, prompt)
                
                # Attempt to find and extract JSON from the response
                json_string = self._extract_json_from_response(response_text)
                json_string = repair_json(json_string)
                story_data = json.loads(json_string)
                mystery_situation = story_data["situacion_misteriosa"]
                hidden_solution = story_data.get("solucion_oculta")
                if hidden_solution is None:
                    # Handle potential misspelling from LLM
                    hidden_solution = story_data.get("solucion_ocruta")
                    if hidden_solution is None:
                        raise KeyError("Neither 'solucion_oculta' nor 'solucion_ocruta' found in response.")

                return Story(
                    mystery_situation=mystery_situation,
                    hidden_solution=hidden_solution
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Error de formato JSON al generar la historia: {e}. Raw response: {json_string}")
            except KeyError as e:
                raise ValueError(f"Error al generar la historia: Falta la clave esperada en el JSON: {e}. Received data: {story_data}")
            except (ConnectionError, ValueError) as e:
                raise type(e)(f"Error al generar la historia: {e}")

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extracts a JSON string from the raw API response, handling markdown code blocks
        and potential surrounding text.
        """
        # Try to find a markdown JSON block
        json_start_marker = "```json"
        json_end_marker = "```"
        
        if json_start_marker in response_text:
            start_index = response_text.find(json_start_marker) + len(json_start_marker)
            end_index = response_text.rfind(json_end_marker)
            
            if start_index != -1 and end_index != -1 and end_index > start_index:
                return response_text[start_index:end_index].strip()
        
        # If no markdown block, assume the entire response is JSON or contains it
        # Attempt to find the first '{' and last '}' to isolate the JSON object
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_string = response_text[first_brace : last_brace + 1].strip()
        else:
            # If all else fails, return the original text and let json.loads handle the error
            json_string = response_text.strip()
        
        # Remove any invalid control characters that might still be present
        # This regex matches any control character (0x00-0x1F) except for tab (0x09),
        # newline (0x0A), and carriage return (0x0D), which are valid in JSON strings
        # when escaped.
        json_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', json_string)

        return json_string
