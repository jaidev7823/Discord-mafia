# service/llm_service.py
import requests
from service.model_config import MODEL_NAME, OLLAMA_URL

def ask_ollama(prompt: str) -> str:
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
            },
        )
        return res.json().get("response", "No response.")
    except Exception as e:
        return f"Error: {e}"