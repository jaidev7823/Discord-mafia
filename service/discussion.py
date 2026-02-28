# game/discussion_phase.py - UPDATED to handle thought/message structure

import asyncio
from service.agent_repository import get_agents
from service.llm_service import ask_llm
from service.tts_service import speak
from game.game_state import Phase, Role
from prompt.prompt_builder import build_discussion_prompt, build_killer_discussion_prompt

async def run_discussion_phase(bot, channel, game_state, duration, phase_type):
    """All agents discuss freely with thought/message separation"""
    await channel.send(f"💬 **Discussion started...**")
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    
    discussion_history = []  # Now stores dicts with thought+message
    end_time = asyncio.get_event_loop().time() + duration
    
    messages_sent = 0
    
    while asyncio.get_event_loop().time() < end_time and messages_sent < len(game_state.get_alive_players()) * 2:
        for player in game_state.get_alive_players():
            if asyncio.get_event_loop().time() >= end_time:
                break
                
            agent = agent_map.get(player.agent_id)
            if not agent:
                continue
            
            # Build prompt with full history
            prompt = build_discussion_prompt(
                agent=agent,
                role=player.role,
                history=discussion_history,
                phase_type=phase_type,
                game_state=game_state,
                current_speaker_id=agent["id"]
            )
            
            response = ask_llm(prompt, agent["name"])
            
            # After getting response from ask_ollama:
            if response and response.get("message") and len(response["message"].strip()) > 3:
                # Store full thought+message in history
                discussion_history.append({
                    "speaker": agent["name"],
                    "speaker_id": agent["id"],
                    "role": player.role.value,
                    "thought": response["thought"],  # Store full thought
                    "message": response["message"]
                })

                # Show only the message publicly
                await channel.send(f"💬 **{agent['name']}**: {response['message']}")

                # Log truncated thought to console (for debugging)
                from service.llm_service import truncate_thought
                truncated_thought = truncate_thought(response["thought"], max_length=150)
                print(f"[{agent['name']} THOUGHT]: {truncated_thought}")

                # Optionally log full thought to file
                with open("tests/thoughts_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"{agent['name']} - {phase_type.value}\n")
                    f.write(f"FULL THOUGHT:\n{response['thought']}\n")
                    f.write(f"SAID: {response['message']}\n")
            
            await asyncio.sleep(2)
    
    if messages_sent == 0:
        await channel.send("🤔 **No one had anything to say...**")
    else:
        await channel.send(f"💬 **Discussion ended** ({messages_sent} messages)")
    
    game_state.last_discussion = discussion_history


async def run_killer_discussion(channel, game_state, duration):
    """Private discussion among killers with thought/message separation"""
    
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
            
            response = ask_ollama(prompt)
            
            if response and response.get("message") and len(response["message"].strip()) > 3:
                discussion_history.append({
                    "speaker": agent["name"],
                    "speaker_id": agent["id"],
                    "thought": response["thought"],
                    "message": response["message"]
                })
                
                await channel.send(f"🔪 **{agent['name']}**: {response['message']}")
                print(f"[{agent['name']} KILLER THOUGHT]: {response['thought']}")
            
            await asyncio.sleep(2)
    
    game_state.last_killer_discussion = discussion_history