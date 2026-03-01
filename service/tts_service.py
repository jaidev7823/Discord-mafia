# service/tts_service.py
import os
import asyncio
import discord
import tempfile
from service.chatterbox_tts import ChatterboxTTS
import gc
import torch

TTS_ENABLED = True 

# Deprecated: hardcoded/random voice pools are intentionally disabled.
# VOICE_SAMPLES = {...}
# AVAILABLE_VOICES = [...]

# Global TTS instances per agent
agent_voices = {}  # agent_id -> ChatterboxTTS instance

async def initialize_agent_voice(agent_id: int, voice_path: str = None):
    """Initialize voice for an agent using DB voice_path only."""
    try:
        if not voice_path:
            print(f"⚠ No voice_path in DB for agent {agent_id}")
            agent_voices[agent_id] = None
            return False

        if os.path.exists(voice_path):
            agent_voices[agent_id] = ChatterboxTTS(voice_path)
            print(f"✅ Voice initialized for agent {agent_id} using {os.path.basename(voice_path)}")
            return True

        print(f"⚠ Voice file not found for agent {agent_id}: {voice_path}")
        agent_voices[agent_id] = None
        return False
            
    except Exception as e:
        print(f"❌ Voice init error for agent {agent_id}: {e}")
        agent_voices[agent_id] = None
        return False

async def speak(bot, channel, agent, message, emotion=None):
    """Speak a message in voice channel"""
    if not TTS_ENABLED:
        print(f"[TTS DISABLED] {agent['name']}: {message[:50]}...")
        return
    
    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
    
    if not voice_client or not voice_client.is_connected():
        return
    
    while voice_client.is_playing():
        await asyncio.sleep(0.2)
    
    tts_engine = agent_voices.get(agent['id'])
    
    if not tts_engine:
        print(f"🔊 NO VOICE - {agent['name']}: {message[:50]}...")
        return
    
    try:
        print(f"🎙 {agent['name']} speaking: {message[:50]}...")
        # Clear cache before generation
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
        
        # Synthesize
        wav, sr = await tts_engine.synthesize(message, emotion)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            await tts_engine.save_to_file(wav, sr, temp_path)
        
        # Play in Discord
        voice_client.play(discord.FFmpegPCMAudio(temp_path))
        
        while voice_client.is_playing():
            await asyncio.sleep(0.2)
        
        # Cleanup
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"❌ TTS error for {agent['name']}: {e}")
        # Clear cache on error too
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

class TTSService:
    """Simple wrapper for TTS"""
    def __init__(self):
        self.agent_voices = agent_voices
    
    async def speak(self, text: str, voice_client, agent_id: int = None, emotion: str = None):
        if agent_id and agent_id in self.agent_voices:
            agent = {"id": agent_id, "name": f"Agent_{agent_id}"}
            await speak(None, None, agent, text, emotion)
