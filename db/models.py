# db/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    personality = Column(Text)
    backstory = Column(Text)
    system_prompt = Column(Text)
    pfp_url = Column(String)