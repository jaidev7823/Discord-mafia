# bot/phases.py
import asyncio
import discord
from game.game_state import Phase, Role, active_games
from game.game_engine import GameEngine, resolve_night_logic, resolve_day_vote, run_day_voting
from service.discussion import run_discussion_phase, run_killer_discussion
from service.action import run_doctor_action, run_killer_action, run_detective_action
from service.llm_service import ask_ollama
from service.tts_service import speak
from prompt.prompt_builder import build_prompt

async def run_conversation(bot, channel, agents, rounds=3):
    """Simple conversation between agents (non-game chat)"""
    history = []
    for _ in range(rounds):
        for agent in agents:
            prompt = build_prompt(agent, history)
            message = ask_ollama(prompt)
            history.append({"speaker": agent["name"], "message": message})
            await channel.send(f"**{agent['name']}**: {message}")
            await speak(bot, channel, agent, message)
            await asyncio.sleep(1)

# Phase configurations
PHASE_CONFIG = {
    Phase.MORNING_DISCUSSION: {
        "duration": 120,
        "handler": "morning_discussion",
        "desc": "☀️ Morning Discussion"
    },
    Phase.MORNING_VOTING: {
        "duration": 20,
        "handler": "morning_voting", 
        "desc": "🗳️ Morning Voting"
    },
    Phase.EVENING_DISCUSSION: {
        "duration": 120,
        "handler": "evening_discussion",
        "desc": "🌆 Evening Discussion"
    },
    Phase.EVENING_ACTION: {
        "duration": 10,
        "handler": "evening_action",
        "desc": "🩺 Doctor's Choice"
    },
    Phase.NIGHT_DISCUSSION: {
        "duration": 30,
        "handler": "night_discussion",
        "desc": "🌙 Killer's Council"
    },
    Phase.NIGHT_ACTION: {
        "duration": 20,
        "handler": "night_action",
        "desc": "🔪 Night Actions"
    }
}

PHASE_ORDER = [
    Phase.MORNING_DISCUSSION,
    Phase.MORNING_VOTING,
    Phase.EVENING_DISCUSSION,
    Phase.EVENING_ACTION,
    Phase.NIGHT_DISCUSSION,
    Phase.NIGHT_ACTION
]

phase_task = None

class PhaseHandlers:
    """Collection of phase handler methods"""
    
    @staticmethod
    async def morning_discussion(bot, channel, game_state, duration):
        """Handle morning discussion"""
        if game_state.last_night_kill_attempt:
            killed = game_state.players.get(game_state.last_night_kill_attempt)
            if killed and not killed.is_alive:
                await channel.send(f"💀 **{killed.name} was killed last night!**")
        else:
            await channel.send("🌙 **Everyone survived the night!**")
        
        # Show game state
        alive_names = [p.name for p in game_state.get_alive_players()]
        await channel.send(f"📊 **Alive: {', '.join(alive_names)}**")
        
        await run_discussion_phase(bot, channel, game_state, duration, Phase.MORNING_DISCUSSION)
    
    @staticmethod
    async def morning_voting(bot, channel, game_state, duration):
        """Handle morning voting"""
        await run_day_voting(channel, game_state, duration)
        eliminated_id = await resolve_day_vote(game_state)
        
        if eliminated_id:
            name = game_state.players[eliminated_id].name
            await channel.send(f"💀 **{name} was eliminated by vote!**")
            game_state.kill_player(eliminated_id, "voted out")
            
            engine = GameEngine()
            engine.eliminate_player(game_state.game_id, eliminated_id, "vote")
            
            return game_state.check_win_condition()
        return None
    
    @staticmethod
    async def evening_discussion(bot, channel, game_state, duration):
        """Handle evening discussion"""
        await channel.send("🩺 **Evening falls... The doctor listens carefully...**")
        await run_discussion_phase(bot, channel, game_state, duration, Phase.EVENING_DISCUSSION)
    
    @staticmethod
    async def evening_action(bot, channel, game_state, duration):
        """Handle doctor's action"""
        save_target = await run_doctor_action(channel, game_state, duration)
        if save_target:
            game_state.last_night_saved = save_target
            await channel.send(f"💊 Doctor will protect someone tonight")
    
    @staticmethod
    async def night_discussion(bot, channel, game_state, duration):
        """Handle killer's private discussion"""
        await run_killer_discussion(channel, game_state, duration)
    
    @staticmethod
    async def night_action(bot, channel, game_state, duration):
        """Handle night actions (killer + detective)"""
        kill_target = await run_killer_action(channel, game_state, duration)
        investigation = await run_detective_action(channel, game_state, duration)
        
        # Resolve night actions
        dead_player = resolve_night_logic(game_state, kill_target, game_state.last_night_saved)
        engine = GameEngine()
        
        if dead_player:
            name = game_state.players[dead_player].name
            await channel.send(f"🔪 **{name} was killed during the night!**")
            engine.resolve_night(game_state.game_id, kill_target, game_state.last_night_saved)
        else:
            await channel.send("🌙 **No one died last night...**")
        
        # Handle investigation
        if investigation:
            target_id, is_killer = investigation
            target_name = game_state.players[target_id].name
            result = "🔪 **IS A KILLER!**" if is_killer else "👤 **is NOT a killer**"
            await channel.send(f"🕵️ **Detective's investigation: {target_name}** {result}")
            
            detective = game_state.get_detective()
            if detective:
                detective.knows_role_of[target_id] = Role.KILLER if is_killer else Role.CITIZEN
            
            engine.log_investigation(game_state.game_id, target_id, is_killer)
        
        # Reset night state
        game_state.last_night_saved = None
        game_state.last_killer_discussion = []
        
        return game_state.check_win_condition()

async def phase_loop(bot, channel):
    """Main game phase loop - simplified"""
    global phase_task
    
    game_state = active_games.get(channel.id)
    if not game_state:
        return
    
    handlers = PhaseHandlers()
    current_idx = PHASE_ORDER.index(game_state.phase) if game_state.phase in PHASE_ORDER else 0
    
    while True:
        try:
            phase = PHASE_ORDER[current_idx]
            config = PHASE_CONFIG[phase]
            handler_name = config["handler"]
            
            # Announce phase
            await channel.send(f"⏰ **{config['desc']}** ({config['duration']} seconds)")
            
            # Get handler method
            handler = getattr(handlers, handler_name)
            
            # Execute phase
            winner = await handler(bot, channel, game_state, config["duration"])
            
            # Check win condition
            if winner or game_state.check_win_condition():
                await end_game(channel, game_state, winner)
                return
            
            # Move to next phase
            current_idx = (current_idx + 1) % len(PHASE_ORDER)
            game_state.phase = PHASE_ORDER[current_idx]
            
            # Increment day after night action
            if phase == Phase.NIGHT_ACTION:
                game_state.day_number += 1
                game_state.reset_night_actions()
            
            await asyncio.sleep(2)
            
        except Exception as e:
            await channel.send(f"❌ **Error:** {str(e)}")
            print(f"Phase loop error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)

async def end_game(channel, game_state, winner=None):
    """Handle game end"""
    winner = winner or game_state.check_win_condition()
    await channel.send(f"🏆 **GAME OVER! {winner.upper()} WIN!** 🏆")
    
    # Show final roles
    await channel.send("**Final Roles:**")
    for player in game_state.players.values():
        status = "Alive" if player.is_alive else "Dead"
        await channel.send(f"  • {player.name}: {player.role.value} ({status})")
    
    del active_games[channel.id]

def setup_phase_commands(bot):
    """Setup phase commands"""
    
    @bot.tree.command(name="start-phases", description="Start the game phase loop")
    async def start_phases(interaction: discord.Interaction):
        global phase_task
        if interaction.channel.id not in active_games:
            await interaction.response.send_message("No active game in this channel!")
            return
        
        await interaction.response.send_message("🎮 Starting phase loop...")
        phase_task = bot.loop.create_task(phase_loop(bot, interaction.channel))

    @bot.tree.command(name="stop-phases", description="Stop the game phase loop")
    async def stop_phases(interaction: discord.Interaction):
        global phase_task
        if phase_task:
            phase_task.cancel()
            phase_task = None
            await interaction.response.send_message("⏹️ Phase loop stopped.")
        else:
            await interaction.response.send_message("No active phase loop.")

__all__ = ['phase_loop', 'run_conversation', 'setup_phase_commands']