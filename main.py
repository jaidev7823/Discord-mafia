import requests

url = "http://localhost:11434/api/chat"
payload = {
    "model": "gemma3",
    "messages": [{"role": "user", "content": "Hello, Gemma!"}],
    "stream": False
}

response = requests.post(url, json=payload)
print(response.json()['message']['content'])