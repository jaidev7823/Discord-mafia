# bot/voice.py
import discord
from service import tts_service

def setup_voice_commands(bot):
    """Setup voice-related commands"""
    
    @bot.tree.command(name="join-voice", description="Join your current voice channel")
    async def join_voice(interaction: discord.Interaction):
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            await interaction.response.send_message("✅ Joined voice channel.")
        else:
            await interaction.response.send_message("❌ You need to be in a voice channel first.")

    @bot.tree.command(name="leave-voice", description="Leave the current voice channel")
    async def leave_voice(interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 Left voice channel.")
        else:
            await interaction.response.send_message("❌ Not in a voice channel.")

    @bot.tree.command(name="toggle-tts", description="Enable/disable TTS")
    async def toggle_tts(interaction: discord.Interaction):
        tts_service.TTS_ENABLED = not tts_service.TTS_ENABLED
        status = "enabled" if tts_service.TTS_ENABLED else "disabled"
        await interaction.response.send_message(f"🔊 TTS {status}")

    @bot.tree.command(name="voice-status", description="Check voice initialization status")
    async def voice_status(interaction: discord.Interaction):
        await interaction.response.defer()
        
        msg = f"**TTS Enabled:** {tts_service.TTS_ENABLED}\n"
        msg += f"**Initialized Voices:** {len(tts_service.agent_voices)}\n"
        
        if tts_service.agent_voices:
            msg += "\n**Agents with voices:**\n"
            for agent_id in list(tts_service.agent_voices.keys())[:10]:  # Show first 10
                msg += f"  • Agent {agent_id}\n"
        
        await interaction.followup.send(msg)
