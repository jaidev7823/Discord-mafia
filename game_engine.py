# game_engine.py
import random
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import SessionLocal
from sqlalchemy import bindparam

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
            # Validate target exists and alive
            target = db.execute(
                text("""
                    SELECT id FROM game_players
                    WHERE id = :id AND game_id = :game_id AND is_alive = 1
                """),
                {"id": killer_target_id, "game_id": game_id}
            ).fetchone()

            if not target:
                raise Exception("Invalid killer target")

            if killer_target_id != doctor_target_id:
                db.execute(
                    text("""
                        UPDATE game_players
                        SET is_alive = 0,
                            death_reason = 'killed'
                        WHERE id = :id
                    """),
                    {"id": killer_target_id}
                )

            db.execute(
                text("UPDATE games SET phase = 'day' WHERE id = :game_id"),
                {"game_id": game_id}
            )

            db.commit()
        finally:
            db.close()

    # -------------------------
    # 5️⃣ Resolve Day Vote
    # -------------------------
    def resolve_day_vote(self, game_id):
        db: Session = SessionLocal()
        try:
            votes = db.execute(
                text("""
                    SELECT target_agent_id, COUNT(*) as c
                    FROM votes
                    WHERE game_id = :game_id
                      AND phase = 'day_vote'
                    GROUP BY target_agent_id
                    ORDER BY c DESC
                    LIMIT 1
                """),
                {"game_id": game_id}
            ).fetchone()

            if votes:
                target_agent_id = votes[0]

                db.execute(
                    text("""
                        UPDATE game_players
                        SET is_alive = 0,
                            death_reason = 'voted'
                        WHERE game_id = :game_id
                          AND agent_id = :agent_id
                    """),
                    {"game_id": game_id, "agent_id": target_agent_id}
                )

            db.execute(
                text("""
                    UPDATE games
                    SET phase = 'night',
                        day_number = day_number + 1
                    WHERE id = :game_id
                """),
                {"game_id": game_id}
            )

            db.commit()
        finally:
            db.close()

    # -------------------------
    # 6️⃣ Check Win Condition
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
