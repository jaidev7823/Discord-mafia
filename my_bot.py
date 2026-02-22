import discord   # Installed via pip
import os        # Built-in (No pip install needed)
import requests  # Installed via pip
from dotenv import load_dotenv # Installed via pip

# 1. Load the variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2. Setup Intents
intents = discord.Intents.default()
intents.message_content = True 

client = discord.Client(intents=intents)

# 3. Function to talk to Ollama
def ask_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "ministral-3",
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload)
        return response.json().get("response", "No response from AI.")
    except Exception as e:
        return f"Error: {e}"

@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message):
        clean_prompt = message.content.replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '').strip()
        async with message.channel.typing():
            answer = ask_ollama(clean_prompt)
            await message.reply(answer)

client.run(TOKEN)