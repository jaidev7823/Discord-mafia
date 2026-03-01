# bot.py
import discord
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands

from bot.commands import setup_commands
from bot.voice import setup_voice_commands
from bot.phases import setup_phase_commands
from service.chatterbox_tts import load_global_model

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Setup all command groups
setup_commands(bot)
setup_voice_commands(bot)
setup_phase_commands(bot)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Slash commands synced")
    print(f"Bot ready as {bot.user}")

preload_tts = os.getenv("PRELOAD_TTS_MODEL", "1").lower() in ("1", "true", "yes", "on")
if preload_tts:
    print("🔄 Preloading TTS model before connecting to Discord...")
    asyncio.run(load_global_model())

bot.run(TOKEN)
