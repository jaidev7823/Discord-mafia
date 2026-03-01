# service/llm_service.py
import requests
import json
import re
import os
from service.model_config import MODEL_CONFIGS

PROVIDER_PRIORITY = ("gemini", "groq", "ollama")

def _is_valid_api_key(api_key_env: str) -> bool:
    """Check if API key exists and looks valid (not a placeholder)"""
    if not api_key_env:
        return False
    
    key = os.getenv(api_key_env, "")
    if not key:
        return False
    
    placeholders = ["your_", "sk-xxx", "demo", "placeholder", "xxxx", "gsk_xxx", "AIzaSyXXX"]
    key_lower = key.lower()
    if any(p in key_lower for p in placeholders):
        return False
    
    # Groq keys start with gsk_
    if api_key_env == "GROQ_API_KEY":
        return key.startswith("gsk_") and len(key) > 20
    
    # DeepSeek keys start with sk-
    if api_key_env == "DEEPSEEK_API_KEY":
        return key.startswith("sk-") and len(key) > 10
    
    return True

def get_best_available_provider() -> str:
    """
    Returns the best available provider:
    - Gemini first
    - Groq second
    - Ollama as fallback
    """
    for provider in PROVIDER_PRIORITY:
        if _provider_is_available(provider):
            return provider
    return None

def _provider_is_available(provider: str) -> bool:
    """Check whether provider can be used right now."""
    config = MODEL_CONFIGS.get(provider)
    if not config:
        return False

    if config["type"] == "ollama":
        try:
            requests.get("http://localhost:11434/api/tags", timeout=2)
            return True
        except Exception:
            return False

    api_key_env = config.get("api_key_env")
    return _is_valid_api_key(api_key_env)

def _provider_chain(start_provider: str = None) -> list:
    """
    Build ordered fallback chain:
    gemini -> groq -> ollama
    """
    if start_provider:
        if start_provider in PROVIDER_PRIORITY:
            idx = PROVIDER_PRIORITY.index(start_provider)
            return list(PROVIDER_PRIORITY[idx:])
        return [start_provider]
    return list(PROVIDER_PRIORITY)

def _critical_llm_error(prompt: str, agent_name: str = None, details: str = ""):
    message = (
        "CRITICAL: All LLM providers failed in order "
        "(gemini -> groq -> ollama)."
    )
    if details:
        message = f"{message} {details}"
    _log_message(agent_name, "fallback_chain", prompt, error=message)
    raise RuntimeError(message)

def _log_message(agent_name: str, provider: str, prompt: str, response_text: str = None, error: str = None):
    """Helper function to log messages"""
    with open("tests/prompt_debug.log", "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"TIMESTAMP: {__import__('datetime').datetime.now()}\n")
        f.write(f"AGENT: {agent_name}\n")
        f.write(f"PROVIDER: {provider}\n")
        f.write(f"PROMPT:\n{prompt}\n")
        if response_text:
            f.write(f"RESPONSE:\n{response_text}\n")
        if error:
            f.write(f"ERROR: {error}\n")
        f.write(f"{'='*50}\n")

def ask_llm(prompt: str, agent_name: str = None, provider: str = None) -> dict:
    """
    Send prompt to LLM with strict fallback:
    gemini -> groq -> ollama.
    """
    fallback_chain = _provider_chain(provider)
    attempted = []

    for candidate in fallback_chain:
        config = MODEL_CONFIGS.get(candidate)
        if not config:
            attempted.append(f"{candidate}:missing_config")
            continue

        if not _provider_is_available(candidate):
            attempted.append(f"{candidate}:not_available")
            continue

        print(f"[Using provider: {candidate}]")

        try:
            if config["type"] == "ollama":
                response_text = _call_ollama(prompt, config)
            elif config["type"] == "openai_compatible":
                response_text = _call_openai_compatible(prompt, config)
            else:
                attempted.append(f"{candidate}:unsupported_type")
                continue

            _log_message(agent_name, candidate, prompt, response_text)
            return _parse_response(response_text)

        except Exception as e:
            error_msg = f"{candidate} API error: {str(e)}"
            print(f"❌ {error_msg}")
            _log_message(agent_name, candidate, prompt, error=error_msg)
            attempted.append(f"{candidate}:error")

    _critical_llm_error(prompt, agent_name, details=f"Attempts={','.join(attempted)}")

def _call_ollama(prompt: str, config: dict) -> str:
    """Call Ollama API"""
    res = requests.post(config["url"], json={
        "model": config["name"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2000}
    }, timeout=30)
    data = res.json()
    return data.get("response", "")

def _call_openai_compatible(prompt: str, config: dict) -> str:
    """Call any OpenAI-compatible API (Groq, DeepSeek, OpenAI)"""
    api_key = os.getenv(config["api_key_env"])
    
    if not api_key:
        raise ValueError(f"{config['api_key_env']} not found")
    
    print(f"🔄 Calling {config['name']} API...")
    
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
        },
        timeout=30
    )
    
    if res.status_code != 200:
        raise ValueError(f"API returned {res.status_code}: {res.text}")
    
    data = res.json()
    
    if "error" in data:
        raise ValueError(f"API error: {data['error']}")
    
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")

def _parse_response(text: str) -> dict:
    """Extract thought and speak from JSON response"""
    if not text:
        return {"thought": "No response", "message": "", "raw": ""}
    
    text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE)
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        return {"thought": "No JSON found", "message": text[:200], "raw": text}
    
    try:
        data = json.loads(json_match.group())
        return {
            "thought": data.get("thought", "").strip(),
            "message": data.get("speak", "").strip(),
            "raw": text
        }
    except Exception as e:
        thought = re.search(r'"thought"\s*:\s*"([^"]+)"', text)
        speak = re.search(r'"speak"\s*:\s*"([^"]+)"', text)
        return {
            "thought": thought.group(1) if thought else f"Parse error: {str(e)}",
            "message": speak.group(1) if speak else text[:200],
            "raw": text
        }

def truncate_thought(thought: str, max_length: int = 150) -> str:
    """Truncate thought for Discord display"""
    if not thought or len(thought) <= max_length:
        return thought
    return thought[:max_length-3] + "..."

# Helper functions
def ask_groq(prompt: str, agent: str = None) -> dict:
    """Use Groq API"""
    return ask_llm(prompt, agent, "groq")

def ask_gemini(prompt: str, agent: str = None) -> dict:
    """Use Gemini API"""
    return ask_llm(prompt, agent, "gemini")

def ask_deepseek(prompt: str, agent: str = None) -> dict:
    """Use DeepSeek API"""
    return ask_llm(prompt, agent, "deepseek")

def ask_ollama(prompt: str, agent: str = None) -> dict:
    """Use Ollama"""
    return ask_llm(prompt, agent, "ollama")

def get_message(prompt: str, agent: str = None, provider: str = None) -> str:
    """Quick helper to just get the message text"""
    return ask_llm(prompt, agent, provider).get("message", "")
