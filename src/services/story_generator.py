import json
from typing import Dict, Any
from src.services.api_client import APIClient
from src.models.story import Story
from src.utils.display import display_error_and_retry

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
        difficulty_description = {
            "facil": "con lógica directa, menos elementos rebuscados, causas evidentes.",
            "media": "con una combinación de elementos lógicos y algunos giros inesperados.",
            "dificil": "muy rebuscada, con causas no obvias y múltiples elementos engañosos.",
        }

        return f"""
        Eres un experto creador de Black Stories. Tu tarea es generar una historia de Black Stories
        con el siguiente formato JSON:
        {{
            "situacion_misteriosa": "Una breve descripción de la situación inicial que se presenta al detective.",
            "solucion_oculta": "La explicación completa y detallada de lo que realmente sucedió."
        }}

        La historia debe ser {difficulty_description[difficulty]}.
        Asegúrate de que la "solucion_oculta" sea la verdad completa y que la "situacion_misteriosa"
        sea intrigante pero no revele la solución directamente.
        La historia debe ser concisa y clara.
        """

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

                story_data = json.loads(json_string)
                return Story(
                    mystery_situation=story_data["situacion_misteriosa"],
                    hidden_solution=story_data["solucion_oculta"]
                )
            except json.JSONDecodeError as e:
                print(f"DEBUG: Invalid JSON received from API: {json_string}. Error: {e}")
                if not display_error_and_retry(f"Error de formato JSON al generar la historia: {e}. Reintentando..."):
                    raise
            except (ConnectionError, ValueError, KeyError) as e:
                if not display_error_and_retry(f"Error al generar la historia: {e}"):
                    raise

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
        
        # Sanitize the JSON string to escape invalid control characters
        # This is a common issue with LLM outputs that might include unescaped newlines/tabs within string values
        json_string = json_string.replace('\\n', '\\\\n').replace('\\t', '\\\\t').replace('\\r', '\\\\r')
        # Also, sometimes the LLM might output actual newline characters that need to be escaped
        json_string = json_string.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')

        return json_string
