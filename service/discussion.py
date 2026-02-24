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
    
    # Determine discussion tone based on phase
    tone = {
        Phase.MORNING_DISCUSSION: "casual discussion about who seems suspicious",
        Phase.EVENING_DISCUSSION: "quieter discussion, doctor is listening carefully",
        Phase.NIGHT_DISCUSSION: "tense, people are cautious"
    }.get(phase_type, "normal discussion")
    
    messages_sent = 0
    
    while asyncio.get_event_loop().time() < end_time and messages_sent < len(game_state.get_alive_players()) * 2:
        for player in game_state.get_alive_players():
            if asyncio.get_event_loop().time() >= end_time:
                break
                
            agent = agent_map.get(player.agent_id)
            if not agent:
                continue
            
            # ✅ USE YOUR EXISTING FUNCTION HERE!
            prompt = build_discussion_prompt(
                agent=agent,
                role=player.role,
                history=discussion_history,
                phase_tone=tone,
                game_state=game_state
            )
            
            message = ask_ollama(prompt)
            
            # Only add if message has content
            if message and len(message.strip()) > 3:
                discussion_history.append({
                    "speaker": agent["name"],
                    "role": player.role.value,
                    "message": message
                })
                
                await channel.send(f"💬 **{agent['name']}**: {message}")
                
                try:
                    await speak(bot, channel, agent, message)
                except:
                    pass
                    
                messages_sent += 1
            
            await asyncio.sleep(2)
    
    if messages_sent == 0:
        await channel.send("🤔 **No one had anything to say...**")
    else:
        await channel.send(f"💬 **Discussion ended** ({messages_sent} messages)")
    
    game_state.last_discussion = discussion_history