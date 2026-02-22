import requests

url = "http://localhost:11434/api/chat"
payload = {
    "model": "ministral-3",
    "messages": [{"role": "user", "content": "Hello, Gemma!"}],
    "stream": False
}

response = requests.post(url, json=payload)
print(response.json()['message']['content'])