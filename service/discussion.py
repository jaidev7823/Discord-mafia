import asyncio
from service.agent_repository import get_agents
from service.llm_service import ask_ollama
from service.tts_service import speak
from game.game_state import Phase, Role
from prompt.prompt_builder import build_discussion_prompt, build_killer_discussion_prompt

async def run_discussion_phase(bot, channel, game_state, duration, phase_type):
    """All agents discuss freely"""
    await channel.send(f"💬 **Discussion started...**")
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    
    discussion_history = []
    end_time = asyncio.get_event_loop().time() + duration
    
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
            
            # In run_discussion_phase function
            prompt = build_discussion_prompt(
                agent=agent,
                role=player.role,
                history=discussion_history,
                phase_type=phase_type,  # ← Changed from phase_tone to phase_type
                game_state=game_state
            )
            
            message = ask_ollama(prompt)
            
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

async def run_killer_discussion(channel, game_state, duration):
    """Private discussion among killers only"""
    
    killers = game_state.get_alive_by_role(Role.KILLER)
    if not killers:
        await channel.send("😴 No killers alive to discuss")
        return
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    
    await channel.send("🔪 **🔪 KILLER PRIVATE CHAT 🔪** (others cannot hear)")
    await channel.send("💬 **Killers, discuss who to kill tonight and why...**")
    
    discussion_history = []
    end_time = asyncio.get_event_loop().time() + duration
    
    while asyncio.get_event_loop().time() < end_time:
        for killer in killers:
            if asyncio.get_event_loop().time() >= end_time:
                break
                
            agent = agent_map.get(killer.agent_id)
            if not agent:
                continue
            
            other_killers = [k for k in killers if k.agent_id != killer.agent_id]
            alive_targets = [p for p in game_state.get_alive_players() if p.role != Role.KILLER]
            
            prompt = build_killer_discussion_prompt(
                agent, other_killers, alive_targets, discussion_history
            )
            
            message = ask_ollama(prompt)
            
            if message and len(message.strip()) > 3:
                discussion_history.append({
                    "speaker": agent["name"],
                    "message": message
                })
                
                await channel.send(f"🔪 **{agent['name']}**: {message}")
            
            await asyncio.sleep(2)
    
    game_state.last_killer_discussion = discussion_history