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