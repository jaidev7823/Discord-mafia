# bot/commands.py
import discord
from discord.ext import commands
from service.agent_repository import get_agents
from service.tts_service import initialize_agent_voice
from game.game_state import GameState, Player, Role, Phase, active_games
from game.game_engine import GameEngine
from db.database import SessionLocal
from sqlalchemy import text
from .modals import CreateAgentModal
from .phases import run_conversation  # Removed phase_loop import

def setup_commands(bot):
    """Setup all slash commands"""
    
    @bot.tree.command(name="start-chat", description="Start AI agents conversation")
    async def start_chat(interaction: discord.Interaction):
        await interaction.response.defer()
        agents = get_agents(limit=5)
        if len(agents) < 5:
            await interaction.followup.send("Need at least 5 agents.")
            return
        await interaction.followup.send("AI agents are starting...")
        await run_conversation(bot, interaction.channel, agents)

    @bot.tree.command(name="start-game", description="Start a new Mafia game")
    async def start_game(interaction: discord.Interaction):
        await interaction.response.defer()
        
        channel_id = interaction.channel.id

        # Prevent duplicate game
        if channel_id in active_games:
            await interaction.followup.send("Game already running in this channel.")
            return

        # Load agents from DB
        agents = get_agents(limit=10)

        if len(agents) < 3:
            await interaction.followup.send("Need at least 3 agents.")
            return

        # Initialize voices for these agents
        await interaction.followup.send("🎙️ Initializing agent voices...")
        voice_count = 0
        for agent in agents:
            success = await initialize_agent_voice(agent['id'])
            if success:
                voice_count += 1
        
        await interaction.followup.send(f"✅ Initialized {voice_count} voices")

        # Create game
        engine = GameEngine()
        game_id = engine.create_game()
        agent_ids = [a["id"] for a in agents]
        engine.add_agents_to_game(game_id, agent_ids)
        engine.assign_roles(game_id)

        # Load roles from DB
        db = SessionLocal()
        rows = db.execute(
            text("""
                SELECT gp.agent_id, gp.role, a.name
                FROM game_players gp
                JOIN agents a ON gp.agent_id = a.id
                WHERE gp.game_id = :gid
            """),
            {"gid": game_id},
        ).fetchall()
        db.close()

        # Build in-memory players
        players = {}
        for agent_id, role_str, name in rows:
            players[agent_id] = Player(
                agent_id=agent_id, 
                name=name, 
                role=Role(role_str), 
                is_alive=True,
                knows_role_of={}
            )

        # Create GameState
        game_state = GameState(
            game_id=game_id,
            phase=Phase.MORNING_DISCUSSION,
            players=players,
            alive_agents=set(players.keys()),
            dead_agents=set(),
            day_number=1,
            last_discussion=[],
            last_killer_discussion=[],
            last_night_kill_attempt=None,
            last_night_saved=None,
            current_votes={},
            game_over=False,
            winner=None
        )
        game_state.reset_discussion_history() 
        active_games[channel_id] = game_state

        await interaction.followup.send(
            f"🎮 **Game started with {len(players)} players!**\n"
            f"Roles assigned. Use `/start-phases` to begin the game cycle.\n"
            f"First phase: **MORNING DISCUSSION**"
        )

    @bot.tree.command(name="create-agent", description="Create a new AI agent")
    async def create_agent(interaction: discord.Interaction):
        await interaction.response.send_modal(CreateAgentModal())