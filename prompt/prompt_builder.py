# prompt/prompt_builder.py
def build_prompt(agent, history, phase=None):
    context = "\n".join(
        f"{h['speaker']}: {h['message']}" for h in history[-10:]
    )

    phase_text = phase.upper() if phase else "DAY"

    return f"""
You are {agent['name']}.
Talk casually in a group chat.
Keep response 1 short line.
Current Phase: {phase_text}

Behavior Rules by Phase:

DAY:
- Open discussion
- Share opinions
- Mild suspicion allowed

EVENING:
- Increase suspicion
- Question others more directly

NIGHT:
- Speak briefly
- Be cautious
- Tone should feel quiet or tense

MORNING:
- React to events
- Express thoughts calmly

STRICT RULES:
- One sentence only
- No narration
- No stage directions
- No quotation marks

Personality: {agent['personality']}
Backstory: {agent['backstory']}
System Prompt: {agent['system_prompt']}

Conversation:
{context}

Your message:
"""

def build_night_decision_prompt(agent, game_state):
    alive_ids = list(game_state.alive_agents)

    return f"""
You are playing Mafia.

Your role: {agent['role']}
Alive players: {alive_ids}

Return ONLY one line:

If killer:
KILL: <agent_id>

If doctor:
SAVE: <agent_id>

If detective:
INVESTIGATE: <agent_id>

Do not explain.
Do not speak.
Return only the action.
"""

# prompt/prompt_builder.py (add these functions)

def build_vote_prompt(agent, game_state):
    """Prompt for DAY phase - all agents vote"""
    alive_players = game_state.get_alive_players()
    alive_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in alive_players])
    
    return f"""
You are {agent['name']} in a Mafia game.

Your role: {agent.get('role', 'unknown')}

Alive players:
{alive_list}

TASK: Vote for who you SUSPECT the most.
Return ONLY the agent_id number of your vote.
Do not explain. Do not add any text.
Just the number.
"""

def build_save_prompt(agent, game_state):
    """Prompt for EVENING phase - doctor only"""
    alive_players = game_state.get_alive_players()
    alive_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in alive_players])
    
    return f"""
You are {agent['name']} and you are the DOCTOR.

Alive players you can save:
{alive_list}

TASK: Choose ONE player to SAVE from the killer tonight.
Return ONLY the agent_id number of who you save.
Do not explain. Just the number.
"""

def build_kill_prompt(agent, game_state):
    """Prompt for NIGHT phase - killer only"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets
    alive_list = "\n".join([
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ])
    
    return f"""
You are {agent['name']} and you are the KILLER.

Alive players you can kill:
{alive_list}

TASK: Choose ONE player to KILL tonight.
Return ONLY the agent_id number of your target.
Do not explain. Just the number.
"""

def build_investigate_prompt(agent, game_state):
    """Prompt for MORNING phase - detective only"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets
    alive_list = "\n".join([
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ])
    
    return f"""
You are {agent['name']} and you are the DETECTIVE.

Alive players you can investigate:
{alive_list}

TASK: Choose ONE player to INVESTIGATE and learn if they are the killer.
Return ONLY the agent_id number of who you investigate.
Do not explain. Just the number.
"""