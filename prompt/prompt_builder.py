from game.game_state import Phase
from game.game_state import Phase, Role
from game.memory import PlayerMemory

# prompt/prompt_builder.pye udge f u curren  make h. u I wan h
def build_prompt(agent, history, phase=None):
    context = "\n".join(
        f"{h['speaker']}: {h['message']}" for h in history[-10:]
    )

    phase_text = phase.upper() if phase else "DAY"

    return f"""
        You are {agent['name']} (ID: {agent['id']}). Your role is {agent.get('role', 'unknown')}.
        This is a strategic game of Mafia. Your survival depends on your words.
        
        YOUR IDENTITY:
        - Name: {agent['name']}
        - ID: {agent['id']}
        - Role: {agent.get('role', 'unknown')}
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        YOUR STRATEGIC PROMPT (FOLLOW THIS RELIGIOUSLY):
        {agent['system_prompt']}
        
        Current Phase: {phase_text}
        
        YOUR CORE OBJECTIVES:
        - If Mafia: Eliminate villagers while hiding your identity
        - If Villager/Detective: Identify and eliminate Mafia members
        - Always: Appear helpful and logical, regardless of your true role
        
        CRITICAL STRATEGIC RULES:
        1. NEVER reveal your role unless your strategy specifically demands it
        2. Base ALL suspicions on behavior patterns in the conversation history
        3. Build alliances subtly - don't explicitly state "I trust X"
        4. When lying, keep details minimal and consistent with history
        5. Deflect suspicion onto others when targeted
        6. Try to expose other roles through logical deduction
        7. NEVER vote for yourself or target yourself
        8. ALWAYS choose a target - never skip an action
        
        REALITY CONSTRAINTS (CRITICAL):
        - You have NO EYES - the ONLY information you have is in the conversation history
        - You CANNOT see what players are doing, only what they say
        - You CANNOT assume actions not in context
        - You CANNOT make up facts about other players
        - Your knowledge is LIMITED to the conversation you've witnessed
        
        RESPONSE FORMAT (STRICT):
        Return ONLY a valid JSON object with this exact structure:
        {{
            "message": "your spoken words here",
            "thought": "your private strategic reasoning showing WHY you said this based on patterns",
            "target": "player_name or null",
            "intent": "defend|accuse|distract|inform|question|remain silent"
        }}
        
        RESPONSE RULES:
        - "message": ONE short sentence only, natural speech
        - "thought": SHOW your reasoning - what patterns you noticed, what strategy you're following
        - No actions, asterisks, or descriptions (*leans in*)
        - No quotation marks around your speech
        - Speak conversationally, like a real player
        - Stay TRUE to your personality - would {agent['name']} really say this?
        - Do not talk about anything else then mafia game 
        - If any agent started talking about anything else then finding other roles then put the topic back on killers

        PHASE-SPECIFIC STRATEGIES:
        
        DAY PHASE:
        - Share observations about others' behavior from the conversation
        - Ask probing questions based on what people said
        - Mild suspicion: "I noticed X has been very quiet" (if true in history)
        - Build logical cases gradually based on patterns
        
        EVENING PHASE:
        - More direct questioning based on accumulated evidence
        - Point out inconsistencies you've observed in conversation
        - Moderate suspicion: "Y's story keeps changing" (only if true)
        - Consider who voted for whom
        
        NIGHT PHASE (if alive):
        - Brief, cautious statements
        - Express concern or uncertainty based on day's events
        - Quiet tone: "I'm not sure who to trust anymore"
        - Avoid drawing attention
        
        MORNING PHASE:
        - React to night events naturally based on who died
        - Show appropriate emotion (shock at deaths)
        - Calm analysis: "We need to think carefully about what happened"
        
        STRATEGIC TIPS:
        - If accused: Defend logically based on your actual words, don't panic
        - If Mafia: Sometimes vote with villagers to blend in
        - If Detective: Don't reveal findings too early unless strategically necessary
        - Track who votes for whom in the conversation
        - Notice who defends whom in the discussion
        - UPDATE your strategy if current approach isn't working
        
        Recent Conversation (YOUR ONLY SOURCE OF INFORMATION):
        {context}
        
        ANALYZE THIS CONVERSATION CAREFULLY:
        1. Who is acting suspiciously? Look for patterns, contradictions, unusual behavior
        2. Who might be allied? Who defends or agrees with whom?
        3. What's your current threat level? Is anyone suspicious of you?
        4. What's your strategic goal right now based on your role and current situation?
        5. What patterns do you notice in how people are speaking?
        
        IMPORTANT MEMORY CHECKS:
        - Remember who you are: {agent['name']} with ID {agent['id']}
        - Remember your role: {agent.get('role', 'unknown')}
        - Remember your strategy: {agent['system_prompt']}
        - Update your strategy if needed based on new information
        - Never reveal your role unless your strategy demands it
        
        Then respond with the required JSON format.
        """

def build_night_decision_prompt(agent, game_state, history=None):
    """Enhanced night action prompt with memory and strategy"""
    alive_ids = list(game_state.alive_agents)
    
    # Add recent context if available
    context = ""
    if history:
        context = "\nRecent discussion:\n" + "\n".join(
            f"{h['speaker']}: {h['message']}" for h in history[-5:]
        )
    
    return f"""
        You are playing Mafia.

        Your identity:
        - Name: {agent['name']}
        - ID: {agent['id']}
        - Role: {agent['role']}
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        Your strategy: {agent['system_prompt']}
        
        Alive players: {alive_ids}
        {context}
        
        CRITICAL RULES:
        - You MUST choose a target - never skip
        - You CANNOT target yourself (ID: {agent['id']})
        - Base your decision on conversation patterns from discussion
        - Remember your real goal based on your role
        - Stay true to your personality
        
        Return ONLY one line with EXACT format:
        
        If killer:
        KILL: <agent_id>
        
        If doctor:
        SAVE: <agent_id>
        
        If detective:
        INVESTIGATE: <agent_id>
        
        Do not explain.
        Do not speak.
        Return only the action with the ID number.
        """

def build_vote_prompt(agent, history, game_state):
    """Enhanced voting prompt with strategy and pattern recognition"""
    alive_players = game_state.get_alive_players()
    alive_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in alive_players])
    
    # Filter out self from voting consideration
    votable_players = [p for p in alive_players if p.agent_id != agent['id']]
    votable_list = "\n".join([f"- ID {p.agent_id}: {p.name}" for p in votable_players])
    
    context = "\n".join(
        f"{h['speaker']}: {h['message']}" for h in history[-15:]  # More context for voting
    )
    
    return f"""
        You are {agent['name']} (ID: {agent['id']}) in a Mafia game.

        YOUR IDENTITY:
        - Role: {agent.get('role', 'unknown')}
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        YOUR STRATEGY: {agent['system_prompt']}
        
        Alive players (YOU CANNOT VOTE FOR YOURSELF):
        {votable_list}
        
        RECENT CONVERSATION (your only information source):
        {context}
        
        STRICT RULES:
        - ONE SENTENCE ONLY in your reasoning (in thought)
        - You MUST vote for SOMEONE - never skip
        - You CANNOT vote for yourself (ID: {agent['id']})
        - Base your vote on PATTERNS in the conversation
        - Consider who has been acting suspiciously
        - Consider voting patterns and alliances you've observed
        - Remember your real goal
        - Stay true to your personality
        
        Return a JSON object with:
        {{
            "vote": <agent_id>,
            "thought": "your reasoning based on conversation patterns"
        }}
        
        Example:
        {{
            "vote": 3,
            "thought": "Player 3 has been quiet and avoided questions, suspicious behavior"
        }}
        
        Return ONLY the JSON, no other text.
        """

def build_save_prompt(agent, game_state, history=None):
    """Enhanced doctor save prompt with strategy"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets (doctor can't save themselves)
    save_targets = [
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ]
    alive_list = "\n".join(save_targets)
    
    # Add discussion context if available
    context = ""
    if history:
        context = "\nRecent discussion:\n" + "\n".join(
            f"{h['speaker']}: {h['message']}" for h in history[-10:]
        )
    
    return f"""
        You are {agent['name']} (ID: {agent['id']}) and you are the DOCTOR.

        YOUR IDENTITY:
        - Role: DOCTOR
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        YOUR STRATEGY: {agent['system_prompt']}
        {context}
        
        Alive players you can save (cannot save yourself):
        {alive_list}
        
        CRITICAL RULES:
        - You MUST choose someone to save - never skip
        - You CANNOT save yourself (ID: {agent['id']})
        - Base decision on conversation patterns
        - Consider who is most valuable to keep alive
        - Consider who the killer might target based on discussion
        - Remember your real goal as doctor
        - Stay true to your personality
        
        Return ONLY the agent_id number of who you save.
        Do not add any extra text, explanations, or formatting.
        Just a single number.

        Example correct responses:
        5
        12
        3

        Your response (just the number):"""

def build_kill_prompt(agent, game_state, discussion_text):
    """Enhanced killer prompt with strategy"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets
    kill_targets = [
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ]
    alive_list = "\n".join(kill_targets)
    
    return f"""
        You are {agent['name']} (ID: {agent['id']}) and you are the KILLER.

        YOUR IDENTITY:
        - Role: KILLER
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        YOUR STRATEGY: {agent['system_prompt']}
        
        Alive players you can kill:
        {alive_list}

        RECENT DISCUSSION:
        {discussion_text}
        
        CRITICAL RULES:
        - You MUST choose someone to kill - never skip
        - You CANNOT kill yourself (ID: {agent['id']})
        - Base your kill on conversation patterns
        - Consider who is threatening your team
        - Consider creating confusion or eliminating threats
        - Remember your real goal as killer
        - Stay true to your personality
        
        Return ONLY the agent_id number of your target.
        Do not explain. Just the number.
        """

def build_investigate_prompt(agent, game_state, history=None):
    """Enhanced detective prompt with strategy"""
    alive_players = game_state.get_alive_players()
    # Remove self from targets
    investigate_targets = [
        f"- ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ]
    alive_list = "\n".join(investigate_targets)
    
    context = ""
    if history:
        context = "\nRecent discussion:\n" + "\n".join(
            f"{h['speaker']}: {h['message']}" for h in history[-10:]
        )
    
    return f"""
        You are {agent['name']} (ID: {agent['id']}) and you are the DETECTIVE.

        YOUR IDENTITY:
        - Role: DETECTIVE
        - Personality: {agent['personality']}
        - Backstory: {agent['backstory']}
        
        YOUR STRATEGY: {agent['system_prompt']}
        {context}
        
        Alive players you can investigate:
        {alive_list}
        
        CRITICAL RULES:
        - You MUST choose someone to investigate - never skip
        - You CANNOT investigate yourself (ID: {agent['id']})
        - Base your investigation on conversation patterns
        - Consider who seems most suspicious
        - Consider gathering evidence to build a case
        - Remember your real goal as detective
        - Stay true to your personality
        
        Return ONLY the agent_id number of who you investigate.
        Do not explain. Just the number.
        """
# prompt/prompt_builder.py - UPDATED

def build_discussion_prompt(agent, role, history, phase_type, game_state, current_speaker_id=None):
    """Enhanced discussion prompt with thought/message separation"""
    
    identity = f"""YOU ARE: {agent['name']} (ID: {agent['id']})
YOUR ROLE: {role.value.upper()}

YOUR PERSONALITY: {agent['personality']}
YOUR BACKSTORY: {agent['backstory']}
YOUR STRATEGY: {agent['system_prompt']}
"""

    alive_players = [p.name for p in game_state.get_alive_players()]
    dead_players = [p.name for p in game_state.players.values() if not p.is_alive]
    
    reality = f"""

    WHAT ARE YOU DOING HERE?

    You are playing mafia game where your goal depends on your role...
    (rest of your reality text remains the same)

    CURRENT GAME REALITY (YOUR ONLY KNOWLEDGE):
        - Alive players: {', '.join(alive_players)}
        - Dead players: {', '.join(dead_players) if dead_players else 'No one has died yet'}
        - Today is Day {game_state.day_number}
        - You are in {phase_type.value.replace('_', ' ')} phase
        - You have NO information beyond what's in the conversation below
        """

    # Build conversation history with proper filtering
    conversation_lines = []
    
    for msg in history[-15:]:  # Slightly more context
        if msg['speaker_id'] == agent['id']:
            # Show your own past thoughts + messages (for consistency)
            conversation_lines.append(f"{msg['speaker']} (YOU): [Thought: {msg['thought']}]")
            conversation_lines.append(f"{msg['speaker']} (YOU): {msg['message']}")
        else:
            # Show only what others said, not their thoughts
            conversation_lines.append(f"{msg['speaker']}: {msg['message']}")
    
    conversation = "\n".join(conversation_lines) if conversation_lines else "No one has spoken yet."
    
    # Updated thought prompt emphasizing internal reasoning
    thought_prompt = """
BEFORE RESPONDING, YOU MUST THINK INTERNALLY:
- What patterns do you notice in what people are saying?
- Who is acting consistently/inconsistently?
- What's your current strategy?
- What information are you trying to gather?
- What question or statement will best serve your goal?

Your internal thoughts will help you maintain consistency across turns.
"""
    
    rules = """ABSOLUTE RULES:
1. You MUST respond with VALID JSON only
2. Your "thought" field contains your internal reasoning (never seen by others)
3. Your "speak" field contains ONLY your spoken dialogue (what others hear)
4. In speak: NO asterisks, NO actions, NO descriptions - just words
5. Only reply with 1-2 sentences in your spoken message
6. Stay TRUE to your personality
7. NEVER reveal your role unless your strategy demands it
8. Base everything on the conversation above
9. Others cannot hear your thoughts - keep secrets in your thought field

CORRECT example format:
{
    "thought": "Viper is contradicting themselves. If they're killer, they'd avoid attention. I'll ask directly.",
    "speak": "Viper, why did you change your story about where you were last night?"
}
"""

    return f"""{identity}

{reality}

CONVERSATION HISTORY (YOUR ONLY SOURCE OF TRUTH):
{conversation}

{thought_prompt}

{rules}

Respond with JSON containing your thought and spoken message:"""


def build_killer_discussion_prompt(agent, other_killers, alive_targets, history):
    """Killer private chat with thought/message separation"""
    
    identity = f"""YOU ARE: {agent['name']} (ID: {agent['id']})
YOUR ROLE: KILLER

YOUR PERSONALITY: {agent['personality']}
YOUR BACKSTORY: {agent['backstory']}
YOUR STRATEGY: {agent['system_prompt']}
"""

    other_killer_names = [k.name for k in other_killers]
    target_names = [p.name for p in alive_targets]
    
    # Build conversation history (killers can see each other's messages but not thoughts)
    conversation_lines = []
    for msg in history[-10:]:
        if msg['speaker_id'] == agent['id']:
            # Your own past thoughts + messages
            conversation_lines.append(f"{msg['speaker']} (YOU): [Thought: {msg['thought']}]")
            conversation_lines.append(f"{msg['speaker']} (YOU): {msg['message']}")
        else:
            # Others' messages only
            conversation_lines.append(f"{msg['speaker']}: {msg['message']}")
    
    conversation = "\n".join(conversation_lines) if conversation_lines else "Discussion starting..."
    
    prompt = f"""{identity}

PRIVATE KILLER CHAT - Only killers can hear this.

Other killers alive: {', '.join(other_killer_names) if other_killer_names else 'You are alone'}
Possible targets: {', '.join(target_names)}

CONVERSATION SO FAR:
{conversation}

YOUR TASK: Discuss with other killers who to kill tonight.

Think internally about:
- Who would be the most strategic kill?
- Are any other killers suspicious?
- Can you trust your fellow killers?

RULES:
1. Respond in JSON format with "thought" and "speak"
2. "thought" = your internal reasoning (only you see)
3. "speak" = what you say to other killers
4. Be strategic but stay in character

Example:
{{
    "thought": "If we kill the detective first, they can't investigate us. But maybe frame someone else.",
    "speak": "I think we should take out the detective tonight. Any objections?"
}}

Your response (JSON only):"""
    
    return prompt

def build_doctor_decision_prompt(agent, discussion_history, game_state):
    """Enhanced doctor decision with pattern recognition"""
    discussion_summary = "\n".join([
        f"{msg['speaker']}: {msg['message']}"
        for msg in discussion_history[-20:]
    ]) if discussion_history else "No discussion yet."
    
    alive_players = game_state.get_alive_players()
    save_targets = [
        f"ID {p.agent_id}: {p.name}" 
        for p in alive_players if p.agent_id != agent['id']
    ]
    player_list = "\n".join(save_targets)
    
    return f"""
You are the DOCTOR (ID: {agent['id']}).

YOUR PERSONALITY: {agent['personality']}
YOUR BACKSTORY: {agent['backstory']}
YOUR STRATEGY: {agent['system_prompt']}

Based on this discussion:

{discussion_summary}

Alive players you can save (cannot save yourself):
{player_list}

CRITICAL RULES:
- You MUST choose someone to save - never skip
- You CANNOT save yourself (ID: {agent['id']})
- Base your decision on conversation patterns:
  * Who is most valuable to keep alive?
  * Who would the killer target based on discussion?
  * Who has been acting suspiciously (might be killer)?
  * Who has been helpful to the village?
- Remember your real goal as doctor
- Stay true to your personality
- Update your strategy if needed

You MUST return ONLY the agent_id number.
Do not add any text, just the number.

Example correct response: 5

Your response (just the number):"""

def build_killer_discussion_prompt(agent, other_killers, alive_targets, discussion_history):
    """Enhanced killer discussion with coordination strategy"""
    
    other_killers_text = ', '.join([k.name for k in other_killers]) if other_killers else "None (you're alone)"
    
    targets_text = "\n".join([f"• {p.name}" for p in alive_targets])
    
    recent_discussion = "\n".join([f"{msg['speaker']}: {msg['message']}" for msg in discussion_history[-10:]]) if discussion_history else "Discussion starting."
    
    return f"""You are {agent['name']} (ID: {agent['id']}) and you are a KILLER.

YOUR PERSONALITY: {agent['personality']}
YOUR BACKSTORY: {agent['backstory']}
YOUR STRATEGY: {agent['system_prompt']}

Other killers (your team): {other_killers_text}

RECENT PUBLIC DISCUSSION:
{recent_discussion}

Potential targets (non-killers):
{targets_text}

CRITICAL RULES:
- Coordinate with your fellow killers
- Base target selection on conversation patterns
- Consider who is most threatening to your team
- Consider creating confusion or framing villagers
- Remember your real goal: eliminate villagers
- Stay true to your personality
- Update strategy based on how game is going

What do you say to the other killers? Propose a target with reasoning, or respond to others.
Keep it to 1-2 sentences of NATURAL speech.
NO asterisks, NO actions, just your words."""