# service/model_config.py
import os

# Simple dictionary of model configurations
MODEL_CONFIGS = {
    "ollama": {
        "name": os.getenv("OLLAMA_MODEL", "ministral-3:latest"),
        "url": os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        "api_key_env": None,
        "type": "ollama"
    },
    "deepseek": {
        "name": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "url": "https://api.deepseek.com/v1/chat/completions",
        "api_key_env": "DEEPSEEK_API_KEY",
        "type": "openai_compatible"
    },
    "openai": {
        "name": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "type": "openai_compatible"
    },
    "groq": {  # Add this
        "name": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key_env": "GROQ_API_KEY",
        "type": "openai_compatible"
    }
}

# Don't set a default here - we'll determine it dynamically
