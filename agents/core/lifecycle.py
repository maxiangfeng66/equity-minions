"""
Agent Lifecycle State Management

Defines the lifecycle states for spawnable agents and valid transitions.
"""

from enum import Enum, auto
from typing import Set, Dict


class AgentLifecycleState(Enum):
    """
    Agent lifecycle states with defined transitions.

    State Machine:
        SPAWNING -> ACTIVE -> IDLE <-> ACTIVE
                           -> SUSPENDED <-> ACTIVE
                           -> DYING -> TERMINATED
        Any state -> ERROR -> DYING -> TERMINATED
    """
    SPAWNING = auto()     # Being created, not yet ready
    ACTIVE = auto()       # Running and processing work
    IDLE = auto()         # Available but not working
    SUSPENDED = auto()    # Temporarily paused (can resume)
    DYING = auto()        # Graceful shutdown in progress
    TERMINATED = auto()   # Fully stopped, resources released
    ERROR = auto()        # In error state, needs intervention


# Valid state transitions
VALID_TRANSITIONS: Dict[AgentLifecycleState, Set[AgentLifecycleState]] = {
    AgentLifecycleState.SPAWNING: {
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.ERROR,
        AgentLifecycleState.DYING
    },
    AgentLifecycleState.ACTIVE: {
        AgentLifecycleState.IDLE,
        AgentLifecycleState.SUSPENDED,
        AgentLifecycleState.DYING,
        AgentLifecycleState.ERROR
    },
    AgentLifecycleState.IDLE: {
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.DYING,
        AgentLifecycleState.ERROR
    },
    AgentLifecycleState.SUSPENDED: {
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.DYING,
        AgentLifecycleState.ERROR
    },
    AgentLifecycleState.DYING: {
        AgentLifecycleState.TERMINATED
    },
    AgentLifecycleState.TERMINATED: set(),  # Terminal state
    AgentLifecycleState.ERROR: {
        AgentLifecycleState.DYING,
        AgentLifecycleState.ACTIVE  # Recovery
    }
}


def can_transition(from_state: AgentLifecycleState, to_state: AgentLifecycleState) -> bool:
    """Check if a state transition is valid"""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def is_terminal(state: AgentLifecycleState) -> bool:
    """Check if state is terminal (no valid outgoing transitions)"""
    return state == AgentLifecycleState.TERMINATED


def is_active_state(state: AgentLifecycleState) -> bool:
    """Check if agent is in an operational state"""
    return state in {
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.IDLE,
        AgentLifecycleState.SUSPENDED
    }
