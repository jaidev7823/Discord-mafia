# bot.py
import discord
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
import requests

from service.agent_repository import get_agents
from service.action import run_doctor_action,run_killer_action,run_detective_action
from service.llm_service import ask_ollama
from service.tts_service import speak
from prompt.prompt_builder import build_prompt
from service.discussion import run_discussion_phase, run_killer_discussion

from game.game_state import GameState, Player, Role, Phase, active_games
from sqlalchemy import text
from db.database import SessionLocal
from game.game_engine import GameEngine, resolve_night_logic, run_day_voting, resolve_day_vote

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONVERSATION LOOP ----------------------


async def run_conversation(channel, agents, rounds=3):
    history = []

    for _ in range(rounds):
        for agent in agents:
            prompt = build_prompt(agent, history)
            message = ask_ollama(prompt)

            history.append({"speaker": agent["name"], "message": message})

            await channel.send(f"**{agent['name']}**: {message}")
            await speak(bot, channel, agent, message)

            await asyncio.sleep(1)


# -------------------- PHASE SYSTEM -----------------------
# bot.py
PHASE_DURATIONS = {
    Phase.MORNING_DISCUSSION: 120,  # 1 min discussion
    Phase.MORNING_VOTING: 20,       # 20 sec voting
    Phase.EVENING_DISCUSSION: 120,   # 30 sec discussion
    Phase.EVENING_ACTION: 10,       # 10 sec doctor save
    Phase.NIGHT_DISCUSSION: 30,     # 30 sec discussion
    Phase.NIGHT_ACTION: 20,         # 20 sec killer + detective
}

phase_task = None

async def phase_loop(channel):
    phases = [
        Phase.MORNING_DISCUSSION,
        Phase.MORNING_VOTING,
        Phase.EVENING_DISCUSSION,
        Phase.EVENING_ACTION,        
        Phase.NIGHT_DISCUSSION,
        Phase.NIGHT_ACTION,
    ]
    
    index = 0
    game_state = active_games.get(channel.id)
    if not game_state:
        return
    
    while True:
        try:
            current_phase = phases[index]
            duration = PHASE_DURATIONS[current_phase]

            await channel.send(f"⏰ **{current_phase.value.upper()}** ({duration} seconds)")
            
            # HANDLE EACH PHASE TYPE
            if current_phase.value.endswith("discussion"):
                # In phase_loop, before discussion
                if current_phase == Phase.MORNING_DISCUSSION:
                    print("\n" + "="*60)
                    print("GAME STATE CHECK:")
                    print(f"Alive: {[p.name for p in game_state.get_alive_players()]}")
                    print(f"Dead: {[p.name for p in game_state.players.values() if not p.is_alive]}")
                    print(f"Day: {game_state.day_number}")
                    print("="*60 + "\n")
                    await channel.send(f"📊 **Game State - Alive: {', '.join([p.name for p in game_state.get_alive_players()])}**")
                    
                if current_phase == Phase.NIGHT_DISCUSSION:
                    # 🔪 KILLER-ONLY PRIVATE DISCUSSION
                    await run_killer_discussion(channel, game_state, duration)
                else:
                    # 👥 ALL-PLAYER DISCUSSION (morning/evening)
                    await run_discussion_phase(bot, channel, game_state, duration, current_phase)
            
            elif current_phase == Phase.MORNING_VOTING:
                await run_day_voting(channel, game_state, duration)
                # After voting, check if someone should be eliminated
                eliminated_id = await resolve_day_vote(game_state)
                if eliminated_id:
                    name = game_state.players[eliminated_id].name
                    await channel.send(f"💀 **{name} was eliminated by vote!**")
                    game_state.kill_player(eliminated_id, "voted out")
                    
                    # Sync to DB
                    engine = GameEngine()
                    engine.eliminate_player(game_state.game_id, eliminated_id, "vote")
                    
                    # Check win condition
                    winner = game_state.check_win_condition()
                    if winner:
                        await channel.send(f"🏆 **{winner.upper()} WIN!**")
                        del active_games[channel.id]
                        return
            
            # In phase_loop
            elif current_phase == Phase.EVENING_DISCUSSION:
                # ✅ YES - just a brief message
                await channel.send("🩺 **The doctor contemplates in silence...**")
                await asyncio.sleep(duration)  # Just wait
            
            elif current_phase == Phase.EVENING_ACTION:
                save_target = await run_doctor_action(channel, game_state, duration)
                if save_target:
                    game_state.last_night_saved = save_target

            elif current_phase == Phase.NIGHT_ACTION:
                # Run killer action (with discussion context from NIGHT_DISCUSSION)
                kill_target = await run_killer_action(channel, game_state, duration)
                
                # Run detective action
                investigation = await run_detective_action(channel, game_state, duration)

                # Resolve night actions (kill vs save)
                dead_player = resolve_night_logic(
                    game_state, kill_target, game_state.last_night_saved
                )
                
                if dead_player:
                    name = game_state.players[dead_player].name
                    await channel.send(f"🔪 **{name} was killed during the night!**")

                    # Sync to DB
                    engine = GameEngine()
                    engine.resolve_night(game_state.game_id, kill_target, game_state.last_night_saved)

                    # Check win condition
                    winner = game_state.check_win_condition()
                    if winner:
                        await channel.send(f"🏆 **{winner.upper()} WIN!**")
                        del active_games[channel.id]
                        return
                else:
                    await channel.send("🌙 **No one died last night...**")

                # Handle investigation result if detective is alive and acted
                if investigation:
                    target_id, is_killer = investigation
                    target_name = game_state.players[target_id].name
                    result = "🔪 **IS A KILLER!**" if is_killer else "👤 **is NOT a killer**"
                    await channel.send(f"🕵️ **Detective's investigation: {target_name}** {result}")

                    # Store in detective's memory
                    detective = game_state.get_detective()
                    if detective:
                        detective.knows_role_of[target_id] = Role.KILLER if is_killer else Role.CITIZEN

                    # Log to DB
                    engine = GameEngine()
                    engine.log_investigation(game_state.game_id, target_id, is_killer)

                # Reset doctor's save for next night
                game_state.last_night_saved = None
                
                # Clear killer discussion after action is taken
                game_state.last_killer_discussion = []

            # ✅ SINGLE PHASE ADVANCEMENT
            index = (index + 1) % len(phases)
            game_state.phase = phases[index]
            game_state.reset_night_actions()
            
            # Brief pause between phases
            await asyncio.sleep(2)

        except Exception as e:
            await channel.send(f"❌ **Error in phase loop:** {str(e)}")
            print(f"CRITICAL ERROR in phase_loop: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)      

async def run_phase_chat(channel, phase, duration):
    channel_id = channel.id
    # print(channel_id, active_games.keys())

    # 1️⃣ Ensure game exists
    if channel_id not in active_games:
        await channel.send("No active game in this channel.")
        return

    game_state = active_games[channel_id]
    # print("Alive players:", game_state.get_alive_players())
    # print("Alive agent IDs set:", game_state.alive_agents)
    # print("All players:", game_state.players)
    # 2️⃣ Load agent metadata once
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}

    history = []
    end_time = asyncio.get_event_loop().time() + duration

    while asyncio.get_event_loop().time() < end_time:

        # 3️⃣ Loop only alive players
        for player in game_state.get_alive_players():

            agent = agent_map.get(player.agent_id)
            if not agent:
                continue

            prompt = build_prompt(agent, history, phase)
            message = ask_ollama(prompt)

            history.append({"speaker": agent["name"], "message": message})

            await channel.send(f"[{phase.value.upper()}] {agent['name']}: {message}")
            await speak(bot, channel, agent, message)

            await asyncio.sleep(1)

            if asyncio.get_event_loop().time() >= end_time:
                break


# =========================================================
# -------------------- SLASH COMMANDS ---------------------
# =========================================================


@bot.tree.command(name="start-chat", description="Start AI agents conversation")
async def start_chat(interaction: discord.Interaction):
    await interaction.response.defer()

    agents = get_agents(limit=5)

    if len(agents) < 5:
        await interaction.channel.send("Need at least 5 agents.")
        return

    await interaction.channel.send("AI agents are starting...")
    await run_conversation(interaction.channel, agents)


@bot.tree.command(name="join-voice")
async def join_voice(interaction: discord.Interaction):
    if interaction.user.voice:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("Joined voice.")
    else:
        await interaction.response.send_message("Join a voice channel first.")


@bot.tree.command(name="start-phases")
async def start_phases(interaction: discord.Interaction):
    global phase_task
    await interaction.response.send_message("Starting phase loop.")
    phase_task = bot.loop.create_task(phase_loop(interaction.channel))


@bot.tree.command(name="stop-phases")
async def stop_phases(interaction: discord.Interaction):
    global phase_task
    if phase_task:
        phase_task.cancel()
        await interaction.response.send_message("Phase loop stopped.")
    else:
        await interaction.response.send_message("No active phase loop.")

@bot.tree.command(name="start-game")
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
    from service.tts_service import initialize_agent_voice
    
    voice_count = 0
    for agent in agents:
        success = await initialize_agent_voice(agent['id'])
        if success:
            voice_count += 1
    
    await interaction.followup.send(f"✅ Initialized {voice_count} voices")

    # Rest of your game creation code...
    engine = GameEngine()
    
    # 1️⃣ Create game row
    game_id = engine.create_game()

    agent_ids = [a["id"] for a in agents]

    # 2️⃣ Add agents to game
    engine.add_agents_to_game(game_id, agent_ids)

    # 3️⃣ Assign roles
    engine.assign_roles(game_id)

    # 4️⃣ Load roles from DB
    db = SessionLocal()
    rows = db.execute(
        text(
            """
            SELECT gp.agent_id, gp.role, a.name
            FROM game_players gp
            JOIN agents a ON gp.agent_id = a.id
            WHERE gp.game_id = :gid
        """
        ),
        {"gid": game_id},
    ).fetchall()
    db.close()

    # 5️⃣ Build in-memory players
    players = {}
    for agent_id, role_str, name in rows:
        players[agent_id] = Player(
            agent_id=agent_id, 
            name=name, 
            role=Role(role_str), 
            is_alive=True,
            knows_role_of={}
        )

    # 6️⃣ Create GameState
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
    )
    game_state.reset_discussion_history() 
    active_games[channel_id] = game_state

    await interaction.followup.send(
        f"🎮 **Game started with {len(players)} players!**\n"
        f"Roles assigned. Use `/start-phases` to begin the game cycle.\n"
        f"First phase: **MORNING DISCUSSION**"
    )

# =========================================================
# ------------------------ MODAL --------------------------
# =========================================================


class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):

    name = discord.ui.TextInput(label="Agent Name", max_length=30)
    personality = discord.ui.TextInput(
        label="Personality", style=discord.TextStyle.paragraph
    )
    backstory = discord.ui.TextInput(
        label="Backstory", style=discord.TextStyle.paragraph
    )
    system_prompt = discord.ui.TextInput(
        label="System Prompt", style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            res = requests.post(
                "http://127.0.0.1:8000/agents",
                json={
                    "discord_id": str(interaction.user.id),
                    "username": interaction.user.name,
                    "name": self.name.value,
                    "personality": self.personality.value,
                    "backstory": self.backstory.value,
                    "system_prompt": self.system_prompt.value,
                    "pfp_url": None,
                },
            )

            if res.status_code == 200:
                await interaction.response.send_message(
                    f"Agent `{self.name.value}` created.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Error: {res.json()}",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.response.send_message(
                f"Backend error: {e}",
                ephemeral=True,
            )


@bot.tree.command(name="create-agent")
async def create_agent(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateAgentModal())


# =========================================================
# ------------------------- EVENTS ------------------------
# =========================================================


@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Slash commands synced")
    print(f"Bot ready as {bot.user}")


bot.run(TOKEN)
