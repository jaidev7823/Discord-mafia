import discord
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
import requests

from service.agent_repository import get_agents
from service.llm_service import ask_ollama
from service.tts_service import speak
from prompt.prompt_builder import build_prompt

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONVERSATION LOOP ----------------------

async def run_conversation(channel, agents, rounds=3):
    history = []

    for _ in range(rounds):
        for agent in agents:
            prompt = build_prompt(agent, history)
            message = ask_ollama(prompt)

            history.append({
                "speaker": agent["name"],
                "message": message
            })

            await channel.send(f"**{agent['name']}**: {message}")
            await speak(bot, channel, agent, message)

            await asyncio.sleep(1)

# -------------------- PHASE SYSTEM -----------------------

class Phase:
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"
    MORNING = "morning"

PHASE_DURATIONS = {
    Phase.DAY: 20,
    Phase.EVENING: 10,
    Phase.NIGHT: 20,
    Phase.MORNING: 10,
}

phase_task = None

async def phase_loop(channel):
    phases = [
        Phase.DAY,
        Phase.EVENING,
        Phase.NIGHT,
        Phase.MORNING,
    ]

    index = 0

    while True:
        current_phase = phases[index]
        duration = PHASE_DURATIONS[current_phase]

        await channel.send(f"Phase started: {current_phase.upper()} ({duration}s)")
        await run_phase_chat(channel, current_phase, duration)

        index = (index + 1) % len(phases)

async def run_phase_chat(channel, phase, duration):
    agents = get_agents(limit=10)
    history = []

    end_time = asyncio.get_event_loop().time() + duration

    while asyncio.get_event_loop().time() < end_time:
        for agent in agents:
            prompt = build_prompt(agent, history, phase)
            message = ask_ollama(prompt)

            history.append({
                "speaker": agent["name"],
                "message": message
            })

            await channel.send(f"[{phase.upper()}] {agent['name']}: {message}")
            await speak(bot, channel, agent, message)

            await asyncio.sleep(1)

            if asyncio.get_event_loop().time() >= end_time:
                break

# =========================================================
# -------------------- SLASH COMMANDS ---------------------
# =========================================================

@bot.tree.command(name="start-chat", description="Start AI agents conversation")
async def start_chat(interaction: discord.Interaction):
    await interaction.response.defer()

    agents = get_agents(limit=5)

    if len(agents) < 5:
        await interaction.followup.send("Need at least 5 agents.")
        return

    await interaction.followup.send("AI agents are starting...")
    await run_conversation(interaction.channel, agents)

@bot.tree.command(name="join-voice")
async def join_voice(interaction: discord.Interaction):
    if interaction.user.voice:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("Joined voice.")
    else:
        await interaction.response.send_message("Join a voice channel first.")

@bot.tree.command(name="start-phases")
async def start_phases(interaction: discord.Interaction):
    global phase_task
    await interaction.response.send_message("Starting phase loop.")
    phase_task = bot.loop.create_task(phase_loop(interaction.channel))

@bot.tree.command(name="stop-phases")
async def stop_phases(interaction: discord.Interaction):
    global phase_task
    if phase_task:
        phase_task.cancel()
        await interaction.response.send_message("Phase loop stopped.")
    else:
        await interaction.response.send_message("No active phase loop.")

# =========================================================
# ------------------------ MODAL --------------------------
# =========================================================

class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):

    name = discord.ui.TextInput(label="Agent Name", max_length=30)
    personality = discord.ui.TextInput(label="Personality", style=discord.TextStyle.paragraph)
    backstory = discord.ui.TextInput(label="Backstory", style=discord.TextStyle.paragraph)
    system_prompt = discord.ui.TextInput(label="System Prompt", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            res = requests.post(
                "http://127.0.0.1:8000/agents",
                json={
                    "discord_id": str(interaction.user.id),
                    "username": interaction.user.name,
                    "name": self.name.value,
                    "personality": self.personality.value,
                    "backstory": self.backstory.value,
                    "system_prompt": self.system_prompt.value,
                    "pfp_url": None,
                },
            )

            if res.status_code == 200:
                await interaction.response.send_message(
                    f"Agent `{self.name.value}` created.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Error: {res.json()}",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.response.send_message(
                f"Backend error: {e}",
                ephemeral=True,
            )

@bot.tree.command(name="create-agent")
async def create_agent(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateAgentModal())

# =========================================================
# ------------------------- EVENTS ------------------------
# =========================================================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Slash commands synced")
    print(f"Bot ready as {bot.user}")

bot.run(TOKEN)