# service/agent_repository.py
from sqlalchemy import text
from db.database import SessionLocal

def get_agents(limit=5):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT id, name, personality, backstory, system_prompt
                FROM agents
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "personality": r[2],
                "backstory": r[3],
                "system_prompt": r[4],
            }
            for r in rows
        ]
    finally:
        db.close()