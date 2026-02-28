# service/model_config.py
import os
from typing import Dict, Any

# Simple dictionary of model configurations
MODEL_CONFIGS = {
    "ollama": {
        "name": os.getenv("OLLAMA_MODEL", "ministral-3:latest"),
        "url": os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        "api_key_env": None,  # No API key needed
        "type": "ollama"
    },
    "deepseek": {
        "name": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "url": "https://api.deepseek.com/v1/chat/completions",
        "api_key_env": "DEEPSEEK_API_KEY",
        "type": "openai_compatible"  # Uses OpenAI format
    },
    "openai": {
        "name": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "type": "openai_compatible"
    },
    "groq": {
        "name": os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key_env": "GROQ_API_KEY",
        "type": "openai_compatible"
    },
    "anthropic": {
        "name": os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        "url": "https://api.anthropic.com/v1/messages",
        "api_key_env": "ANTHROPIC_API_KEY",
        "type": "anthropic"
    }
}

# Default provider (change this or set env var)
DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")