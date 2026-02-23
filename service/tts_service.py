import os
import asyncio
import unicodedata
import re
import discord
from tts import synthesize_to_file

def clean_text_for_tts(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

async def speak(bot, channel, agent, message):
    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)

    if not voice_client or not voice_client.is_connected():
        return

    # Wait for current audio to finish instead of skipping
    while voice_client.is_playing():
        await asyncio.sleep(0.2)

    clean_message = clean_text_for_tts(message)
    if not clean_message:
        return

    output_file = f"temp_{agent['id']}.wav"
    synthesize_to_file(clean_message, output_file)

    source = discord.FFmpegPCMAudio(output_file)
    voice_client.play(source)

    while voice_client.is_playing():
        await asyncio.sleep(0.2)

    os.remove(output_file)