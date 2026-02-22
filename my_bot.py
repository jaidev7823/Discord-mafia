import discord   # Installed via pip
import os        # Built-in (No pip install needed)
import requests  # Installed via pip
from dotenv import load_dotenv # Installed via pip
from discord import app_commands
from discord.ext import commands


# 1. Load the variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2. Setup Intents
intents = discord.Intents.default()
intents.message_content = True 

client = discord.Client(intents=intents)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):

    name = discord.ui.TextInput(
        label="Agent Name",
        max_length=30
    )

    personality = discord.ui.TextInput(
        label="Personality",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    backstory = discord.ui.TextInput(
        label="Backstory",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    system_prompt = discord.ui.TextInput(
        label="System Prompt",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Here you will save to DB later
        await interaction.response.send_message(
            f"Agent `{self.name}` received successfully.",
            ephemeral=True
        )

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot ready")

@bot.tree.command(name="create-agent", description="Create a new AI agent")
async def create_agent(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateAgentModal())

bot.run(TOKEN)
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