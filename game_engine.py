# game_engine.py
# it will make new game
# add new players adding agent into game
# assign roles
# night resolution
# voting system
# win check


# basic structure of this file
# engine.create_game()
# engine.add_agents_to_game()
# engine.assign_roles()

# while game not ended:
#     night phase:
#         collect decisions
#         engine.resolve_night()
#     check win

#     day phase:
#         collect votes
#         engine.resolve_day_vote()
#     check win

import random
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import User, Agent
from sqlalchemy import text

class GameEngine:

    def __init__(self):
        self.db: Session = SessionLocal()


    def create_game(self):
        result = self.db.execute(
            text("INSERT INTO games (status, phase, day_number) VALUES ('running', 'night', 1)")
        )
        self.db.commit()

        game_id = self.db.execute(text("SELECT last_insert_rowid()")).scalar()
        return game_id
    
    def add_agents_to_game(self, game_id, agent_ids):
        for agent_id in agent_ids:
            self.db.execute(
                text("""
                    INSERT INTO game_players (game_id, agent_id, role, is_alive)
                    VALUES (:game_id, :agent_id, 'citizen', 1)
                """),
                {"game_id": game_id, "agent_id": agent_id}
            )

        self.db.commit()

    def assign_roles(self, game_id):

        players = self.db.execute(
            text("SELECT id FROM game_players WHERE game_id = :game_id"),
            {"game_id": game_id}
        ).fetchall()

        player_ids = [p[0] for p in players]

        killer = random.choice(player_ids)
        player_ids.remove(killer)

        doctor = random.choice(player_ids)
        player_ids.remove(doctor)

        detective = random.choice(player_ids)

        roles = {
            killer: "killer",
            doctor: "doctor",
            detective: "detective"
        }

        for pid, role in roles.items():
            self.db.execute(
                text("UPDATE game_players SET role = :role WHERE id = :id"),
                {"role": role, "id": pid}
            )

        self.db.commit()

    def resolve_night(self, game_id, killer_target, doctor_target):

        if killer_target != doctor_target:
            self.db.execute(
                text("""
                    UPDATE game_players
                    SET is_alive = 0
                    WHERE id = :id
                """),
                {"id": killer_target}
            )

        self.db.execute(
            text("UPDATE games SET phase = 'day' WHERE id = :game_id"),
            {"game_id": game_id}
        )

        self.db.commit()

    def resolve_day_vote(self, game_id):

        votes = self.db.execute(
            text("""
                SELECT target_agent_id, COUNT(*) as c
                FROM votes
                WHERE game_id = :game_id AND phase = 'day_vote'
                GROUP BY target_agent_id
                ORDER BY c DESC
                LIMIT 1
            """),
            {"game_id": game_id}
        ).fetchone()

        if votes:
            target = votes[0]

            self.db.execute(
                text("UPDATE game_players SET is_alive = 0 WHERE agent_id = :id"),
                {"id": target}
            )

        self.db.execute(
            text("""
                UPDATE games
                SET phase = 'night',
                    day_number = day_number + 1
                WHERE id = :game_id
            """),
            {"game_id": game_id}
        )

        self.db.commit()
        
    def check_win(self, game_id):

        killers = self.db.execute(
            text("""
                SELECT COUNT(*) FROM game_players
                WHERE game_id = :game_id
                AND role = 'killer'
                AND is_alive = 1
            """),
            {"game_id": game_id}
        ).scalar()

        citizens = self.db.execute(
            text("""
                SELECT COUNT(*) FROM game_players
                WHERE game_id = :game_id
                AND role != 'killer'
                AND is_alive = 1
            """),
            {"game_id": game_id}
        ).scalar()

        if killers == 0:
            self.db.execute(
                text("UPDATE games SET status='ended', winner='citizens' WHERE id=:game_id"),
                {"game_id": game_id}
            )
            self.db.commit()
            return "citizens"

        if killers >= citizens:
            self.db.execute(
                text("UPDATE games SET status='ended', winner='killer' WHERE id=:game_id"),
                {"game_id": game_id}
            )
            self.db.commit()
            return "killer"

        return None