# service/emotion_engine.py
from game.game_state import Role, Phase  # Add this import!

def get_emotion_for_player(player, game_state, phase, message):
    """
    Determine emotion based on game state
    """
    if player.role == Role.KILLER:
        if phase == Phase.NIGHT_DISCUSSION:
            return "whisper"
        elif hasattr(game_state, 'current_votes') and player.agent_id in game_state.current_votes.values():
            return "angry"  # Being voted for
        else:
            return "neutral"
            
    elif player.role == Role.DOCTOR:
        if phase == Phase.EVENING_ACTION:
            return "thoughtful"
        else:
            return "neutral"
            
    elif player.role == Role.DETECTIVE:
        if phase == Phase.MORNING_DISCUSSION:
            return "suspicious"
        else:
            return "neutral"
            
    # Check if they're dead (about to die)
    if not player.is_alive:
        return "scared"
        
    return "neutral"