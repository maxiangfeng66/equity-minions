"""
Visualizer Bridge - Real-time state updates for minions.html

Writes workflow state to JSON file that the visualizer polls.
Auto-opens browser when workflow starts.
"""

import json
import os
import webbrowser
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class VisualizerBridge:
    """Bridge between workflow agents and the visualizer"""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(exist_ok=True)
        self.state_file = self.context_dir / "visualizer_state.json"
        self.server_process = None
        self._state = {
            "status": "idle",
            "ticker": None,
            "company_name": None,
            "start_time": None,
            "last_updated": None,
            "agents": {},
            "connections": [],
            "chat_log": [],
            "progress": 0,
            "nodes_done": 0,
            "total_nodes": 28,  # V4 workflow nodes
            "iterations": 0,
            "total_chars": 0
        }
        self._save_state()

    @classmethod
    def get_instance(cls, context_dir: str = "context") -> 'VisualizerBridge':
        """Get singleton instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(context_dir)
            return cls._instance

    def _save_state(self):
        """Save current state to JSON file"""
        self._state["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2)

    def _add_chat(self, agent: str, message: str, provider: str = "system"):
        """Add chat log entry"""
        self._state["chat_log"].append({
            "agent": agent,
            "message": message,
            "provider": provider,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        # Keep last 100 messages
        if len(self._state["chat_log"]) > 100:
            self._state["chat_log"] = self._state["chat_log"][-100:]

    def start_server(self, port: int = 8765):
        """Start the HTTP server in background and open browser"""
        import subprocess
        import sys

        # Start server as subprocess
        server_script = Path(__file__).parent / "serve_visualizer.py"
        if server_script.exists():
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script), str(port)],
                cwd=str(Path(__file__).parent.parent)
            )
            time.sleep(0.5)  # Let server start

            # Open browser
            webbrowser.open(f"http://localhost:{port}")
            return True
        return False

    def open_visualizer(self, port: int = 8765):
        """Open visualizer in browser (starts server if needed)"""
        import socket

        # Check if server is already running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result != 0:
            # Server not running, start it
            self.start_server(port)
        else:
            # Server running, just open browser
            webbrowser.open(f"http://localhost:{port}")

    def start_research(self, ticker: str, company_name: str):
        """Start research for a ticker"""
        self._state["status"] = "running"
        self._state["ticker"] = ticker
        self._state["company_name"] = company_name
        self._state["start_time"] = datetime.now().isoformat()
        self._state["progress"] = 0
        self._state["nodes_done"] = 0
        self._state["agents"] = {}
        self._state["connections"] = []

        self._add_chat("SYSTEM", f"Starting research: {ticker}", "system")
        self._save_state()

    def node_start(self, node_id: str, provider: str = "openai", task: str = None):
        """Mark node as started/thinking"""
        self._state["agents"][node_id] = {
            "status": "thinking",
            "provider": provider,
            "message": "Working...",
            "start_time": datetime.now().isoformat(),
            "task": task[:500] if task else None,  # Store task description (truncated)
            "output": None
        }
        self._add_chat(node_id, "Analyzing...", provider)
        self._save_state()

    def node_progress(self, node_id: str, message: str, chars: int = 0):
        """Update node progress"""
        if node_id in self._state["agents"]:
            self._state["agents"][node_id]["message"] = message[:50]
        if chars > 0:
            self._state["total_chars"] += chars
        self._save_state()

    def node_output(self, node_id: str, output: str):
        """Store node output for display in modal"""
        if node_id in self._state["agents"]:
            # Store truncated output (keep first 5000 chars for display)
            self._state["agents"][node_id]["output"] = output[:5000] if output else None
            self._state["agents"][node_id]["output_length"] = len(output) if output else 0
        self._save_state()

    def node_complete(self, node_id: str, output_length: int = 0, output: str = None):
        """Mark node as complete"""
        if node_id in self._state["agents"]:
            self._state["agents"][node_id]["status"] = "complete"
            self._state["agents"][node_id]["message"] = "Done!"
            if output:
                self._state["agents"][node_id]["output"] = output[:5000]
                self._state["agents"][node_id]["output_length"] = len(output)

        self._state["nodes_done"] += 1
        self._state["progress"] = min(100, int((self._state["nodes_done"] / self._state["total_nodes"]) * 100))

        if output_length > 0:
            self._state["total_chars"] += output_length

        self._add_chat(node_id, "Complete!", self._state["agents"].get(node_id, {}).get("provider", "system"))
        self._save_state()

    def node_error(self, node_id: str, error: str):
        """Mark node as error"""
        if node_id in self._state["agents"]:
            self._state["agents"][node_id]["status"] = "error"
            self._state["agents"][node_id]["message"] = "ERROR!"
            self._state["agents"][node_id]["output"] = f"Error occurred:\n{error}"

        self._add_chat(node_id, f"Error: {error[:30]}", "error")
        self._save_state()

    def activate_connection(self, from_node: str, to_node: str):
        """Activate a connection between nodes"""
        conn = {"from": from_node, "to": to_node, "status": "active"}
        # Remove existing connection if any
        self._state["connections"] = [c for c in self._state["connections"]
                                       if not (c["from"] == from_node and c["to"] == to_node)]
        self._state["connections"].append(conn)
        self._save_state()

    def complete_connection(self, from_node: str, to_node: str):
        """Mark connection as complete"""
        for conn in self._state["connections"]:
            if conn["from"] == from_node and conn["to"] == to_node:
                conn["status"] = "complete"
        self._save_state()

    def iteration_start(self, iteration: int):
        """Mark start of new iteration/round"""
        self._state["iterations"] = iteration
        self._add_chat("SYSTEM", f"Round {iteration} started", "system")
        self._save_state()

    def update_phase(self, ticker: str, phase: str, progress: int = None):
        """Update current phase and activate corresponding agents"""
        if progress is not None:
            self._state["progress"] = min(100, progress)
        # Map phases to agent nodes
        phase_to_agents = {
            "data_gathering": [("Market Data Collector", "google"), ("Data Verifier", "openai")],
            "industry_analysis": [("Industry Deep Dive", "openai")],
            "company_analysis": [("Company Deep Dive", "openai")],
            "dcf_valuation": [("Financial Modeler", "google"), ("Pre-Model Validator", "openai")],
            "scenario_analysis": [("Assumption Challenger", "openai"), ("Sensitivity Auditor", "openai")],
            "debate": [("Debate Moderator", "openai"), ("Bull Advocate R1", "xai"), ("Bear Advocate R1", "dashscope")],
            "synthesis": [("Synthesizer", "openai"), ("Quality Supervisor", "openai")],
            "report_generation": [("Synthesizer", "openai")]
        }

        phase_messages = {
            "data_gathering": "Gathering market data...",
            "industry_analysis": "Analyzing industry...",
            "company_analysis": "Deep dive on company...",
            "dcf_valuation": "Building DCF model...",
            "scenario_analysis": "Running scenarios...",
            "debate": "Bull vs Bear debate...",
            "synthesis": "Synthesizing findings...",
            "report_generation": "Generating report..."
        }

        # Complete previous agents
        for node_id, agent in self._state["agents"].items():
            if agent["status"] == "thinking":
                agent["status"] = "complete"
                agent["message"] = "Done!"
                self._state["nodes_done"] += 1

        # Activate new phase agents
        if phase in phase_to_agents:
            for node_id, provider in phase_to_agents[phase]:
                self._state["agents"][node_id] = {
                    "status": "thinking",
                    "provider": provider,
                    "message": "Working...",
                    "start_time": datetime.now().isoformat()
                }

        msg = phase_messages.get(phase, phase)
        self._add_chat("SYSTEM", msg, "system")
        self._save_state()

    def update_progress(self, ticker: str, progress: int, message: str = ""):
        """Update overall progress"""
        self._state["progress"] = min(100, progress)
        if message:
            self._add_chat("SYSTEM", message, "system")
        self._save_state()

    def complete_research(self, ticker: str):
        """Mark research as complete"""
        self._state["status"] = "complete"
        self._state["progress"] = 100
        self._add_chat("SYSTEM", f"Research complete: {ticker}", "system")
        self._save_state()

    def error_research(self, ticker: str, error: str):
        """Mark research as error"""
        self._state["status"] = "error"
        self._add_chat("SYSTEM", f"Error: {error[:50]}", "error")
        self._save_state()

    def set_all_tasks(self, tasks: List[Dict]):
        """Set all tasks (for multi-equity runs)"""
        self._state["all_tasks"] = tasks
        self._save_state()

    def stop_server(self):
        """Stop the HTTP server"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None