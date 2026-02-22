from game_engine import GameEngine
from db.database import SessionLocal
from sqlalchemy import text

def get_agent_ids(limit=4):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id FROM agents LIMIT :limit"),
            {"limit": limit}
        ).fetchall()

        return [r[0] for r in rows]
    finally:
        db.close()


def get_game_player_ids(game_id):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id FROM game_players WHERE game_id = :gid AND is_alive = 1"),
            {"gid": game_id}
        ).fetchall()

        return [r[0] for r in rows]
    finally:
        db.close()

def run_test_game():
    engine = GameEngine()

    print("Creating game...")
    game_id = engine.create_game()
    print("Game ID:", game_id)

    agent_ids = get_agent_ids(4)

    if len(agent_ids) < 3:
        raise Exception("Need at least 3 agents in agents table")

    print("Adding agents:", agent_ids)
    engine.add_agents_to_game(game_id, agent_ids)

    print("Assigning roles...")
    engine.assign_roles(game_id)

    # Pick 2 different players for night simulation
    player_ids = get_game_player_ids(game_id)
    print(player_ids)
    killer_target = player_ids[0]
    doctor_target = player_ids[1]
    print("Resolving night...")
    engine.resolve_night(game_id, killer_target, doctor_target)

    print("Resolving day vote...")
    engine.resolve_day_vote(game_id)

    winner = engine.check_win(game_id)
    print("Winner:", winner)


if __name__ == "__main__":
    run_test_game()
