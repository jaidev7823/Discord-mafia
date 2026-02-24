# service/llm_service.py
import requests
from service.model_config import MODEL_NAME, OLLAMA_URL

# service/llm_service.py - Modify to log prompts
def ask_ollama(prompt: str, agent_name: str = None) -> str:
    """Log prompts to file for debugging"""
    try:
        # Log the prompt being sent
        with open("prompt_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"AGENT: {agent_name}\n")
            f.write(f"PROMPT SENT:\n{prompt}\n")
            f.write(f"{'='*50}\n")
        
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,
                }
            },
        )
        
        response = res.json().get("response", "").strip()
        
        # Log the response
        with open("prompt_debug.log", "a", encoding="utf-8") as f:
            f.write(f"RESPONSE: {response}\n")
            f.write(f"{'='*50}\n\n")
        
        return response
    except Exception as e:
        return ""