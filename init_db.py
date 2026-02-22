import sqlite3

conn = sqlite3.connect("mafia.db")
cursor = conn.cursor()

cursor.executescript("""
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    system_prompt TEXT,
    backstory TEXT,
    personality TEXT,
    pfp_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,              -- lobby, running, ended
    phase TEXT NOT NULL,               -- day, night
    day_number INTEGER DEFAULT 1,
    winner TEXT,                       -- citizens / killer
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE game_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    role TEXT NOT NULL,                -- killer, doctor, detective, citizen
    is_alive INTEGER DEFAULT 1,
    death_reason TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    phase TEXT NOT NULL,               -- day_vote / night_kill / night_save / night_investigate
    voter_agent_id INTEGER NOT NULL,
    target_agent_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id)
);
CREATE TABLE chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    phase TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id)
);
CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    memory_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id)
);""")

conn.commit()
conn.close()

print("Database created.")