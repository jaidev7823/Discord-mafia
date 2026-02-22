# api/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import engine, SessionLocal
from db.models import Base, User, Agent

app = FastAPI()

Base.metadata.create_all(bind=engine)

# ---------------------------
# DB Dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# Request Schema
# ---------------------------
class AgentCreate(BaseModel):
    discord_id: str
    username: str
    name: str
    personality: str
    backstory: str
    system_prompt: str
    pfp_url: str | None = None


# ---------------------------
# Create Agent Endpoint
# ---------------------------
@app.post("/agents")
def create_agent(data: AgentCreate, db: Session = Depends(get_db)):

    # 1️⃣ Ensure user exists
    user = db.query(User).filter(User.discord_id == data.discord_id).first()
    
    if not user:
        user = User(
            discord_id=data.discord_id,
            username=data.username
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2️⃣ Prevent duplicate agent name per user
    existing = db.query(Agent).filter(
        Agent.owner_id == user.id,
        Agent.name == data.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Agent name already exists")

    # 3️⃣ Create agent
    agent = Agent(
        owner_id=user.id,
        name=data.name,
        personality=data.personality,
        backstory=data.backstory,
        system_prompt=data.system_prompt,
        pfp_url=data.pfp_url
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return {
        "status": "success",
        "agent_id": agent.id
    }


@app.get("/")
def root():
    return {"status": "running"}