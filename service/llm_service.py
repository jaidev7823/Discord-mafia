# service/llm_service.py - UPDATED with fixed scoping and simpler JSON parsing
import requests
import json
import re
from service.model_config import MODEL_NAME, OLLAMA_URL

def ask_ollama(prompt: str, agent_name: str = None) -> dict:
    """Send prompt to Ollama and parse JSON response with thought and message
    
    Returns:
        dict: {
            "thought": str,  # Internal reasoning (may contain newlines)
            "message": str,  # Spoken dialogue  
            "raw": str       # Full raw response for debugging
        }
    """
    try:
        # Log the prompt being sent
        with open("prompt_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"AGENT: {agent_name}\n")
            f.write(f"PROMPT SENT:\n{prompt}\n")
            f.write(f"{'='*50}\n")
        
        # Make request to Ollama
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2000,
                }
            },
        )
        
        raw_text = res.text

        # Log raw response
        with open("prompt_debug.log", "a", encoding="utf-8") as f:
            f.write(f"RAW RESPONSE:\n{raw_text}\n")
        
        # Parse the response
        try:
            data = res.json()
            response_text = (
                data.get("response")
                or data.get("message", {}).get("content")
                or data.get("thinking")
                or ""
            ).strip()
            
            # Log parsed response text
            with open("prompt_debug.log", "a", encoding="utf-8") as f:
                f.write(f"PARSED RESPONSE TEXT:\n{response_text}\n")
            
            # Try to extract JSON from the response
            # First, remove markdown code block markers if present
            cleaned_text = re.sub(r'^```json\s*', '', response_text, flags=re.MULTILINE)
            cleaned_text = re.sub(r'\s*```$', '', cleaned_text, flags=re.MULTILINE)
            
            # Find JSON pattern (anything between { and }), allowing for multiline content
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                
                # Try to parse the JSON
                try:
                    parsed = json.loads(json_str)
                except json.JSONDecodeError:
                    # If that fails, try to fix common issues
                    # Replace unescaped newlines in string values
                    def fix_json_newlines(match):
                        # Get the string content without the quotes
                        content = match.group(1)
                        # Escape newlines and other control characters
                        escaped = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                        return f'"{escaped}"'
                    
                    # Pattern to match string content (simplified but works for our case)
                    fixed_json = re.sub(r'"((?:[^"\\]|\\.)*)"', fix_json_newlines, json_str, flags=re.DOTALL)
                    
                    try:
                        parsed = json.loads(fixed_json)
                    except json.JSONDecodeError as e2:
                        with open("prompt_debug.log", "a", encoding="utf-8") as f:
                            f.write(f"ERROR: Still failing after fixes: {e2}\n")
                        
                        # Manual extraction as last resort
                        thought_match = re.search(r'"thought"\s*:\s*"([^"]+)"', json_str, re.DOTALL)
                        speak_match = re.search(r'"speak"\s*:\s*"([^"]+)"', json_str, re.DOTALL)
                        
                        thought = thought_match.group(1).replace('\n', ' ').strip() if thought_match else "No thought extracted"
                        speak = speak_match.group(1).replace('\n', ' ').strip() if speak_match else response_text[:200]
                        
                        return {
                            "thought": thought,
                            "message": speak,
                            "raw": response_text
                        }
                
                # Validate required fields
                if "thought" in parsed and "speak" in parsed:
                    result = {
                        "thought": parsed["thought"].strip(),
                        "message": parsed["speak"].strip(),
                        "raw": response_text
                    }
                    
                    # Log successful parse
                    with open("prompt_debug.log", "a", encoding="utf-8") as f:
                        thought_preview = result['thought'][:100].replace('\n', ' ') + "..." if len(result['thought']) > 100 else result['thought']
                        f.write(f"PARSED JSON - Thought: {thought_preview}\n")
                        f.write(f"PARSED JSON - Message: {result['message']}\n")
                    
                    return result
                else:
                    with open("prompt_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"ERROR: JSON missing required fields. Got: {list(parsed.keys())}\n")
                    
                    return {
                        "thought": "No structured thought provided",
                        "message": response_text[:200],
                        "raw": response_text
                    }
            else:
                # No JSON found
                with open("prompt_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"WARNING: No JSON structure found in response\n")
                
                return {
                    "thought": "No structured thought provided",
                    "message": response_text[:200],
                    "raw": response_text
                }
                
        except Exception as e:
            # Response parsing failed
            with open("prompt_debug.log", "a", encoding="utf-8") as f:
                f.write(f"ERROR: Failed to parse response: {e}\n")
            
            return {
                "thought": "Error processing response",
                "message": raw_text.strip()[:200],
                "raw": raw_text
            }
        
    except Exception as e:
        # Request failed
        with open("prompt_debug.log", "a", encoding="utf-8") as f:
            f.write(f"ERROR: Request failed: {e}\n")
        
        return {
            "thought": "Error in LLM request",
            "message": "",
            "raw": ""
        }


def ask_ollama_simple(prompt: str, agent_name: str = None) -> str:
    """Legacy function that returns only the message text"""
    result = ask_ollama(prompt, agent_name)
    return result.get("message", "")


def truncate_thought(thought: str, max_length: int = 150) -> str:
    """Truncate thought for Discord display, keeping it readable"""
    if not thought or len(thought) <= max_length:
        return thought
    
    # Try to truncate at a sentence boundary
    sentences = re.split(r'[.!?]', thought)
    truncated = ""
    for sentence in sentences:
        if len(truncated) + len(sentence) + 3 <= max_length:
            truncated += sentence + ". "
        else:
            break
    
    if truncated:
        return truncated.strip() + "..."
    else:
        # If no complete sentence fits, just truncate
        return thought[:max_length-3] + "..."