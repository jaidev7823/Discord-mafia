# service/llm_service.py - SIMPLIFIED
import requests
import json
import re
import os
from service.model_config import MODEL_CONFIGS, DEFAULT_PROVIDER

def ask_llm(prompt: str, agent_name: str = None, provider: str = None) -> dict:
    """
    Send prompt to LLM and return parsed response.
    
    Args:
        prompt: The prompt to send
        agent_name: For logging
        provider: 'ollama', 'deepseek', 'openai', 'groq', 'anthropic'
    
    Returns:
        {"thought": str, "message": str, "raw": str}
    """
    provider = provider or DEFAULT_PROVIDER
    config = MODEL_CONFIGS.get(provider)
    
    if not config:
        return {"thought": f"Unknown provider: {provider}", "message": "", "raw": ""}
    
    # Log the prompt
    with open("prompt_debug.log", "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\nAGENT: {agent_name}\nPROVIDER: {provider}\nPROMPT:\n{prompt}\n")
    
    try:
        # Call the appropriate API based on type
        if config["type"] == "ollama":
            response_text = _call_ollama(prompt, config)
        elif config["type"] == "openai_compatible":
            response_text = _call_openai_compatible(prompt, config)
        elif config["type"] == "anthropic":
            response_text = _call_anthropic(prompt, config)
        else:
            response_text = ""
        
        # Parse JSON response
        return _parse_response(response_text)
        
    except Exception as e:
        with open("prompt_debug.log", "a") as f:
            f.write(f"ERROR: {e}\n")
        return {"thought": f"Error: {str(e)}", "message": "", "raw": ""}

def _call_ollama(prompt: str, config: dict) -> str:
    """Call Ollama API"""
    res = requests.post(config["url"], json={
        "model": config["name"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2000}
    })
    data = res.json()
    return data.get("response", "")

def _call_openai_compatible(prompt: str, config: dict) -> str:
    """Call any OpenAI-compatible API (DeepSeek, OpenAI, Groq)"""
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(f"Missing {config['api_key_env']}")
    
    res = requests.post(
        config["url"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "model": config["name"],
            "messages": [
                {"role": "system", "content": "Respond in JSON format with 'thought' and 'speak' fields."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
    )
    
    data = res.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")

def _call_anthropic(prompt: str, config: dict) -> str:
    """Call Anthropic Claude API"""
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(f"Missing {config['api_key_env']}")
    
    res = requests.post(
        config["url"],
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": config["name"],
            "messages": [{"role": "user", "content": prompt}],
            "system": "Respond in JSON format with 'thought' and 'speak' fields.",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    )
    
    data = res.json()
    return data.get("content", [{}])[0].get("text", "")

def _parse_response(text: str) -> dict:
    """Extract thought and speak from JSON response"""
    if not text:
        return {"thought": "No response", "message": "", "raw": ""}
    
    # Clean markdown code blocks
    text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE)
    
    # Try to find JSON
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        return {"thought": "No JSON found", "message": text[:200], "raw": text}
    
    # Try to parse JSON
    try:
        data = json.loads(json_match.group())
        return {
            "thought": data.get("thought", "").strip(),
            "message": data.get("speak", "").strip(),
            "raw": text
        }
    except:
        # Fallback: try to extract fields with regex
        thought = re.search(r'"thought"\s*:\s*"([^"]+)"', text)
        speak = re.search(r'"speak"\s*:\s*"([^"]+)"', text)
        return {
            "thought": thought.group(1) if thought else "Parse error",
            "message": speak.group(1) if speak else text[:200],
            "raw": text
        }

# Simple helper functions
def ask_ollama(prompt: str, agent: str = None) -> dict:
    return ask_llm(prompt, agent, "ollama")

def ask_deepseek(prompt: str, agent: str = None) -> dict:
    return ask_llm(prompt, agent, "deepseek")

def get_message(prompt: str, agent: str = None, provider: str = None) -> str:
    """Quick helper to just get the message text"""
    return ask_llm(prompt, agent, provider).get("message", "")

def truncate(text: str, max_len: int = 150) -> str:
    """Simple truncation"""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."