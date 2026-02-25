# service/tts_service.py
import os
import asyncio
import discord
import tempfile
import random
from service.chatterbox_tts import ChatterboxTTS
import gc
import torch

TTS_ENABLED = False 

# Voice samples mapping - you can assign these manually or randomly
VOICE_SAMPLES = {
    # You can assign specific agent IDs to specific voices
    # Format: agent_id: "path/to/voice.wav"
    1: "voice_samples/aizen.wav",
    2: "voice_samples/ayankoji.wav",
    3: "voice_samples/johanlibert.wav",
    4: "voice_samples/kira.wav",
    5: "voice_samples/L.wav",
}

# Available voices for random assignment
AVAILABLE_VOICES = [
    "voice_samples/aizen.wav",
    "voice_samples/ayankoji.wav", 
    "voice_samples/johanlibert.wav",
    "voice_samples/kira.wav",
    "voice_samples/L.wav"
]

# Global TTS instances per agent
agent_voices = {}  # agent_id -> ChatterboxTTS instance

async def initialize_agent_voice(agent_id: int, voice_path: str = None):
    """Initialize voice for an agent"""
    try:
        # If specific voice path provided, use it
        if voice_path and os.path.exists(voice_path):
            agent_voices[agent_id] = ChatterboxTTS(voice_path)
            print(f"✅ Voice initialized for agent {agent_id} using {os.path.basename(voice_path)}")
            return True
        
        # If agent has a predefined voice in mapping, use it
        if agent_id in VOICE_SAMPLES and os.path.exists(VOICE_SAMPLES[agent_id]):
            agent_voices[agent_id] = ChatterboxTTS(VOICE_SAMPLES[agent_id])
            print(f"✅ Voice initialized for agent {agent_id} using {os.path.basename(VOICE_SAMPLES[agent_id])}")
            return True
        
        # Otherwise, pick a random voice from available ones
        if AVAILABLE_VOICES:
            # Simple round-robin or random assignment
            random_voice = random.choice(AVAILABLE_VOICES)
            agent_voices[agent_id] = ChatterboxTTS(random_voice)
            print(f"✅ Voice initialized for agent {agent_id} using random voice: {os.path.basename(random_voice)}")
            return True
        else:
            print(f"⚠ No voice samples available for agent {agent_id}")
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
        return    """Speak a message in voice channel"""
    
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