"""
Claude Minions Visualizer Client

A Python client for pushing real-time updates to the Claude Minions Visualizer.

Usage:
    from minions_client import MinionsClient

    client = MinionsClient()
    client.update_agent('researcher-1', progress=85, status='active')
    client.update_task('6682 HK', status='completed')
"""

import json
import requests
from typing import Optional, Dict, List, Literal

AgentType = Literal['orchestrator', 'researcher', 'analyst', 'critic', 'debater']
AgentStatus = Literal['active', 'waiting', 'idle']
TaskStatus = Literal['active', 'pending', 'completed']
ConnectionType = Literal['command', 'data_flow', 'waiting', 'parallel', 'interaction']


class MinionsClient:
    """Client for the Claude Minions Visualizer API."""

    def __init__(self, base_url: str = 'http://localhost:8080'):
        self.base_url = base_url.rstrip('/')
        self.api_url = f'{self.base_url}/api'

    def _post(self, endpoint: str, data: dict) -> dict:
        """Make a POST request to the API."""
        try:
            response = requests.post(f'{self.api_url}/{endpoint}', json=data, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"[MinionsClient] Server not running at {self.base_url}")
            return {'success': False, 'error': 'Connection refused'}
        except Exception as e:
            print(f"[MinionsClient] Error: {e}")
            return {'success': False, 'error': str(e)}

    def _get(self, endpoint: str) -> dict:
        """Make a GET request to the API."""
        try:
            response = requests.get(f'{self.api_url}/{endpoint}', timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"[MinionsClient] Server not running at {self.base_url}")
            return {}
        except Exception as e:
            print(f"[MinionsClient] Error: {e}")
            return {}

    # ==========================================
    # Agent Methods
    # ==========================================

    def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        task: Optional[str] = None,
        ticker: Optional[str] = None,
        progress: Optional[int] = None,
        tier: Optional[int] = None,
        position: Optional[Dict[str, float]] = None,
        connections: Optional[List[Dict]] = None
    ) -> dict:
        """
        Update a single agent in the visualizer.

        Args:
            agent_id: Unique identifier for the agent (required)
            name: Display name (e.g., "Researcher Alpha")
            type: Agent type (orchestrator, researcher, analyst, critic, debater)
            status: Current status (active, waiting, idle)
            task: Current task description
            ticker: Associated stock ticker
            progress: Progress percentage (0-100)
            tier: Workflow tier (0=top/orchestrator, 3=bottom/review)
            position: 3D position {'x': float, 'z': float}
            connections: List of connections [{'to': 'agent-id', 'type': 'data_flow'}]

        Returns:
            API response dict
        """
        data = {'id': agent_id}

        if name is not None: data['name'] = name
        if type is not None: data['type'] = type
        if status is not None: data['status'] = status
        if task is not None: data['task'] = task
        if ticker is not None: data['ticker'] = ticker
        if progress is not None: data['progress'] = max(0, min(100, progress))
        if tier is not None: data['tier'] = tier
        if position is not None: data['position'] = position
        if connections is not None: data['connections'] = connections

        return self._post('agent', data)

    def update_agents(self, agents: List[Dict]) -> dict:
        """
        Update multiple agents at once.

        Args:
            agents: List of agent dicts, each must have 'id' field

        Returns:
            API response dict
        """
        return self._post('agents', agents)

    def get_agents(self) -> List[Dict]:
        """Get all current agents."""
        return self._get('agents')

    # ==========================================
    # Task Methods
    # ==========================================

    def update_task(
        self,
        ticker: str,
        company: Optional[str] = None,
        status: Optional[TaskStatus] = None
    ) -> dict:
        """
        Update a single task in the visualizer.

        Args:
            ticker: Stock ticker symbol (required, e.g., "6682 HK")
            company: Company name
            status: Task status (active, pending, completed)

        Returns:
            API response dict
        """
        data = {'ticker': ticker}

        if company is not None: data['company'] = company
        if status is not None: data['status'] = status

        return self._post('task', data)

    def update_tasks(self, tasks: List[Dict]) -> dict:
        """
        Update multiple tasks at once.

        Args:
            tasks: List of task dicts, each must have 'ticker' field

        Returns:
            API response dict
        """
        return self._post('tasks', tasks)

    def get_tasks(self) -> List[Dict]:
        """Get all current tasks."""
        return self._get('tasks')

    # ==========================================
    # State Methods
    # ==========================================

    def get_state(self) -> dict:
        """Get full current state (agents and tasks)."""
        return self._get('state')

    # ==========================================
    # Convenience Methods
    # ==========================================

    def start_task(self, ticker: str, company: str, agent_id: str, agent_name: str = None) -> None:
        """
        Convenience method to start a new research task.

        Args:
            ticker: Stock ticker
            company: Company name
            agent_id: ID of the agent to assign
            agent_name: Optional agent display name
        """
        self.update_task(ticker, company=company, status='active')
        self.update_agent(
            agent_id,
            name=agent_name,
            status='active',
            task=f'Researching {ticker}',
            ticker=ticker,
            progress=0
        )

    def complete_task(self, ticker: str, agent_id: str) -> None:
        """
        Convenience method to mark a task as completed.

        Args:
            ticker: Stock ticker
            agent_id: ID of the agent that completed it
        """
        self.update_task(ticker, status='completed')
        self.update_agent(agent_id, status='idle', progress=100)

    def handoff(self, from_agent: str, to_agent: str, ticker: str, new_task: str) -> None:
        """
        Convenience method to hand off work from one agent to another.

        Args:
            from_agent: ID of the agent handing off
            to_agent: ID of the agent receiving
            ticker: Stock ticker being worked on
            new_task: Task description for the receiving agent
        """
        self.update_agents([
            {'id': from_agent, 'status': 'idle', 'progress': 100},
            {'id': to_agent, 'status': 'active', 'task': new_task, 'ticker': ticker, 'progress': 0}
        ])


# ==========================================
# Quick Demo
# ==========================================

if __name__ == '__main__':
    import time

    print("Claude Minions Client Demo")
    print("=" * 40)

    client = MinionsClient()

    # Check connection
    state = client.get_state()
    if not state:
        print("Could not connect to server. Make sure 'Start Server.bat' is running.")
        exit(1)

    print(f"Connected! Current agents: {len(state.get('agents', []))}")
    print()

    # Demo: Update researcher progress
    print("Demo: Updating researcher-1 progress...")
    for progress in range(10, 101, 10):
        client.update_agent('researcher-1', progress=progress, task=f'Gathering data... {progress}%')
        print(f"  Progress: {progress}%")
        time.sleep(0.5)

    print()
    print("Demo complete! Check the visualizer for updates.")
