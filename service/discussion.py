# bot.py
import asyncio

from service.agent_repository import get_agents
from service.llm_service import ask_ollama
from service.tts_service import speak

from game.game_state import Phase
from prompt.prompt_builder import build_discussion_prompt

# service/discussion.py
async def run_discussion_phase(bot, channel, game_state, duration, phase_type):
    """All agents discuss freely"""
    await channel.send(f"💬 **Discussion started...**")
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    
    discussion_history = []
    end_time = asyncio.get_event_loop().time() + duration
    
    # Track if anyone has spoken
    messages_sent = 0
    
    while asyncio.get_event_loop().time() < end_time and messages_sent < len(game_state.get_alive_players()) * 2:
        # Each alive player speaks
        for player in game_state.get_alive_players():
            if asyncio.get_event_loop().time() >= end_time:
                break
                
            agent = agent_map.get(player.agent_id)
            if not agent:
                continue
            
            # Add role context to agent
            agent_with_role = agent.copy()
            agent_with_role["role"] = player.role.value
            
            # Build discussion prompt with more specific instructions
            prompt = f"""You are {agent['name']} ({player.role.value}) in a Mafia game.

Alive players: {', '.join([p.name for p in game_state.get_alive_players()])}

Recent conversation:
{chr(10).join([f"{msg['speaker']}: {msg['message']}" for msg in discussion_history[-5:]]) if discussion_history else "No one has spoken yet."}

Current phase: {phase_type.value.replace('_', ' ').title()}

What do you say? Express your thoughts, suspicions, or defend yourself.
Keep it to 1-2 sentences. Be natural and in-character."""
            
            message = ask_ollama(prompt)
            
            # Only add if message has content
            if message and len(message.strip()) > 3:
                discussion_history.append({
                    "speaker": agent["name"],
                    "role": player.role.value,
                    "message": message
                })
                
                await channel.send(f"💬 **{agent['name']}**: {message}")
                
                # Try to speak in voice if connected
                try:
                    await speak(bot, channel, agent, message)
                except:
                    pass  # Voice might not be connected
                    
                messages_sent += 1
            
            await asyncio.sleep(2)
    
    if messages_sent == 0:
        await channel.send("🤔 **No one had anything to say...**")
    else:
        await channel.send(f"💬 **Discussion ended** ({messages_sent} messages)")
    
    # Store discussion in game_state
    game_state.last_discussion = discussion_history