import sys
import os
from groq import Groq

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import GROQ_API_KEY

class LLMOnline:
    """
    Online LLM Client using Groq API (e.g., LLaMA 3 / Mixtral).
    Used for high-speed online inference when internet is available.
    """
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama3-8b-8192"

    def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"[LLM Online Error] {e}")
            return "Sorry, I encountered an error connecting to the online model."
