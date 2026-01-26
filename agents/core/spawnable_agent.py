"""
Spawnable Agent - Extended base class supporting hierarchical spawning and lifecycle management

This class extends BaseAgent with:
- Parent-child relationships with generation tracking
- Lifecycle state management with transitions
- Dynamic child spawning and termination
- Health reporting for supervision
- Integration with AgentRegistry
- Automatic logging via AgentLogger
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import uuid4
import asyncio

# Import base agent
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, ResearchContext, AgentMessage
from .lifecycle import AgentLifecycleState, can_transition, is_terminal

# Import agent logger
try:
    from agents.agent_logger import get_logger, log_spawn, log_terminate, log_ai_call
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False
    def get_logger(): return None
    def log_spawn(*args, **kwargs): pass
    def log_terminate(*args, **kwargs): pass
    def log_ai_call(*args, **kwargs): pass

if TYPE_CHECKING:
    from .agent_registry import AgentRegistry
    from visualizer.visualizer_bridge import VisualizerBridge


class SpawnableAgent(BaseAgent):
    """
    Extended base class supporting hierarchical spawning and lifecycle management.

    Key Capabilities:
    - Parent-child relationships with generation tracking
    - Lifecycle state management with transitions
    - Dynamic child spawning and termination
    - Health reporting for supervision
    - Integration with global AgentRegistry

    Usage:
        class MyAgent(SpawnableAgent):
            def _get_system_prompt(self) -> str:
                return "You are a specialized agent..."

            async def analyze(self, context, **kwargs) -> str:
                # Can spawn children
                child = await self.spawn_child(
                    ChildAgentClass, "child_role",
                    config={'task': 'subtask'}
                )
                result = await child.analyze(context)
                await self.terminate_child(child.agent_id)
                return result
    """

    # Class-level registry reference (set at startup)
    _registry: Optional['AgentRegistry'] = None
    # Class-level visualizer reference (set at startup)
    _visualizer: Optional['VisualizerBridge'] = None

    def __init__(
        self,
        ai_provider,
        role: str,
        parent_id: Optional[str] = None,
        tier: int = 2,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a spawnable agent.

        Args:
            ai_provider: AI provider for generation
            role: Role identifier (analyst, bull, bear, etc.)
            parent_id: ID of parent agent (None for root)
            tier: Hierarchy tier (0=architect, 1=supervisor, 2=worker, 3=goalkeeper)
            config: Additional configuration
        """
        super().__init__(ai_provider, role)

        # Identity
        self.agent_id: str = f"{role}-{uuid4().hex[:8]}"
        self.tier: int = tier
        self.config: Dict[str, Any] = config or {}

        # Hierarchy
        self.parent_id: Optional[str] = parent_id
        self.supervisor_id: Optional[str] = config.get('supervisor_id', parent_id) if config else parent_id
        self.children_ids: List[str] = []
        self.generation: int = self._calculate_generation()

        # Lifecycle
        self._state: AgentLifecycleState = AgentLifecycleState.SPAWNING
        self.created_at: datetime = datetime.now()
        self.terminated_at: Optional[datetime] = None
        self.last_heartbeat: datetime = datetime.now()
        self.state_history: List[Dict] = []

        # Health tracking
        self.error_count: int = 0
        self.max_errors: int = config.get('max_errors', 3) if config else 3

        # Work tracking
        self.current_task: Optional[str] = None
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0

        # Register with global registry
        if self._registry:
            self._registry.register(self)

        # Notify visualizer of spawn
        if self._visualizer:
            self._visualizer.spawn_agent(
                agent_type=self._get_visualizer_type(),
                name=self._get_display_name(),
                parent_id=self.parent_id,
                supervisor_id=self.supervisor_id,
                tier=self.tier,
                task=self.current_task or "Initializing",
                agent_id=self.agent_id  # Use agent's actual ID for consistency
            )

        # Log agent spawn
        if LOGGER_AVAILABLE:
            provider_name = getattr(ai_provider, 'provider_name', None) if ai_provider else None
            log_spawn(
                agent_id=self.agent_id,
                role=role,
                tier=tier,
                parent_id=parent_id,
                provider=provider_name,
                config=config
            )

    # ==========================================
    # Lifecycle Management
    # ==========================================

    @property
    def state(self) -> AgentLifecycleState:
        """Current lifecycle state"""
        return self._state

    def _transition_state(self, new_state: AgentLifecycleState) -> bool:
        """
        Attempt to transition to a new state.

        Returns:
            True if transition successful
        """
        if not can_transition(self._state, new_state):
            return False

        old_state = self._state
        self._state = new_state

        # Record in history
        self.state_history.append({
            'from': old_state.name,
            'to': new_state.name,
            'timestamp': datetime.now().isoformat()
        })

        # Notify registry
        if self._registry:
            self._registry.notify_state_change(self, old_state, new_state)

        return True

    async def activate(self) -> bool:
        """
        Transition to ACTIVE state.

        Returns:
            True if activation successful
        """
        if self._state in (AgentLifecycleState.SPAWNING, AgentLifecycleState.IDLE):
            if self._transition_state(AgentLifecycleState.ACTIVE):
                self.last_heartbeat = datetime.now()
                await self._on_activate()
                # Notify visualizer of activation
                if self._visualizer:
                    self._visualizer.activate_agent(
                        self.agent_id,
                        task=self.current_task or f"Active: {self.role}"
                    )
                return True
        return False

    async def deactivate(self) -> bool:
        """
        Transition to IDLE state.

        Returns:
            True if deactivation successful
        """
        if self._state == AgentLifecycleState.ACTIVE:
            if self._transition_state(AgentLifecycleState.IDLE):
                self.current_task = None
                await self._on_deactivate()
                # Notify visualizer of deactivation
                if self._visualizer:
                    self._visualizer.update_agent_task(
                        self.agent_id,
                        "Standing by",
                        progress=0
                    )
                return True
        return False

    async def suspend(self) -> bool:
        """
        Suspend agent (pausable).

        Returns:
            True if suspension successful
        """
        if self._state == AgentLifecycleState.ACTIVE:
            if self._transition_state(AgentLifecycleState.SUSPENDED):
                await self._on_suspend()
                # Notify visualizer of suspension
                if self._visualizer:
                    self._visualizer.suspend_agent(self.agent_id, reason="manual_suspend")
                return True
        return False

    async def resume(self) -> bool:
        """
        Resume from suspension.

        Returns:
            True if resume successful
        """
        if self._state == AgentLifecycleState.SUSPENDED:
            if self._transition_state(AgentLifecycleState.ACTIVE):
                self.last_heartbeat = datetime.now()
                await self._on_resume()
                # Notify visualizer of resume
                if self._visualizer:
                    self._visualizer.activate_agent(
                        self.agent_id,
                        task=self.current_task or f"Resumed: {self.role}"
                    )
                return True
        return False

    async def terminate(self, graceful: bool = True) -> bool:
        """
        Terminate agent and all children.

        Args:
            graceful: If True, allows current work to complete

        Returns:
            True if termination successful
        """
        if is_terminal(self._state):
            return False

        # Transition to DYING
        self._transition_state(AgentLifecycleState.DYING)

        # Terminate all children first (depth-first)
        for child_id in list(self.children_ids):
            child = self._registry.get(child_id) if self._registry else None
            if child:
                await child.terminate(graceful=graceful)

        # Graceful shutdown
        if graceful:
            await self._graceful_shutdown()

        # Cleanup hook
        await self._on_terminate()

        # Final state
        self._transition_state(AgentLifecycleState.TERMINATED)
        self.terminated_at = datetime.now()

        # Notify visualizer of termination
        if self._visualizer:
            self._visualizer.terminate_agent(
                self.agent_id,
                reason="graceful" if graceful else "forced"
            )

        # Log agent termination
        if LOGGER_AVAILABLE:
            log_terminate(self.agent_id, reason="graceful" if graceful else "forced")

        # Deregister from registry
        if self._registry:
            self._registry.deregister(self.agent_id)

        return True

    def mark_error(self, error_msg: str = None):
        """Mark an error occurrence"""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self._transition_state(AgentLifecycleState.ERROR)
            # Notify visualizer of error state
            if self._visualizer:
                self._visualizer.update_agent_task(
                    self.agent_id,
                    f"ERROR: {error_msg[:30] if error_msg else 'Max errors reached'}",
                    progress=0
                )

    def clear_errors(self):
        """Clear error count (after recovery)"""
        self.error_count = 0
        if self._state == AgentLifecycleState.ERROR:
            self._transition_state(AgentLifecycleState.ACTIVE)

    def heartbeat(self):
        """Update heartbeat timestamp (called periodically during work)"""
        self.last_heartbeat = datetime.now()

    def is_healthy(self, timeout_seconds: int = 60) -> bool:
        """
        Check if agent is responsive and healthy.

        Args:
            timeout_seconds: Max seconds since last heartbeat

        Returns:
            True if healthy
        """
        if self._state in (AgentLifecycleState.TERMINATED, AgentLifecycleState.ERROR):
            return False

        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds and self.error_count < self.max_errors

    def is_available(self) -> bool:
        """Check if agent can accept new work"""
        return self._state in (AgentLifecycleState.IDLE, AgentLifecycleState.ACTIVE)

    # ==========================================
    # Child Spawning
    # ==========================================

    async def spawn_child(
        self,
        agent_class: type,
        role: str,
        ai_provider=None,
        config: Optional[Dict[str, Any]] = None
    ) -> 'SpawnableAgent':
        """
        Spawn a child agent.

        Args:
            agent_class: Class of agent to spawn (must extend SpawnableAgent)
            role: Role identifier for the child
            ai_provider: AI provider to inject (uses parent's if None)
            config: Configuration dict for child

        Returns:
            The spawned child agent
        """
        # Use parent's AI provider if not specified
        provider = ai_provider or self.ai_provider

        # Merge config with defaults
        child_config = config or {}
        child_config['supervisor_id'] = child_config.get('supervisor_id', self.agent_id)

        # Create child with parent reference
        child = agent_class(
            ai_provider=provider,
            role=role,
            parent_id=self.agent_id,
            tier=self.tier + 1,
            config=child_config
        )

        # Track child
        self.children_ids.append(child.agent_id)

        # Activate child
        await child.activate()

        return child

    async def terminate_child(self, child_id: str, graceful: bool = True) -> bool:
        """
        Terminate a specific child.

        Args:
            child_id: ID of child to terminate
            graceful: Allow graceful shutdown

        Returns:
            True if terminated successfully
        """
        if child_id not in self.children_ids:
            return False

        child = self._registry.get(child_id) if self._registry else None
        if child:
            await child.terminate(graceful=graceful)

        # Remove from tracking
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)

        return True

    async def terminate_all_children(self, graceful: bool = True):
        """Terminate all child agents"""
        for child_id in list(self.children_ids):
            await self.terminate_child(child_id, graceful=graceful)

    def get_child(self, child_id: str) -> Optional['SpawnableAgent']:
        """Get a specific child by ID"""
        if child_id in self.children_ids and self._registry:
            return self._registry.get(child_id)
        return None

    def get_children(self) -> List['SpawnableAgent']:
        """Get all direct children"""
        if self._registry:
            return [self._registry.get(cid) for cid in self.children_ids
                    if self._registry.get(cid)]
        return []

    # ==========================================
    # Helper Methods
    # ==========================================

    def _calculate_generation(self) -> int:
        """Calculate generation depth from root"""
        if not self.parent_id or not self._registry:
            return 0
        parent = self._registry.get(self.parent_id)
        return (parent.generation + 1) if parent else 0

    def get_status(self) -> Dict[str, Any]:
        """Get agent status for reporting/visualization"""
        return {
            'agent_id': self.agent_id,
            'role': self.role,
            'tier': self.tier,
            'generation': self.generation,
            'state': self._state.name,
            'parent_id': self.parent_id,
            'supervisor_id': self.supervisor_id,
            'children_ids': self.children_ids.copy(),
            'children_count': len(self.children_ids),
            'current_task': self.current_task,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'error_count': self.error_count,
            'is_healthy': self.is_healthy(),
            'created_at': self.created_at.isoformat(),
            'terminated_at': self.terminated_at.isoformat() if self.terminated_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat()
        }

    def set_task(self, task_description: str, progress: int = None):
        """Set current task (for status display)"""
        self.current_task = task_description
        self.heartbeat()
        # Notify visualizer of task update
        if self._visualizer:
            self._visualizer.update_agent_task(
                self.agent_id,
                task_description,
                progress=progress
            )

    def complete_task(self):
        """Mark current task as completed"""
        self.tasks_completed += 1
        self.current_task = None
        self.heartbeat()

    def fail_task(self, error_msg: str = None):
        """Mark current task as failed"""
        self.tasks_failed += 1
        self.mark_error(error_msg)
        self.current_task = None

    # ==========================================
    # Lifecycle Hooks (Override in subclasses)
    # ==========================================

    async def _on_activate(self):
        """Hook called when agent activates"""
        pass

    async def _on_deactivate(self):
        """Hook called when agent deactivates"""
        pass

    async def _on_suspend(self):
        """Hook called when agent suspends"""
        pass

    async def _on_resume(self):
        """Hook called when agent resumes"""
        pass

    async def _on_terminate(self):
        """Hook called when agent terminates"""
        pass

    async def _graceful_shutdown(self):
        """Override to implement graceful shutdown logic (save state, etc.)"""
        pass

    # ==========================================
    # Abstract Methods (from BaseAgent)
    # ==========================================

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Define the agent's system prompt/personality"""
        pass

    @abstractmethod
    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Perform analysis on the given context"""
        pass

    # ==========================================
    # Visualizer Helper Methods
    # ==========================================

    def _get_visualizer_type(self) -> str:
        """
        Map agent role to visualizer agent type.
        Override in subclasses for custom mapping.
        """
        role_map = {
            # Architect tier (0)
            'chief_architect': 'chief_architect',
            'resource_allocator': 'resource_allocator',
            'priority_manager': 'priority_manager',
            # Supervisor tier (1)
            'research_supervisor': 'research_supervisor',
            'debate_moderator': 'debate_moderator',
            # Worker tier (2)
            'analyst': 'analyst',
            'bull': 'bull',
            'bear': 'bear',
            'critic': 'critic',
            'synthesizer': 'synthesizer',
            'devil_advocate': 'devil_advocate',
            'specialist': 'specialist',
            # Goalkeeper tier (3)
            'publish_gatekeeper': 'publish_gatekeeper',
            'fact_checker': 'fact_checker',
            'logic_auditor': 'logic_auditor',
            'consensus_validator': 'consensus_validator',
        }
        # Extract base role from compound names like "analyst_1045_HK"
        base_role = self.role.split('_')[0] if '_' in self.role else self.role
        return role_map.get(base_role, role_map.get(self.role, 'researcher'))

    def _get_display_name(self) -> str:
        """
        Get human-readable display name for visualizer.
        Override in subclasses for custom names.
        """
        # Convert role to title case and clean up
        base_name = self.role.replace('_', ' ').title()
        # Add short ID suffix for uniqueness
        short_id = self.agent_id.split('-')[-1][:4] if '-' in self.agent_id else self.agent_id[-4:]
        return f"{base_name} {short_id}"


# Helper function to set global registry
def set_global_registry(registry: 'AgentRegistry'):
    """Set the global registry for all SpawnableAgent instances"""
    SpawnableAgent._registry = registry


def set_global_visualizer(visualizer: 'VisualizerBridge'):
    """Set the global visualizer for all SpawnableAgent instances"""
    SpawnableAgent._visualizer = visualizer
