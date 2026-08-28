import sys
import os
import requests
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import OLLAMA_ENDPOINT, OLLAMA_MODEL

class LLMOffline:
    """
    Offline LLM Client using local Ollama.
    Used for zero-latency offline processing and fallback when offline.
    """
    def __init__(self):
        self.endpoint = OLLAMA_ENDPOINT
        self.model = OLLAMA_MODEL

    def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        try:
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
                "stream": False
            }
            response = requests.post(self.endpoint, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "No response generated.")
            else:
                print(f"[LLM Offline Error] HTTP {response.status_code}")
                return "Sorry, the local offline model returned an error."
        except requests.exceptions.RequestException as e:
            print(f"[LLM Offline Request Error] {e}")
            return "Sorry, I could not connect to the local Ollama instance."
