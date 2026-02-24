# game/game_engine.py
import random
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import SessionLocal
from sqlalchemy import bindparam
import asyncio

# IMPORT THE MODELS!
from db.models import Vote, AgentMemory  # Add this line!

from prompt.prompt_builder import build_vote_prompt
from service.agent_repository import get_agents
from service.llm_service import ask_ollama

# Fix the circular import - remove this line
# from game.game_engine import GameEngine  <- THIS CAUSES CIRCULAR IMPORT!

def resolve_night_logic(game_state, killer_target, doctor_target):
    if killer_target is None:
        return None

    if killer_target == doctor_target:
        return None  # saved

    game_state.kill_player(killer_target, "killed")
    return killer_target

class GameEngine:
    # -------------------------
    # 1️⃣ Create Game
    # -------------------------
    def create_game(self):
        db: Session = SessionLocal()
        try:
            db.execute(
                text("INSERT INTO games (status, phase, day_number) VALUES ('running', 'night', 1)")
            )
            db.commit()

            game_id = db.execute(
                text("SELECT last_insert_rowid()")
            ).scalar()

            return game_id
        finally:
            db.close()

    # -------------------------
    # 2️⃣ Add Agents To Game
    # -------------------------
    def add_agents_to_game(self, game_id, agent_ids):
        db: Session = SessionLocal()
        try:
            # Validate agents exist
            query = text(
                "SELECT id FROM agents WHERE id IN :ids"
            ).bindparams(
                bindparam("ids", expanding=True)
            )

            existing = db.execute(
                query,
                {"ids": agent_ids}
            ).fetchall()

            existing_ids = [row[0] for row in existing]

            if len(existing_ids) != len(agent_ids):
                raise Exception("One or more agent IDs do not exist")

            for agent_id in agent_ids:
                db.execute(
                    text("""
                        INSERT INTO game_players (game_id, agent_id, role, is_alive)
                        VALUES (:game_id, :agent_id, 'citizen', 1)
                    """),
                    {"game_id": game_id, "agent_id": agent_id}
                )

            db.commit()
        finally:
            db.close()

    # -------------------------
    # 3️⃣ Assign Roles
    # -------------------------
    def assign_roles(self, game_id):
        db: Session = SessionLocal()
        try:
            players = db.execute(
                text("SELECT id FROM game_players WHERE game_id = :game_id"),
                {"game_id": game_id}
            ).fetchall()

            player_ids = [p[0] for p in players]

            if len(player_ids) < 3:
                raise Exception("Minimum 3 players required")

            killer = random.choice(player_ids)
            remaining = [p for p in player_ids if p != killer]

            doctor = random.choice(remaining)
            remaining.remove(doctor)

            detective = random.choice(remaining)

            roles = {
                killer: "killer",
                doctor: "doctor",
                detective: "detective"
            }

            for pid, role in roles.items():
                db.execute(
                    text("UPDATE game_players SET role = :role WHERE id = :id"),
                    {"role": role, "id": pid}
                )

            db.commit()
        finally:
            db.close()

    # -------------------------
    # 4️⃣ Resolve Night
    # -------------------------
    def resolve_night(self, game_id, killer_target_id, doctor_target_id):
        db: Session = SessionLocal()
        try:
            # Validate target exists and alive - use agent_id, not id!
            target = db.execute(
                text("""
                    SELECT agent_id FROM game_players
                    WHERE agent_id = :agent_id AND game_id = :game_id AND is_alive = 1
                """),
                {"agent_id": killer_target_id, "game_id": game_id}  # Fixed!
            ).fetchone()

            if not target:
                print(f"WARNING: Invalid killer target {killer_target_id} for game {game_id}")
                return

            if killer_target_id != doctor_target_id:
                db.execute(
                    text("""
                        UPDATE game_players
                        SET is_alive = 0,
                            death_reason = 'killed'
                        WHERE game_id = :game_id AND agent_id = :agent_id  -- Fixed!
                    """),
                    {"game_id": game_id, "agent_id": killer_target_id}
                )

            db.execute(
                text("UPDATE games SET phase = 'day' WHERE id = :game_id"),
                {"game_id": game_id}
            )

            db.commit()
            print(f"Night resolved: Killer {killer_target_id} killed, Doctor saved {doctor_target_id}")
        except Exception as e:
            print(f"ERROR in resolve_night: {e}")
            db.rollback()
        finally:
            db.close()

    # -------------------------
    # 5️⃣ Log Vote
    # -------------------------
    def log_vote(self, game_id, voter_id, target_id, phase):
        """Log a vote to the database"""
        db = SessionLocal()
        try:
            vote = Vote(
                game_id=game_id,
                phase=phase,
                voter_agent_id=voter_id,
                target_agent_id=target_id
            )
            db.add(vote)
            db.commit()
        finally:
            db.close()

    # -------------------------
    # 6️⃣ Log Action
    # -------------------------
    # In GameEngine.log_action()
    def log_action(self, game_id, actor_id, target_id, action_type):
        """Log a night action to the database"""
        db = SessionLocal()
        try:
            print(f"Logging action: game={game_id}, actor={actor_id}, target={target_id}, type={action_type}")
            action = Vote(
                game_id=game_id,
                phase=action_type,
                voter_agent_id=actor_id,  # This should match your column name
                target_agent_id=target_id  # This should match your column name
            )
            db.add(action)
            db.commit()
            print("Action logged successfully")
        except Exception as e:
            print(f"Error logging action: {e}")
            db.rollback()
        finally:
            db.close()

    # -------------------------
    # 7️⃣ Log Investigation
    # -------------------------
    def log_investigation(self, game_id, target_id, is_killer):
        """Log detective investigation result"""
        db = SessionLocal()
        try:
            # Store in agent_memory for detective
            memory = AgentMemory(
                game_id=game_id,
                agent_id=target_id,  # The investigated agent
                memory_text=f"Investigation result: {'KILLER' if is_killer else 'NOT KILLER'}"
            )
            db.add(memory)
            db.commit()
        finally:
            db.close()

    # -------------------------
    # 8️⃣ Eliminate Player
    # -------------------------
    def eliminate_player(self, game_id, agent_id, reason):
        """Eliminate a player (by vote or night kill)"""
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE game_players 
                    SET is_alive = 0, death_reason = :reason 
                    WHERE game_id = :game_id AND agent_id = :agent_id  -- Fixed!
                """),
                {"game_id": game_id, "agent_id": agent_id, "reason": reason}
            )
            db.commit()
            print(f"Player {agent_id} eliminated: {reason}")
        except Exception as e:
            print(f"ERROR in eliminate_player: {e}")
            db.rollback()
        finally:
            db.close()

    # -------------------------
    # 9️⃣ Check Win Condition
    # -------------------------
    def check_win(self, game_id):
        db: Session = SessionLocal()
        try:
            killers = db.execute(
                text("""
                    SELECT COUNT(*) FROM game_players
                    WHERE game_id = :game_id
                      AND role = 'killer'
                      AND is_alive = 1
                """),
                {"game_id": game_id}
            ).scalar()

            citizens = db.execute(
                text("""
                    SELECT COUNT(*) FROM game_players
                    WHERE game_id = :game_id
                      AND role != 'killer'
                      AND is_alive = 1
                """),
                {"game_id": game_id}
            ).scalar()

            if killers == 0:
                db.execute(
                    text("""
                        UPDATE games
                        SET status = 'ended',
                            winner = 'citizens'
                        WHERE id = :game_id
                    """),
                    {"game_id": game_id}
                )
                db.commit()
                return "citizens"

            if killers >= citizens:
                db.execute(
                    text("""
                        UPDATE games
                        SET status = 'ended',
                            winner = 'killer'
                        WHERE id = :game_id
                    """),
                    {"game_id": game_id}
                )
                db.commit()
                return "killer"

            return None
        finally:
            db.close()

# ===== STANDALONE FUNCTIONS (outside the class) =====

async def resolve_day_vote(game_state):
    """Count votes and determine who gets eliminated"""
    if not game_state.current_votes:
        return None
    
    # Count votes
    vote_count = {}
    for voter, target in game_state.current_votes.items():
        vote_count[target] = vote_count.get(target, 0) + 1
    
    if not vote_count:
        return None
    
    # Find player with most votes
    max_votes = max(vote_count.values())
    candidates = [target for target, count in vote_count.items() if count == max_votes]
    
    # If tie, no one dies
    if len(candidates) > 1:
        return None
    
    eliminated_id = candidates[0]
    
    # Log votes to database
    engine = GameEngine()
    for voter, target in game_state.current_votes.items():
        engine.log_vote(game_state.game_id, voter, target, "day_vote")
    
    return eliminated_id

async def run_day_voting(channel, game_state, duration):
    """All alive agents vote for who they suspect"""
    await channel.send("🗳️ **All players, vote for who you suspect:**")
    
    all_agents = get_agents(limit=20)
    agent_map = {a["id"]: a for a in all_agents}
    
    votes = {}  # voter_id -> target_id
    end_time = asyncio.get_event_loop().time() + duration
    
    # Show all alive players at start
    alive_list = "\n".join([f"  • {p.name} (ID: {p.agent_id})" for p in game_state.get_alive_players()])
    await channel.send(f"**Alive players:**\n{alive_list}")
    
    # Collect votes from all alive players
    for player in game_state.get_alive_players():
        if asyncio.get_event_loop().time() >= end_time:
            remaining = len([p for p in game_state.get_alive_players() if p.agent_id not in votes])
            await channel.send(f"⏰ **Time's up!** {remaining} players didn't vote.")
            break
            
        agent = agent_map.get(player.agent_id)
        if not agent:
            continue
        
        # Add role to agent dict for prompt
        agent_with_role = agent.copy()
        agent_with_role["role"] = player.role.value
        
        # Build voting prompt
        prompt = build_vote_prompt(agent_with_role, game_state)
        response = ask_ollama(prompt).strip()
        
        try:
            # Parse response: "VOTE: 5" or just the number
            if ":" in response:
                target_id = int(response.split(":")[1].strip())
            else:
                target_id = int(response)
            
            # Validate target is alive and not self-voting
            if target_id in game_state.alive_agents and target_id != player.agent_id:
                votes[player.agent_id] = target_id
                target_name = game_state.players[target_id].name
                await channel.send(f"✓ **{agent['name']}** voted for **{target_name}**")
            else:
                # Provide more specific error message
                if target_id == player.agent_id:
                    await channel.send(f"⚠ **{agent['name']}** tried to vote for themselves! Invalid vote.")
                elif target_id not in game_state.alive_agents:
                    await channel.send(f"⚠ **{agent['name']}** voted for a dead/invalid player! Invalid vote.")
                else:
                    await channel.send(f"⚠ **{agent['name']}** submitted an invalid vote.")
                
        except (ValueError, IndexError):
            await channel.send(f"⚠ **{agent['name']}** failed to vote properly (response: '{response}')")
            continue
        
        await asyncio.sleep(0.5)  # Small delay between votes
    
    # Store votes in game state for resolution
    game_state.current_votes = votes
    
    # Show voting summary
    if votes:
        await channel.send("\n📊 **VOTING SUMMARY**")
        vote_count = {}
        for voter_id, target_id in votes.items():
            voter_name = game_state.players[voter_id].name
            target_name = game_state.players[target_id].name
            await channel.send(f"  • {voter_name} → {target_name}")
            vote_count[target_id] = vote_count.get(target_id, 0) + 1
        
        # Show vote counts
        await channel.send("\n**Vote Counts:**")
        for target_id, count in vote_count.items():
            target_name = game_state.players[target_id].name
            await channel.send(f"  • {target_name}: **{count}** votes")
        
        await channel.send(f"\n📊 **Total votes cast:** {len(votes)}/{len(game_state.get_alive_players())}")
    else:
        await channel.send("❌ **No valid votes were cast!**")