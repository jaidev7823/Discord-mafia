# service/action.py
from service.agent_repository import get_agents
from service.llm_service import ask_ollama
from prompt.prompt_builder import build_night_decision_prompt,build_kill_prompt,build_save_prompt,build_investigate_prompt

from game.game_engine import GameEngine
from game.game_state import Role

async def run_killer_action(channel, game_state, duration):
    """Only the killer chooses who to kill"""
    # Find the killer
    killer = game_state.get_killer()
    if not killer:
        await channel.send("⚠ No killer alive to kill anyone")
        return None
    
    # Get killer's agent data
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    killer_agent = agent_map.get(killer.agent_id)
    
    if not killer_agent:
        return None
    
    await channel.send(f"🔪 **Killer {killer.name} is choosing their target...**")
    
    # Build kill prompt
    prompt = build_kill_prompt(killer_agent, game_state)
    response = ask_ollama(prompt).strip()
    
    try:
        # Parse response: "KILL: 5" or just the number
        if ":" in response:
            target_id = int(response.split(":")[1].strip())
        else:
            target_id = int(response)
        
        # Validate target is alive
        if target_id in game_state.alive_agents:
            await channel.send(f"🎯 Killer is targeting {game_state.players[target_id].name}")
            
            # Log to database
            engine = GameEngine()
            engine.log_action(game_state.game_id, killer.agent_id, target_id, "night_kill")
            
            return target_id
        else:
            await channel.send("⚠ Killer chose an invalid target")
            
    except (ValueError, IndexError):
        await channel.send("⚠ Killer failed to choose")
    
    return None

async def run_detective_action(channel, game_state, duration):
    """Only the detective chooses who to investigate"""
    # Find the detective
    detective = game_state.get_detective()
    if not detective:
        await channel.send("⚠ No detective alive to investigate")
        return None
    
    # Get detective's agent data
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    detective_agent = agent_map.get(detective.agent_id)
    
    if not detective_agent:
        return None
    
    await channel.send(f"🕵️ **Detective {detective.name} is choosing who to investigate...**")
    
    # Build investigate prompt
    prompt = build_investigate_prompt(detective_agent, game_state)
    response = ask_ollama(prompt).strip()
    
    try:
        # Parse response: "INVESTIGATE: 5" or just the number
        if ":" in response:
            target_id = int(response.split(":")[1].strip())
        else:
            target_id = int(response)
        
        # Validate target is alive
        if target_id in game_state.alive_agents:
            # Determine if target is killer
            is_killer = game_state.players[target_id].role == Role.KILLER
            
            await channel.send(f"🔍 Detective investigated {game_state.players[target_id].name}")
            
            # Log to database
            engine = GameEngine()
            engine.log_investigation(game_state.game_id, target_id, is_killer)
            
            return (target_id, is_killer)
        else:
            await channel.send("⚠ Detective chose an invalid target")
            
    except (ValueError, IndexError):
        await channel.send("⚠ Detective failed to choose")
    
    return None

async def run_doctor_action(channel, game_state, duration):
    """Only the doctor chooses who to save"""
    # Find the doctor
    doctor = game_state.get_doctor()
    if not doctor:
        await channel.send("⚠ No doctor alive to save anyone")
        return None
    
    # Get doctor's agent data
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    doctor_agent = agent_map.get(doctor.agent_id)
    
    if not doctor_agent:
        return None
    
    await channel.send(f"🩺 **Doctor {doctor.name} is choosing who to save...**")
    
    # Build save prompt
    prompt = build_save_prompt(doctor_agent, game_state)
    response = ask_ollama(prompt).strip()
    
    try:
        # Parse response: "SAVE: 5" or just the number
        if ":" in response:
            target_id = int(response.split(":")[1].strip())
        else:
            target_id = int(response)
        
        # Validate target is alive
        if target_id in game_state.alive_agents:
            await channel.send(f"✅ Doctor chose to save {game_state.players[target_id].name}")
            
            # Log to database
            engine = GameEngine()
            engine.log_action(game_state.game_id, doctor.agent_id, target_id, "night_save")
            
            return target_id
        else:
            await channel.send("⚠ Doctor chose an invalid target - no one saved")
            
    except (ValueError, IndexError):
        await channel.send("⚠ Doctor failed to choose - no one saved")
    
    return None



async def collect_night_actions(channel, game_state):
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}

    killer_target = None
    doctor_target = None
    detective_target = None

    for player in game_state.get_alive_players():

        if player.role == Role.CITIZEN:
            continue

        agent = agent_map[player.agent_id]
        agent["role"] = player.role.value

        prompt = build_night_decision_prompt(agent, game_state)
        response = ask_ollama(prompt).strip()

        try:
            action, target = response.split(":")
            target = int(target.strip())
        except:
            continue
        
        if target not in game_state.alive_agents:
            continue
        
        if player.role == Role.KILLER:
            killer_target = target

        elif player.role == Role.DOCTOR:
            doctor_target = target

        elif player.role == Role.DETECTIVE:
            detective_target = target

    return killer_target, doctor_target, detective_target
