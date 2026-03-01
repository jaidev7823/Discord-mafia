# game/game_state.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
from .memory import PlayerMemory, GameEvent, EventType

class Role(Enum):
    KILLER = "killer"
    DOCTOR = "doctor"
    DETECTIVE = "detective"
    CITIZEN = "citizen"

# class Phase(str, Enum):
#     DAY = "day"
#     EVENING = "evening"
#     NIGHT = "night"
#     MORNING = "morning"

class Phase(str, Enum):
    MORNING_DISCUSSION = "morning_discussion"
    MORNING_VOTING = "morning_voting"
    EVENING_DISCUSSION = "evening_discussion"
    EVENING_ACTION = "evening_action"
    NIGHT_DISCUSSION = "night_discussion"
    NIGHT_ACTION = "night_action"
    
@dataclass
class Player:
    agent_id: int
    name: str
    role: Role
    is_alive: bool = True
    death_reason: Optional[str] = None
    
    # Night actions
    night_target: Optional[int] = None  # Who they target (killer/doctor)
    investigation_target: Optional[int] = None  # Detective only
    
    # Memory/context
    knows_role_of: Dict[int, Role] = field(default_factory=dict)  # Detective findings

    memory: Optional[PlayerMemory] = None  # Add this
    
    def __post_init__(self):
        if self.memory is None:
            self.memory = PlayerMemory(
                player_id=self.agent_id,
                player_name=self.name,
                role=self.role.value
            )

def record_event(self, event_type: EventType, actor: Optional[str] = None, 
                 target: Optional[str] = None, message: Optional[str] = None):
    """Record an event for all players to remember"""
    event = GameEvent(
        type=event_type,
        day=self.day_number,
        phase=self.phase.value,
        actor=actor,
        target=target,
        message=message
    )
    
    # All alive players witness public events
    for player in self.get_alive_players():
        player.memory.add_event(event)
    
    # Special handling for private events
    if event_type == EventType.KILL and actor:
        # Only killers know who killed
        killer = self.players.get(actor)
        if killer and killer.is_alive:
            killer.memory.add_event(event)
    
    elif event_type == EventType.INVESTIGATE and actor:
        # Only detective knows result
        detective = self.players.get(actor)
        if detective and detective.is_alive:
            detective.memory.add_event(event)

@dataclass
class GameState:
    game_id: int
    phase: Phase
    day_number: int = 1
    players: Dict[int, Player] = field(default_factory=dict)
    alive_agents: Set[int] = field(default_factory=set)
    dead_agents: Set[int] = field(default_factory=set)
    
    # Night resolution
    last_night_kill_attempt: Optional[int] = None
    last_night_saved: Optional[int] = None
    last_night_investigation: Optional[tuple] = None
    last_discussion: List[Dict] = field(default_factory=list)   
    last_killer_discussion: List[Dict] = field(default_factory=list)

    # Vote tracking
    current_votes: Dict[int, int] = field(default_factory=dict)
    
    # Game state - ADD THESE LINES
    game_over: bool = False
    winner: Optional[str] = None
    
    def get_alive_by_role(self, role: Role) -> List[Player]:
        """Get all alive players with specific role"""
        return [p for p in self.players.values() if p.is_alive and p.role == role]
    
    # In game/game_state.py, add these methods:
    def get_doctor(self) -> Optional[Player]:
        """Get the alive doctor"""
        doctors = self.get_alive_by_role(Role.DOCTOR)
        return doctors[0] if doctors else None
    
    def get_detective(self) -> Optional[Player]:
        """Get the alive detective"""
        detectives = self.get_alive_by_role(Role.DETECTIVE)
        return detectives[0] if detectives else None

    def get_killer(self) -> Optional[Player]:
        """Get the alive killer (should be only one)"""
        killers = self.get_alive_by_role(Role.KILLER)
        return killers[0] if killers else None
    
    def get_alive_players(self) -> List[Player]:
        """Get all alive players"""
        return [p for p in self.players.values() if p.is_alive]
    
    def kill_player(self, agent_id: int, reason: str):
        """Mark player as dead"""
        if agent_id in self.players:
            self.players[agent_id].is_alive = False
            self.players[agent_id].death_reason = reason
            self.alive_agents.discard(agent_id)
            self.dead_agents.add(agent_id)
    
    def reset_night_actions(self):
        """Clear all night actions for new night phase"""
        for player in self.players.values():
            player.night_target = None
            player.investigation_target = None
        self.current_votes.clear()
    
    def check_win_condition(self) -> Optional[str]:
        """Check if game has ended. Returns 'citizens', 'killer', or None"""
        alive_killers = len(self.get_alive_by_role(Role.KILLER))
        alive_citizens = len([p for p in self.get_alive_players() if p.role != Role.KILLER])
        
        if alive_killers == 0:
            return "citizens"
        # Killer side wins only when no non-killers are alive.
        # This keeps the game running even if killers outnumber others.
        if alive_killers > 0 and alive_citizens == 0:
            return "killer"
        return None

    def reset_discussion_history(self):
        """Clear discussion history for new game"""
        self.last_discussion = []
        self.last_killer_discussion = []

# Global game state storage (in-memory, per channel/guild)
active_games: Dict[int, GameState] = {}  # channel_id -> GameStatoe
