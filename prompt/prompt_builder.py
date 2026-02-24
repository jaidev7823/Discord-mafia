from game.game_state import Phase

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

STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
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

def build_vote_prompt(agent, game_state):
    """Prompt for DAY phase - all agents vote"""
    alive_players = game_state.get_alive_players()
    alive_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in alive_players])
    
    return f"""
You are {agent['name']} in a Mafia game.

Your role: {agent.get('role', 'unknown')}

Alive players:
{alive_list}

STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally

TASK: Vote for who you SUSPECT the most.
Return ONLY the agent_id number of your vote.
Do not explain. Do not add any text.
Just the number.
"""

def build_save_prompt(agent, game_state):
    """Prompt for EVENING phase - doctor only"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets (doctor can't save themselves usually)
    alive_list = "\n".join([
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ])
    
    return f"""You are {agent['name']} and you are the DOCTOR in a Mafia game.

Your role: DOCTOR
Your ID: {agent['id']}

Alive players you can save (cannot save yourself):
{alive_list}
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
TASK: Choose ONE player to SAVE from the killer tonight.
You must return ONLY the agent_id number of who you save.
Do not add any extra text, explanations, or formatting.
Just a single number.

Example correct responses:
5
12
3

Your response (just the number):"""

def build_kill_prompt(agent, game_state, discussion_text):
    """Prompt for NIGHT phase - killer only"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets
    alive_list = "\n".join([
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ])
    
    return f"""
You are {agent['name']} and you are the KILLER.
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
Alive players you can kill:
{alive_list}

{discussion_text}

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
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
Alive players you can investigate:
{alive_list}

TASK: Choose ONE player to INVESTIGATE and learn if they are the killer.
Return ONLY the agent_id number of who you investigate.
Do not explain. Just the number.
"""

def build_discussion_prompt(agent, role, history, phase_type, game_state):
    """Prompt with ULTRA-STRICT rules to prevent actions/descriptions"""
    
    identity = f"""YOU ARE: {agent['name']}
YOUR ROLE: {role.value.upper()}
YOUR PERSONALITY: {agent.get('personality', 'Normal')}"""

    alive_players = [p.name for p in game_state.get_alive_players()]
    dead_players = [p.name for p in game_state.players.values() if not p.is_alive]
    
    reality = f"""CURRENT GAME REALITY:
- Alive players: {', '.join(alive_players)}
- Dead players: {', '.join(dead_players) if dead_players else 'No one has died yet'}
- Today is Day {game_state.day_number}
- You are in {phase_type.value.replace('_', ' ')} phase"""

    if history:
        conversation = "\n".join([
            f"{msg['speaker']}: {msg['message']}" 
            for msg in history[-5:]
        ])
    else:
        conversation = "No one has spoken yet in this game."
    
    # ULTRA-STRICT RULES
    rules = """ABSOLUTE RULES - VIOLATION WILL BREAK THE GAME:
1. OUTPUT ONLY THE WORDS YOU SPEAK - NOTHING ELSE
2. NO asterisks, NO *actions*, NO descriptions
3. NO "leans back", NO "voice low", NO "fingers steepled"
4. NO environment descriptions - no "room is silent"
5. NO tone indicators - not "measured" or "quiet"
6. JUST THE DIALOGUE - exactly what comes out of your mouth
7. Only reply in one two sentence not big paragraph.
8. Mention the name of who you are talking to.

CORRECT example: "I think Viper is acting suspicious."
INCORRECT example: *leans back* "I think Viper is acting suspicious."

Your response must contain ONLY your spoken words."""

    return f"""{identity}

{reality}

CONVERSATION SO FAR:
{conversation}

{rules}

What do you say? (JUST the words, NO actions):"""

def build_voting_prompt_with_context(agent, role, discussion_history, game_state):
    """Voting prompt that uses the discussion context"""
    
    # Summarize key moments from discussion
    discussion_summary = "\n".join([
        f"{msg['speaker']} ({msg['role']}): {msg['message']}"
        for msg in discussion_history[-15:]  # Last 15 messages
    ])
    
    alive_players = game_state.get_alive_players()
    alive_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in alive_players])
    
    return f"""
You are {agent['name']} ({role.value.upper()}).
Based on the discussion you just had:

{discussion_summary}

Alive players you can vote for:
{alive_list}
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
TASK: Vote for who you SUSPECT the most.
Consider what everyone said during discussion.
Return ONLY the agent_id number.
"""

def build_doctor_decision_prompt(agent, discussion_history, game_state):
    discussion_summary = "\n".join([
        f"{msg['speaker']}: {msg['message']}"
        for msg in discussion_history[-20:]
    ]) if discussion_history else "No discussion yet."
    
    alive_players = game_state.get_alive_players()
    player_list = "\n".join([f"ID {p.agent_id}: {p.name}" for p in alive_players if p.agent_id != agent['id']])
    
    return f"""
You are the DOCTOR. Based on this discussion:

{discussion_summary}

Alive players (with their IDs):
{player_list}
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
TASK: Choose ONE player to save tonight.
You MUST return ONLY the agent_id number.
Do not add any text, just the number.

Example correct response: 5

Your response (just the number):"""

def build_killer_discussion_prompt(agent, other_killers, alive_targets, discussion_history):
    """Prompt for killer private discussion"""
    
    other_killers_text = ', '.join([k.name for k in other_killers]) if other_killers else "None (you're alone)"
    
    targets_text = "\n".join([f"• {p.name}" for p in alive_targets])
    
    recent_discussion = "\n".join([f"{msg['speaker']}: {msg['message']}" for msg in discussion_history[-5:]]) if discussion_history else "Discussion starting."
    
    return f"""You are {agent['name']} and you are a KILLER discussing with your fellow killers.
Other killers: {other_killers_text}
STRICT RULES:
- ONE SENTENCE ONLY
- No asterisks or actions like *leans in*
- No descriptions of movements or tone
- No quotation marks around your speech
- Just speak normally
Potential targets (non-killers):
{targets_text}

Recent discussion:
{recent_discussion}

What do you say? Propose a target, give reasons, or respond to others.
Keep it to 1-2 sentences."""