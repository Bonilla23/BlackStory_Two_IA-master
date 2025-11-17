import json
import http.client
from typing import Dict, Any, Tuple

class APIClient:
    """
    Generic API client for interacting with LLM providers like Gemini and Ollama.
    Handles connection errors and retries.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def _make_request(
        self,
        host: str,
        port: int,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: str | None = None,
        use_https: bool = True
    ) -> Tuple[int, str]:
        """
        Makes an HTTP/HTTPS request to the specified host and returns the status and response.
        """
        conn = None
        try:
            if use_https:
                conn = http.client.HTTPSConnection(host, port)
            else:
                conn = http.client.HTTPConnection(host, port)

            conn.request(method, path, body, headers)
            response = conn.getresponse()
            return response.status, response.read().decode('utf-8')
        except Exception as e:
            raise ConnectionError(f"Error de conexión con {host}: {e}")
        finally:
            if conn:
                conn.close()

    def _call_gemini_api(self, model: str, prompt: str) -> str:
        """
        Calls the Gemini API to generate content.
        """
        api_key = self.config.get("gemini_api_key")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada para Gemini.")

        host = "generativelanguage.googleapis.com"
        path = f"/v1beta/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]})

        status, response_text = self._make_request(host, 443, path, "POST", headers, body, use_https=True)

        if status == 200:
            response_data = json.loads(response_text)
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise Exception(f"Error en la API de Gemini (Status: {status}): {response_text}")

    def _call_ollama_api(self, model: str, prompt: str) -> str:
        """
        Calls the Ollama API to generate content.
        """
        ollama_host = self.config.get("ollama_host")
        if not ollama_host:
            raise ValueError("OLLAMA_HOST no configurada para Ollama.")

        # Parse host and port from ollama_host
        # Assuming ollama_host is like http://localhost:11434
        if "://" in ollama_host:
            protocol, rest = ollama_host.split("://", 1)
            host_port = rest.split("/", 1)[0]
        else:
            host_port = ollama_host.split("/", 1)[0]
            protocol = "http" # Default to http if no protocol specified

        host, port_str = (host_port.split(":") + ["80"])[:2] # Default port 80 if not specified
        port = int(port_str)
        use_https = (protocol == "https")

        path = "/api/generate"
        headers = {"Content-Type": "application/json"}
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False
        })

        status, response_text = self._make_request(host, port, path, "POST", headers, body, use_https=use_https)

        if status == 200:
            response_data = json.loads(response_text)
            return response_data["response"]
        else:
            raise Exception(f"Error en la API de Ollama (Status: {status}): {response_text}")

    def generate_text(self, provider_model: str, prompt: str) -> str:
        """
        Generates text using the specified LLM provider and model.
        provider_model format: "provider:model_name" (e.g., "gemini:gemini-2.0-flash")
        """
        provider, model = provider_model.split(":", 1)

        if provider.lower() == "gemini":
            return self._call_gemini_api(model, prompt)
        elif provider.lower() == "ollama":
            return self._call_ollama_api(model, prompt)
        else:
            raise ValueError(f"Proveedor de LLM no soportado: {provider}")
