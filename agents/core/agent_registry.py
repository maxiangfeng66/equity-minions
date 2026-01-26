"""
Agent Registry - Centralized tracking and management of all spawnable agents

Provides:
- Global agent registration and lookup
- Hierarchy queries (parent/child/descendants)
- Statistics and health monitoring
- Event subscription for observers (like visualizer)
"""

from typing import Dict, Optional, List, Set, Callable, Any, TYPE_CHECKING
from datetime import datetime
from threading import Lock
import asyncio

if TYPE_CHECKING:
    from .spawnable_agent import SpawnableAgent

from .lifecycle import AgentLifecycleState


class AgentRegistry:
    """
    Centralized registry for all spawnable agents.

    Thread-safe singleton pattern for managing agent lifecycle,
    parent-child relationships, and health monitoring.

    Usage:
        registry = AgentRegistry()
        registry.register(agent)
        children = registry.get_children(agent_id)
        registry.subscribe(callback)
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._agents: Dict[str, 'SpawnableAgent'] = {}
        self._by_tier: Dict[int, Set[str]] = {0: set(), 1: set(), 2: set(), 3: set()}
        self._by_role: Dict[str, Set[str]] = {}
        self._by_parent: Dict[str, Set[str]] = {}
        self._subscribers: List[Callable] = []
        self._registry_lock = Lock()
        self._initialized = True
        self._event_log: List[Dict] = []
        self._max_events = 500

    # ==========================================
    # Registration
    # ==========================================

    def register(self, agent: 'SpawnableAgent') -> bool:
        """
        Register an agent with the registry.

        Args:
            agent: SpawnableAgent instance to register

        Returns:
            True if registered successfully, False if already exists
        """
        with self._registry_lock:
            if agent.agent_id in self._agents:
                return False

            self._agents[agent.agent_id] = agent

            # Index by tier
            tier = agent.tier
            if tier not in self._by_tier:
                self._by_tier[tier] = set()
            self._by_tier[tier].add(agent.agent_id)

            # Index by role
            if agent.role not in self._by_role:
                self._by_role[agent.role] = set()
            self._by_role[agent.role].add(agent.agent_id)

            # Index by parent
            if agent.parent_id:
                if agent.parent_id not in self._by_parent:
                    self._by_parent[agent.parent_id] = set()
                self._by_parent[agent.parent_id].add(agent.agent_id)

            # Log event
            self._log_event('agent_registered', agent.agent_id, {
                'role': agent.role,
                'tier': agent.tier,
                'parent_id': agent.parent_id,
                'generation': agent.generation
            })

            self._notify_subscribers('register', agent)
            return True

    def deregister(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.

        Args:
            agent_id: ID of agent to remove

        Returns:
            True if removed, False if not found
        """
        with self._registry_lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]

            # Remove from indexes
            if agent.tier in self._by_tier:
                self._by_tier[agent.tier].discard(agent_id)
            if agent.role in self._by_role:
                self._by_role[agent.role].discard(agent_id)
            if agent.parent_id and agent.parent_id in self._by_parent:
                self._by_parent[agent.parent_id].discard(agent_id)

            # Clean up children index for this agent
            if agent_id in self._by_parent:
                del self._by_parent[agent_id]

            # Log event
            self._log_event('agent_deregistered', agent_id, {
                'role': agent.role,
                'tier': agent.tier
            })

            self._notify_subscribers('deregister', agent)

            del self._agents[agent_id]
            return True

    # ==========================================
    # Queries
    # ==========================================

    def get(self, agent_id: str) -> Optional['SpawnableAgent']:
        """Get agent by ID"""
        return self._agents.get(agent_id)

    def exists(self, agent_id: str) -> bool:
        """Check if agent exists in registry"""
        return agent_id in self._agents

    def get_children(self, agent_id: str) -> List['SpawnableAgent']:
        """Get all direct children of an agent"""
        child_ids = self._by_parent.get(agent_id, set())
        return [self._agents[cid] for cid in child_ids if cid in self._agents]

    def get_descendants(self, agent_id: str) -> List['SpawnableAgent']:
        """Get all descendants (children, grandchildren, etc.)"""
        descendants = []
        children = self.get_children(agent_id)
        for child in children:
            descendants.append(child)
            descendants.extend(self.get_descendants(child.agent_id))
        return descendants

    def get_parent(self, agent_id: str) -> Optional['SpawnableAgent']:
        """Get the parent of an agent"""
        agent = self.get(agent_id)
        if agent and agent.parent_id:
            return self.get(agent.parent_id)
        return None

    def get_ancestors(self, agent_id: str) -> List['SpawnableAgent']:
        """Get all ancestors (parent, grandparent, etc.) from nearest to root"""
        ancestors = []
        current_id = agent_id
        while current_id:
            agent = self.get(current_id)
            if agent and agent.parent_id:
                parent = self.get(agent.parent_id)
                if parent:
                    ancestors.append(parent)
                    current_id = parent.agent_id
                else:
                    break
            else:
                break
        return ancestors

    def get_supervisor(self, agent_id: str) -> Optional['SpawnableAgent']:
        """
        Get the supervisor of an agent.
        By default, supervisor is the parent, but can be overridden.
        """
        agent = self.get(agent_id)
        if agent:
            supervisor_id = getattr(agent, 'supervisor_id', None) or agent.parent_id
            if supervisor_id:
                return self.get(supervisor_id)
        return None

    def get_by_tier(self, tier: int) -> List['SpawnableAgent']:
        """Get all agents at a specific tier"""
        agent_ids = self._by_tier.get(tier, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_by_role(self, role: str) -> List['SpawnableAgent']:
        """Get all agents with a specific role"""
        agent_ids = self._by_role.get(role, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_all(self) -> List['SpawnableAgent']:
        """Get all registered agents"""
        return list(self._agents.values())

    def get_all_active(self) -> List['SpawnableAgent']:
        """Get all agents in ACTIVE state"""
        return [a for a in self._agents.values()
                if a.state == AgentLifecycleState.ACTIVE]

    def get_all_idle(self) -> List['SpawnableAgent']:
        """Get all agents in IDLE state"""
        return [a for a in self._agents.values()
                if a.state == AgentLifecycleState.IDLE]

    def get_unhealthy(self, timeout_seconds: int = 60) -> List['SpawnableAgent']:
        """Get all unhealthy agents"""
        return [a for a in self._agents.values() if not a.is_healthy(timeout_seconds)]

    def get_root_agents(self) -> List['SpawnableAgent']:
        """Get agents with no parent (root level)"""
        return [a for a in self._agents.values() if a.parent_id is None]

    # ==========================================
    # Statistics
    # ==========================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            'total_agents': len(self._agents),
            'by_tier': {t: len(ids) for t, ids in self._by_tier.items()},
            'by_role': {r: len(ids) for r, ids in self._by_role.items()},
            'by_state': self._count_by_state(),
            'unhealthy_count': len(self.get_unhealthy()),
            'root_count': len(self.get_root_agents()),
            'max_generation': self._get_max_generation()
        }

    def _count_by_state(self) -> Dict[str, int]:
        """Count agents by lifecycle state"""
        counts = {}
        for agent in self._agents.values():
            state_name = agent.state.name
            counts[state_name] = counts.get(state_name, 0) + 1
        return counts

    def _get_max_generation(self) -> int:
        """Get maximum generation depth"""
        if not self._agents:
            return 0
        return max(a.generation for a in self._agents.values())

    # ==========================================
    # Hierarchy Visualization
    # ==========================================

    def get_hierarchy_tree(self) -> Dict:
        """
        Get full hierarchy tree for visualization.

        Returns:
            {
                'root_agents': [...],
                'tree': {
                    'agent_id': {
                        'agent': {...},
                        'children': [...]
                    }
                }
            }
        """
        def build_subtree(agent_id: str) -> Dict:
            agent = self.get(agent_id)
            if not agent:
                return {}

            children = self.get_children(agent_id)
            return {
                'agent': agent.get_status(),
                'children': [build_subtree(c.agent_id) for c in children]
            }

        roots = self.get_root_agents()
        return {
            'root_agents': [r.agent_id for r in roots],
            'tree': {r.agent_id: build_subtree(r.agent_id) for r in roots}
        }

    def get_agent_family(self, agent_id: str) -> Dict:
        """Get family tree for a specific agent (ancestors + descendants)"""
        agent = self.get(agent_id)
        if not agent:
            return {}

        return {
            'agent': agent.get_status(),
            'ancestors': [a.get_status() for a in self.get_ancestors(agent_id)],
            'children': [c.get_status() for c in self.get_children(agent_id)],
            'descendants': [d.get_status() for d in self.get_descendants(agent_id)]
        }

    # ==========================================
    # Event Subscription
    # ==========================================

    def subscribe(self, callback: Callable[[str, 'SpawnableAgent'], None]):
        """
        Subscribe to registry events.

        Callback receives: (event_type, agent)
        Event types: 'register', 'deregister', 'state_change'
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from registry events"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, event: str, agent: 'SpawnableAgent'):
        """Notify subscribers of registry events"""
        for callback in self._subscribers:
            try:
                callback(event, agent)
            except Exception as e:
                print(f"[Registry] Subscriber error: {e}")

    def notify_state_change(self, agent: 'SpawnableAgent', old_state: AgentLifecycleState, new_state: AgentLifecycleState):
        """Called by agents when state changes"""
        self._log_event('state_change', agent.agent_id, {
            'from': old_state.name,
            'to': new_state.name
        })
        self._notify_subscribers('state_change', agent)

    # ==========================================
    # Event Logging
    # ==========================================

    def _log_event(self, event_type: str, agent_id: str, metadata: Dict):
        """Log registry event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'agent_id': agent_id,
            'metadata': metadata
        }
        self._event_log.append(event)

        # Trim log if too long
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]

    def get_recent_events(self, count: int = 50) -> List[Dict]:
        """Get recent events"""
        return self._event_log[-count:]

    # ==========================================
    # Bulk Operations
    # ==========================================

    async def terminate_all(self, graceful: bool = True):
        """Terminate all agents (system shutdown)"""
        # Terminate from highest tier to lowest (children before parents)
        for tier in sorted(self._by_tier.keys(), reverse=True):
            agent_ids = list(self._by_tier.get(tier, set()))
            for agent_id in agent_ids:
                agent = self.get(agent_id)
                if agent:
                    await agent.terminate(graceful=graceful)

    async def terminate_subtree(self, root_agent_id: str, graceful: bool = True):
        """Terminate an agent and all its descendants"""
        descendants = self.get_descendants(root_agent_id)

        # Terminate descendants first (deepest first)
        sorted_desc = sorted(descendants, key=lambda a: -a.generation)
        for agent in sorted_desc:
            await agent.terminate(graceful=graceful)

        # Then terminate root
        root = self.get(root_agent_id)
        if root:
            await root.terminate(graceful=graceful)

    def reset(self):
        """Reset registry (for testing)"""
        with self._registry_lock:
            self._agents.clear()
            for tier in self._by_tier:
                self._by_tier[tier].clear()
            self._by_role.clear()
            self._by_parent.clear()
            self._event_log.clear()


# Convenience function to get singleton instance
def get_registry() -> AgentRegistry:
    """Get the global AgentRegistry instance"""
    return AgentRegistry()
