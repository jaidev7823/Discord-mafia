# game/memory.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum

class EventType(Enum):
    VOTE = "vote"
    KILL = "kill"
    SAVE = "save"
    INVESTIGATE = "investigate"
    DISCUSSION = "discussion"
    DEATH = "death"
    CLAIM = "claim"

@dataclass
class GameEvent:
    """A single event in the game"""
    type: EventType
    day: int
    phase: str
    actor: Optional[str] = None
    target: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PlayerMemory:
    """What a player remembers about the game"""
    player_id: int
    player_name: str
    role: str
    
    # Observations
    seen_votes: Dict[str, List[str]] = field(default_factory=dict)  # who voted for whom
    seen_deaths: List[str] = field(default_factory=list)  # who died
    seen_claims: Dict[str, str] = field(default_factory=dict)  # who claimed what role
    
    # Suspicions (player -> suspicion level 0-10)
    suspicions: Dict[str, float] = field(default_factory=dict)
    
    # Trust (player -> trust level 0-10)
    trust: Dict[str, float] = field(default_factory=dict)
    
    # Known information
    known_roles: Dict[str, str] = field(default_factory=dict)  # detective findings
    confirmed_allies: Set[str] = field(default_factory=set)  # teammates (for mafia)
    
    # Event log
    events: List[GameEvent] = field(default_factory=list)
    
    def add_event(self, event: GameEvent):
        self.events.append(event)
        
        # Update suspicions based on events
        if event.type == EventType.VOTE and event.target:
            # Someone voted for someone - suspicious if voter is unknown
            if event.actor:
                self.suspicions[event.target] = self.suspicions.get(event.target, 0) + 1
        
        elif event.type == EventType.KILL and event.actor:
            # Killer revealed (only known to mafia)
            self.confirmed_allies.add(event.actor)
        
        elif event.type == EventType.INVESTIGATE and event.target:
            # Detective learned something
            if event.message == "killer":
                self.known_roles[event.target] = "killer"
                self.suspicions[event.target] = 10
            else:
                self.known_roles[event.target] = "citizen"
                self.trust[event.target] = self.trust.get(event.target, 0) + 3
    
    def get_suspicious_players(self) -> List[str]:
        """Return players sorted by suspicion"""
        return sorted(self.suspicions.keys(), key=lambda x: self.suspicions[x], reverse=True)
    
    def get_trusted_players(self) -> List[str]:
        """Return players sorted by trust"""
        return sorted(self.trust.keys(), key=lambda x: self.trust[x], reverse=True)
    
    def format_for_prompt(self) -> str:
        """Format memory for LLM prompt"""
        lines = []
        lines.append(f"Your role: {self.role.upper()}")
        
        if self.known_roles:
            lines.append("\nKnown roles:")
            for player, role in self.known_roles.items():
                lines.append(f"  • {player} is {role}")
        
        if self.suspicions:
            lines.append("\nYour suspicions:")
            for player in self.get_suspicious_players()[:3]:
                lines.append(f"  • {player}: suspicious")
        
        if self.trust:
            lines.append("\nPlayers you trust:")
            for player in self.get_trusted_players()[:2]:
                lines.append(f"  • {player}")
        
        # Recent events
        recent = self.events[-5:] if self.events else []
        if recent:
            lines.append("\nRecent events:")
            for e in recent:
                if e.type == EventType.VOTE and e.actor and e.target:
                    lines.append(f"  • {e.actor} voted for {e.target}")
                elif e.type == EventType.DEATH and e.target:
                    lines.append(f"  • {e.target} died")
                elif e.type == EventType.CLAIM and e.actor and e.message:
                    lines.append(f"  • {e.actor} claimed to be {e.message}")
        
        return "\n".join(lines)