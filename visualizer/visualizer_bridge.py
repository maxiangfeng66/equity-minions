"""
Visualizer Bridge - Real-time sync between research system and visualizer

This module provides:
1. Direct JSON file updates (works without server)
2. Optional server push updates (works with server.py running)
3. Auto-syncs agent status, progress, and task completion

Usage:
    from visualizer.visualizer_bridge import VisualizerBridge

    viz = VisualizerBridge()
    viz.start_research("6682 HK", "Haidilao International")
    viz.update_progress("6682 HK", 50, "Running DCF analysis")
    viz.complete_research("6682 HK")
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Optional, Dict, List, Literal
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

AgentType = Literal['orchestrator', 'researcher', 'analyst', 'critic', 'debater', 'bull', 'bear', 'synthesizer']
AgentStatus = Literal['active', 'waiting', 'idle']


class VisualizerBridge:
    """
    Bridge between research system and visualizer.
    Supports both file-based and server-based updates.
    """

    def __init__(self, context_dir: str = "context", server_url: str = "http://localhost:8080"):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(exist_ok=True)

        self.server_url = server_url
        self.server_available = False
        self.minions_file = self.context_dir / "minions_state.json"

        # Agent tracking
        self.agents: Dict[str, dict] = {}
        self.tasks: Dict[str, dict] = {}
        self.active_research: Dict[str, str] = {}  # ticker -> agent_id

        # Initialize default agents
        self._init_default_agents()

        # Check server availability
        self._check_server()

        # Load existing state
        self._load_state()

    def _init_default_agents(self):
        """Initialize default agent structure"""
        positions = [
            {'x': 0, 'z': -2},   # Orchestrator
            {'x': -4, 'z': 2},   # Researcher 1
            {'x': 0, 'z': 2},    # Researcher 2
            {'x': 4, 'z': 2},    # Researcher 3
            {'x': -4, 'z': 5},   # Analyst
            {'x': 0, 'z': 5},    # Critic
            {'x': 4, 'z': 5},    # Synthesizer
        ]

        self.agents = {
            'orchestrator': {
                'id': 'orchestrator',
                'name': 'Orchestrator',
                'type': 'orchestrator',
                'status': 'active',
                'task': 'Coordinating research',
                'progress': 0,
                'tier': 0,
                'position': positions[0],
                'connections': []
            },
            'researcher-1': {
                'id': 'researcher-1',
                'name': 'Researcher Alpha',
                'type': 'researcher',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 1,
                'position': positions[1],
                'connections': []
            },
            'researcher-2': {
                'id': 'researcher-2',
                'name': 'Researcher Beta',
                'type': 'researcher',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 1,
                'position': positions[2],
                'connections': []
            },
            'researcher-3': {
                'id': 'researcher-3',
                'name': 'Researcher Gamma',
                'type': 'researcher',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 1,
                'position': positions[3],
                'connections': []
            },
            'analyst-1': {
                'id': 'analyst-1',
                'name': 'Analyst Delta',
                'type': 'analyst',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 2,
                'position': positions[4],
                'connections': []
            },
            'critic-1': {
                'id': 'critic-1',
                'name': 'Critic Epsilon',
                'type': 'critic',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 2,
                'position': positions[5],
                'connections': []
            },
            'synthesizer-1': {
                'id': 'synthesizer-1',
                'name': 'Synthesizer Zeta',
                'type': 'debater',
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'tier': 2,
                'position': positions[6],
                'connections': []
            }
        }

        # Set orchestrator connections
        self.agents['orchestrator']['connections'] = [
            {'to': 'researcher-1', 'type': 'command'},
            {'to': 'researcher-2', 'type': 'command'},
            {'to': 'researcher-3', 'type': 'command'},
        ]

    def _check_server(self):
        """Check if visualizer server is running"""
        if not HAS_REQUESTS:
            self.server_available = False
            return

        try:
            resp = requests.get(f"{self.server_url}/api/state", timeout=2)
            self.server_available = resp.status_code == 200
        except:
            self.server_available = False

        if self.server_available:
            print("[Visualizer] Server connected at", self.server_url)
        else:
            print("[Visualizer] Server not available, using file-based updates")

    def _load_state(self):
        """Load existing state from minions_state.json"""
        if self.minions_file.exists():
            try:
                with open(self.minions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'agents' in data:
                        for agent in data['agents']:
                            self.agents[agent['id']] = agent
                    if 'tasks' in data:
                        for task in data['tasks']:
                            self.tasks[task.get('ticker', task.get('id'))] = task
            except Exception as e:
                print(f"[Visualizer] Could not load state: {e}")

    def _save_state(self):
        """Save current state to minions_state.json"""
        state = {
            'agents': list(self.agents.values()),
            'tasks': list(self.tasks.values()),
            'last_updated': datetime.now().isoformat()
        }

        try:
            with open(self.minions_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Visualizer] Could not save state: {e}")

        # Also push to server if available
        if self.server_available and HAS_REQUESTS:
            try:
                requests.post(f"{self.server_url}/api/agents", json=list(self.agents.values()), timeout=2)
                requests.post(f"{self.server_url}/api/tasks", json=list(self.tasks.values()), timeout=2)
            except:
                pass

    def _get_free_researcher(self) -> Optional[str]:
        """Find an idle researcher agent"""
        for agent_id, agent in self.agents.items():
            if agent['type'] == 'researcher' and agent['status'] == 'idle':
                return agent_id
        return None

    # ==========================================
    # Public API - Research Lifecycle
    # ==========================================

    def start_research(self, ticker: str, company: str) -> str:
        """
        Start research on a ticker. Assigns a researcher agent.
        Returns the assigned agent ID.
        """
        # Find free researcher
        agent_id = self._get_free_researcher()
        if not agent_id:
            # All researchers busy, use first one
            agent_id = 'researcher-1'

        # Update task
        self.tasks[ticker] = {
            'ticker': ticker,
            'company': company,
            'status': 'active',
            'started_at': datetime.now().isoformat()
        }

        # Update agent
        self.agents[agent_id].update({
            'status': 'active',
            'task': f'Researching {ticker}',
            'ticker': ticker,
            'progress': 0
        })

        # Track assignment
        self.active_research[ticker] = agent_id

        # Update orchestrator
        active_count = sum(1 for a in self.agents.values() if a['status'] == 'active')
        self.agents['orchestrator']['task'] = f'Coordinating {active_count} active research tasks'
        self.agents['orchestrator']['progress'] = self._calculate_overall_progress()

        self._save_state()
        print(f"[Visualizer] Started research: {ticker} -> {agent_id}")

        return agent_id

    def update_progress(self, ticker: str, progress: int, task_description: str = None):
        """Update progress for a research task"""
        agent_id = self.active_research.get(ticker)
        if not agent_id:
            return

        self.agents[agent_id]['progress'] = max(0, min(100, progress))
        if task_description:
            self.agents[agent_id]['task'] = task_description

        # Update orchestrator progress
        self.agents['orchestrator']['progress'] = self._calculate_overall_progress()

        self._save_state()

    def update_phase(self, ticker: str, phase: str, progress: int = None):
        """Update the current phase of research"""
        agent_id = self.active_research.get(ticker)
        if not agent_id:
            return

        phase_map = {
            'data_gathering': ('Gathering market data', 10),
            'industry_analysis': ('Analyzing industry', 25),
            'company_analysis': ('Analyzing company', 40),
            'dcf_valuation': ('Running DCF model', 55),
            'scenario_analysis': ('Scenario analysis', 70),
            'debate': ('Multi-AI debate', 85),
            'synthesis': ('Synthesizing results', 95),
            'report_generation': ('Generating report', 98),
        }

        task_desc, default_progress = phase_map.get(phase, (phase, progress or 50))
        actual_progress = progress if progress is not None else default_progress

        self.agents[agent_id]['task'] = f'{ticker}: {task_desc}'
        self.agents[agent_id]['progress'] = actual_progress

        self._save_state()

    def complete_research(self, ticker: str):
        """Mark research as completed"""
        agent_id = self.active_research.get(ticker)

        # Update task
        if ticker in self.tasks:
            self.tasks[ticker]['status'] = 'completed'
            self.tasks[ticker]['completed_at'] = datetime.now().isoformat()

        # Update agent
        if agent_id and agent_id in self.agents:
            self.agents[agent_id].update({
                'status': 'idle',
                'task': 'Standing by',
                'ticker': None,
                'progress': 0
            })

        # Remove from active
        if ticker in self.active_research:
            del self.active_research[ticker]

        # Update orchestrator
        completed = sum(1 for t in self.tasks.values() if t.get('status') == 'completed')
        total = len(self.tasks)
        self.agents['orchestrator']['task'] = f'Completed {completed}/{total} equities'
        self.agents['orchestrator']['progress'] = self._calculate_overall_progress()

        self._save_state()
        print(f"[Visualizer] Completed research: {ticker}")

    def error_research(self, ticker: str, error_msg: str):
        """Mark research as errored"""
        agent_id = self.active_research.get(ticker)

        if ticker in self.tasks:
            self.tasks[ticker]['status'] = 'error'
            self.tasks[ticker]['error'] = error_msg

        if agent_id and agent_id in self.agents:
            self.agents[agent_id].update({
                'status': 'idle',
                'task': f'Error: {error_msg[:30]}...',
                'progress': 0
            })

        if ticker in self.active_research:
            del self.active_research[ticker]

        self._save_state()

    # ==========================================
    # Debate System Integration
    # ==========================================

    def start_debate(self, ticker: str, company: str):
        """Start a debate for a ticker"""
        # Activate debate agents
        self.agents['analyst-1'].update({
            'status': 'active',
            'task': f'{ticker}: Bull analysis',
            'progress': 0
        })
        self.agents['critic-1'].update({
            'status': 'active',
            'task': f'{ticker}: Bear analysis',
            'progress': 0
        })
        self.agents['synthesizer-1'].update({
            'status': 'waiting',
            'task': f'{ticker}: Waiting for debate',
            'progress': 0
        })

        # Add debate connections
        researcher_id = self.active_research.get(ticker, 'researcher-1')
        self.agents[researcher_id]['connections'] = [
            {'to': 'analyst-1', 'type': 'data_flow'},
            {'to': 'critic-1', 'type': 'data_flow'}
        ]
        self.agents['analyst-1']['connections'] = [
            {'to': 'synthesizer-1', 'type': 'interaction'}
        ]
        self.agents['critic-1']['connections'] = [
            {'to': 'synthesizer-1', 'type': 'interaction'}
        ]

        self._save_state()
        print(f"[Visualizer] Started debate: {ticker}")

    def update_debate_round(self, ticker: str, round_num: int, total_rounds: int):
        """Update debate progress"""
        progress = int((round_num / total_rounds) * 100)

        self.agents['analyst-1']['progress'] = progress
        self.agents['analyst-1']['task'] = f'{ticker}: Bull round {round_num}/{total_rounds}'

        self.agents['critic-1']['progress'] = progress
        self.agents['critic-1']['task'] = f'{ticker}: Bear round {round_num}/{total_rounds}'

        if round_num > total_rounds * 0.7:
            self.agents['synthesizer-1']['status'] = 'active'
            self.agents['synthesizer-1']['task'] = f'{ticker}: Synthesizing debate'
            self.agents['synthesizer-1']['progress'] = int((round_num - total_rounds * 0.7) / (total_rounds * 0.3) * 100)

        self._save_state()

    def complete_debate(self, ticker: str):
        """Complete debate phase"""
        for agent_id in ['analyst-1', 'critic-1', 'synthesizer-1']:
            self.agents[agent_id].update({
                'status': 'idle',
                'task': 'Standing by',
                'progress': 0,
                'connections': []
            })

        self._save_state()
        print(f"[Visualizer] Completed debate: {ticker}")

    # ==========================================
    # Utility Methods
    # ==========================================

    def _calculate_overall_progress(self) -> int:
        """Calculate overall progress across all tasks"""
        if not self.tasks:
            return 0

        completed = sum(1 for t in self.tasks.values() if t.get('status') == 'completed')
        active_progress = sum(
            self.agents.get(self.active_research.get(t['ticker'], ''), {}).get('progress', 0)
            for t in self.tasks.values() if t.get('status') == 'active'
        )
        active_count = sum(1 for t in self.tasks.values() if t.get('status') == 'active')

        total = len(self.tasks)
        if total == 0:
            return 0

        # Each completed task = 100%, active tasks = their progress
        total_progress = (completed * 100) + active_progress
        return int(total_progress / total)

    def set_all_tasks(self, equities: List[Dict]):
        """Set all tasks from equity list"""
        self.tasks = {}
        for eq in equities:
            ticker = eq.get('ticker')
            self.tasks[ticker] = {
                'ticker': ticker,
                'company': eq.get('company', eq.get('name', '')),
                'status': eq.get('status', 'pending')
            }
        self._save_state()

    def get_state(self) -> dict:
        """Get current state"""
        return {
            'agents': list(self.agents.values()),
            'tasks': list(self.tasks.values())
        }


# Global instance for easy import
_bridge_instance = None

def get_bridge(context_dir: str = "context") -> VisualizerBridge:
    """Get or create global bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = VisualizerBridge(context_dir)
    return _bridge_instance
