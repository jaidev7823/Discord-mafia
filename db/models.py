# db/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
from .database import Base


# -----------------------------
# 1️⃣ Users
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# 2️⃣ Agents
# -----------------------------
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    system_prompt = Column(Text)
    backstory = Column(Text)
    personality = Column(Text)
    voice_path = Column(String, default="en_US-arctic-medium.onnx")  # <-- ADD THIS
    pfp_url = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# 3️⃣ Games
# -----------------------------
class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)  # lobby, running, ended
    phase = Column(String, nullable=False)   # day, night
    day_number = Column(Integer, default=1)
    winner = Column(String)                  # citizens / killer
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# 4️⃣ Game Players
# -----------------------------
class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    role = Column(String, nullable=False)        # killer, doctor, detective, citizen
    is_alive = Column(Integer, default=1)
    death_reason = Column(String)


# -----------------------------
# 5️⃣ Votes
# -----------------------------
class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    phase = Column(String, nullable=False)  # day_vote / night_kill / night_save / night_investigate
    voter_agent_id = Column(Integer, nullable=False)
    target_agent_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# 6️⃣ Chat Logs
# -----------------------------
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    agent_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    phase = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# 7️⃣ Agent Memory
# -----------------------------
class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    agent_id = Column(Integer, nullable=False)
    memory_text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())