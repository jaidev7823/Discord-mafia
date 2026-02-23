# bot.py
import discord
import os
import asyncio
import requests
from dotenv import load_dotenv
from discord.ext import commands
from sqlalchemy import text
from db.database import SessionLocal
from tts import synthesize_to_file
import re
import unicodedata

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# -------------------- UTILITIES --------------------------
# =========================================================

def clean_text_for_tts(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text  # <-- THIS WAS MISSING


def ask_ollama(prompt: str) -> str:
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "ministral-3",
                "prompt": prompt,
                "stream": False,
            },
        )
        return res.json().get("response", "No response.")
    except Exception as e:
        return f"Error: {e}"


def get_agents(limit=5):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT id, name, personality, backstory, system_prompt
                FROM agents
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "personality": r[2],
                "backstory": r[3],
                "system_prompt": r[4],

            }
            for r in rows
        ]
    finally:
        db.close()


def build_prompt(agent, history, phase=None):
    context = "\n".join(
        f"{h['speaker']}: {h['message']}" for h in history[-10:]
    )

    return f"""
You are {agent['name']}.
Talk casually in a group chat.
Keep response 1 short line.
Current Phase: {phase.upper()}

Behavior Rules by Phase:

DAY:
- Open discussion
- Share opinions
- Mild suspicion allowed

EVENING:
- Increase suspicion
- Question others more directly

NIGHT:
- Speak briefly
- Be cautious
- Tone should feel quiet or tense

MORNING:
- React to events
- Express thoughts calmly

STRICT RULES:
- One sentence only
- No narration
- No stage directions
- No quotation marks

Personality: {agent['personality']}
Backstory: {agent['backstory']}
System Prompt: {agent['system_prompt']}

Conversation:
{context}

Your message:
"""

import os

async def speak(channel, agent, message):
    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)

    if not voice_client or not voice_client.is_connected():
        return

    if voice_client.is_playing():
        return

    clean_message = clean_text_for_tts(message)
    if not clean_message:
        return

    output_file = f"temp_{agent['id']}.wav"

    try:
        synthesize_to_file(
            text=clean_message,
            output_path=output_file,
        )
    except Exception as e:
        print("TTS error:", e)
        return

    try:
        source = discord.FFmpegPCMAudio(output_file)
        voice_client.play(source)
    except Exception as e:
        print("Voice play error:", e)
        return

    while voice_client.is_playing():
        await asyncio.sleep(0.2)

    os.remove(output_file)

# =========================================================
# ---------------- CONVERSATION LOOP ----------------------
# =========================================================

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
            voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
            await channel.send(f"**{agent['name']}**: {message}")

            if voice_client:
                await speak(channel, agent, message)

            await asyncio.sleep(1)

# =========================================================
# -------------------- SLASH COMMANDS ---------------------
# =========================================================

@bot.tree.command(name="start-chat", description="Start AI agents conversation")
async def start_chat(interaction: discord.Interaction):
    try:
        await interaction.response.defer()

        agents = get_agents()

        if len(agents) < 5:
            await interaction.followup.send("Need at least 5 agents.")
            return

        await interaction.followup.send("AI agents are starting...")
        await run_conversation(interaction.channel, agents)

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"Error: {e}")


@bot.tree.command(name="create-agent", description="Create a new AI agent")
async def create_agent(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateAgentModal())

@bot.tree.command(name="join-voice")
async def join_voice(interaction: discord.Interaction):
    if interaction.user.voice:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("Joined voice.")
    else:
        await interaction.response.send_message("Join a voice channel first.")

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
    agents = get_agents()
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

            await speak(channel, agent, message)

            await asyncio.sleep(1)

            if asyncio.get_event_loop().time() >= end_time:
                break

@bot.tree.command(name="start-phases")
async def start_phases(interaction: discord.Interaction):
    await interaction.response.send_message("Starting phase loop.")
    global phase_task
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
# ------------------------- EVENTS ------------------------
# =========================================================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Slash commands synced")
    print(f"Bot ready as {bot.user}")


bot.run(TOKEN)
