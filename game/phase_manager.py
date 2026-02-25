# game/phase_manager.py
from typing import Dict, Optional
import asyncio
import logging
from .game_state import GameState, Phase, Role
from service.discussion import run_discussion_phase, run_killer_discussion
from service.action import run_doctor_action, run_killer_action, run_detective_action
from game.game_engine import resolve_night_logic, resolve_day_vote, run_day_voting

logger = logging.getLogger(__name__)

class PhaseResult:
    """Result of a phase execution"""
    def __init__(self, next_phase: Phase, game_over: bool = False, winner: Optional[str] = None):
        self.next_phase = next_phase
        self.game_over = game_over
        self.winner = winner

class PhaseManager:
    def __init__(self, game_engine, llm_service, tts_service, prompt_builder, bot):
        self.game_engine = game_engine
        self.llm = llm_service
        self.tts = tts_service
        self.prompt_builder = prompt_builder
        self.bot = bot
        self.phase_tasks: Dict[int, asyncio.Task] = {}  # channel_id -> phase task
        
        # Define the phase sequence
        self.phase_sequence = [
            Phase.MORNING_DISCUSSION,
            Phase.MORNING_VOTING,
            Phase.EVENING_DISCUSSION,
            Phase.EVENING_ACTION,
            Phase.NIGHT_DISCUSSION,
            Phase.NIGHT_ACTION
        ]
        
    async def run_phase_cycle(self, channel_id: int, game_state: GameState, bot_context):
        """Main phase loop - runs continuously until game ends"""
        try:
            # Find starting index
            current_index = self.phase_sequence.index(game_state.phase)
            
            while not game_state.game_over:
                current_phase = game_state.phase
                logger.info(f"Running phase: {current_phase.value} for game {channel_id}")
                
                # Execute the current phase
                await self._execute_phase(channel_id, current_phase, game_state, bot_context)
                
                # Check win condition after each phase
                winner = game_state.check_win_condition()
                if winner:
                    await self._end_game(channel_id, game_state, winner, bot_context)
                    break
                
                # Move to next phase in sequence
                current_index = (current_index + 1) % len(self.phase_sequence)
                game_state.phase = self.phase_sequence[current_index]
                
                # Increment day number when we complete a full cycle (after NIGHT_ACTION)
                if current_phase == Phase.NIGHT_ACTION:
                    game_state.day_number += 1
                
                # Small delay between phases
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            logger.info(f"Phase cycle cancelled for channel {channel_id}")
        except Exception as e:
            logger.error(f"Error in phase cycle: {e}", exc_info=True)
            await bot_context.send(f"❌ Error in game: {str(e)}")
            
    async def _execute_phase(self, channel_id: int, phase: Phase, game_state: GameState, bot_context):
        """Execute a specific phase"""
        
        # Phase durations (you can adjust these)
        durations = {
            Phase.MORNING_DISCUSSION: 60,
            Phase.MORNING_VOTING: 30,
            Phase.EVENING_DISCUSSION: 30,
            Phase.EVENING_ACTION: 15,
            Phase.NIGHT_DISCUSSION: 45,
            Phase.NIGHT_ACTION: 20
        }
        
        duration = durations.get(phase, 30)
        
        # Phase descriptions
        descriptions = {
            Phase.MORNING_DISCUSSION: "☀️ **MORNING DISCUSSION** - Everyone discusses what happened last night",
            Phase.MORNING_VOTING: "🗳️ **MORNING VOTING** - Time to vote someone out",
            Phase.EVENING_DISCUSSION: "🌆 **EVENING DISCUSSION** - Final discussions before night",
            Phase.EVENING_ACTION: "🩺 **EVENING ACTION** - Doctor makes their choice",
            Phase.NIGHT_DISCUSSION: "🌙 **NIGHT DISCUSSION** - Killers plan in secret",
            Phase.NIGHT_ACTION: "🔪 **NIGHT ACTION** - Killers and detective act"
        }
        
        # Announce phase start
        await bot_context.send(f"⏰ **{descriptions[phase]}** ({duration} seconds)")
        
        # Phase-specific logic
        if phase == Phase.MORNING_DISCUSSION:
            # Announce night results first
            if game_state.last_night_kill_attempt:
                killed_player = game_state.players.get(game_state.last_night_kill_attempt)
                if killed_player and not killed_player.is_alive:
                    await bot_context.send(f"💀 **{killed_player.name} was killed last night!**")
            else:
                await bot_context.send("🌙 **Everyone survived the night!**")
            
            # Run discussion
            await run_discussion_phase(self.bot, bot_context.channel, game_state, duration, phase)
            
        elif phase == Phase.MORNING_VOTING:
            await run_day_voting(bot_context.channel, game_state, duration)
            # Resolve votes
            eliminated_id = await resolve_day_vote(game_state)
            if eliminated_id:
                eliminated = game_state.players[eliminated_id]
                await bot_context.send(f"🔨 **{eliminated.name} was eliminated by vote!**")
                game_state.kill_player(eliminated_id, "voted out")
                self.game_engine.eliminate_player(game_state.game_id, eliminated_id, "vote")
                
        elif phase == Phase.EVENING_DISCUSSION:
            # Regular discussion with everyone
            await run_discussion_phase(self.bot, bot_context.channel, game_state, duration, phase)
            
        elif phase == Phase.EVENING_ACTION:
            # Doctor action
            save_target = await run_doctor_action(bot_context.channel, game_state, duration)
            if save_target:
                game_state.last_night_saved = save_target
                await bot_context.send(f"💊 Doctor will protect someone tonight")
                
        elif phase == Phase.NIGHT_DISCUSSION:
            # Killer-only private discussion
            await run_killer_discussion(bot_context.channel, game_state, duration)
            
        elif phase == Phase.NIGHT_ACTION:
            # Killer action
            kill_target = await run_killer_action(bot_context.channel, game_state, duration)
            game_state.last_night_kill_attempt = kill_target
            
            # Detective action
            investigation = await run_detective_action(bot_context.channel, game_state, duration)
            
            # Resolve night actions
            dead_player = resolve_night_logic(
                game_state, kill_target, game_state.last_night_saved
            )
            
            if dead_player:
                dead_name = game_state.players[dead_player].name
                await bot_context.send(f"🔪 **{dead_name} was killed during the night!**")
                self.game_engine.resolve_night(game_state.game_id, kill_target, game_state.last_night_saved)
            
            # Handle investigation result
            if investigation:
                target_id, is_killer = investigation
                target_name = game_state.players[target_id].name
                result = "🔪 **IS A KILLER!**" if is_killer else "👤 **is NOT a killer**"
                await bot_context.send(f"🕵️ **Detective's investigation: {target_name}** {result}")
                
                # Store in game state for detective's memory
                detective = game_state.get_detective()
                if detective:
                    if target_id not in detective.knows_role_of:
                        detective.knows_role_of[target_id] = Role.KILLER if is_killer else Role.CITIZEN
            
            # Reset for next night
            game_state.last_night_saved = None
            game_state.last_killer_discussion = []
    

    async def _end_game(self, channel_id: int, game_state: GameState, winner: str, bot_context):
        """Handle game end"""
        game_state.game_over = True
        game_state.winner = winner
        await bot_context.send(f"🎮 **GAME OVER!** The **{winner.upper()}** win! 🎮")

        # Show final results
        alive_players = game_state.get_alive_players()
        if alive_players:
            await bot_context.send("**Survivors:**")
            for player in alive_players:
                await bot_context.send(f"  • {player.name} ({player.role.value})")

        # Show all players and their roles
        await bot_context.send("**Final Roles:**")
        for player in game_state.players.values():
            status = "Alive" if player.is_alive else "Dead"
            await bot_context.send(f"  • {player.name}: {player.role.value} ({status})")

        # Clean up
        if channel_id in self.phase_tasks:
            self.phase_tasks[channel_id].cancel()
            del self.phase_tasks[channel_id]

        # Remove from active games
        from game.game_state import active_games
        if channel_id in active_games:
            del active_games[channel_id]