# bot.py
import discord
import os
import requests
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def start_chat(ctx):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, name FROM agents LIMIT 5")
        ).fetchall()

        if len(rows) < 5:
            await ctx.send("Need at least 5 agents in database.")
            return

        agents = [{"id": r[0], "name": r[1]} for r in rows]

    finally:
        db.close()

    await ctx.send("AI agents are starting a conversation...")

    await run_conversation(ctx.channel, agents)
# ----------------------------
# Ollama function
# ----------------------------
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


# ----------------------------
# Modal
# ----------------------------
class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):

    name = discord.ui.TextInput(label="Agent Name", max_length=30)
    personality = discord.ui.TextInput(label="Personality", style=discord.TextStyle.paragraph)
    backstory = discord.ui.TextInput(label="Backstory", style=discord.TextStyle.paragraph)
    system_prompt = discord.ui.TextInput(label="System Prompt", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            response = requests.post(
                "http://127.0.0.1:8000/agents",
                json={
                    "discord_id": str(interaction.user.id),
                    "username": interaction.user.name,
                    "name": self.name.value,
                    "personality": self.personality.value,
                    "backstory": self.backstory.value,
                    "system_prompt": self.system_prompt.value,
                    "pfp_url": None
                }
            )

            if response.status_code == 200:
                await interaction.response.send_message(
                    f"Agent `{self.name.value}` created successfully.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Error: {response.json()}",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.response.send_message(
                f"Backend error: {e}",
                ephemeral=True
            )


# ----------------------------
# Events
# ----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ready as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        clean_prompt = message.content.replace(f"<@!{bot.user.id}>", "").replace(f"<@{bot.user.id}>", "").strip()
        async with message.channel.typing():
            answer = ask_ollama(clean_prompt)
            await message.reply(answer)

    await bot.process_commands(message)


# ----------------------------
# Slash Command
# ----------------------------
@bot.tree.command(name="create-agent", description="Create a new AI agent")
async def create_agent(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateAgentModal())


bot.run(TOKEN)
