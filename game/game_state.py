# game_state.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

class Role(Enum):
    KILLER = "killer"
    DOCTOR = "doctor"
    DETECTIVE = "detective"
    CITIZEN = "citizen"

class Phase(Enum):
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"
    MORNING = "morning"

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

@dataclass
class GameState:
    game_id: int
    phase: Phase
    day_number: int = 1
    players: Dict[int, Player] = field(default_factory=dict)  # agent_id -> Player
    alive_agents: Set[int] = field(default_factory=set)
    dead_agents: Set[int] = field(default_factory=set)
    
    # Night resolution
    last_night_kill_attempt: Optional[int] = None
    last_night_saved: Optional[int] = None
    last_night_investigation: Optional[tuple] = None  # (detective_id, target_id, is_killer)
    
    # Vote tracking
    current_votes: Dict[int, int] = field(default_factory=dict)  # voter_id -> target_id
    
    def get_alive_by_role(self, role: Role) -> List[Player]:
        """Get all alive players with specific role"""
        return [p for p in self.players.values() if p.is_alive and p.role == role]
    
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
        if alive_killers >= alive_citizens:
            return "killer"
        return None

# Global game state storage (in-memory, per channel/guild)
active_games: Dict[int, GameState] = {}  # channel_id -> GameState