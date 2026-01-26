"""
Context Manager - Handles session persistence to avoid losing context
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ContextManager:
    """Manages session state and context persistence"""

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(exist_ok=True)
        self.session_file = self.context_dir / "session_state.json"
        self.session_state = self._load_session()

    def _load_session(self) -> Dict[str, Any]:
        """Load existing session state"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass

        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "equities_completed": [],
            "equities_in_progress": [],
            "equities_pending": [],
            "current_phase": "initialization",
            "errors": [],
            "summary": ""
        }

    def save_session(self):
        """Save current session state"""
        self.session_state["last_updated"] = datetime.now().isoformat()
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_state, f, indent=2, ensure_ascii=False)

    def mark_equity_started(self, ticker: str):
        """Mark an equity as in progress"""
        if ticker not in self.session_state["equities_in_progress"]:
            self.session_state["equities_in_progress"].append(ticker)
        if ticker in self.session_state["equities_pending"]:
            self.session_state["equities_pending"].remove(ticker)
        self.save_session()

    def mark_equity_completed(self, ticker: str):
        """Mark an equity as completed"""
        if ticker not in self.session_state["equities_completed"]:
            self.session_state["equities_completed"].append(ticker)
        if ticker in self.session_state["equities_in_progress"]:
            self.session_state["equities_in_progress"].remove(ticker)
        self.save_session()

    def mark_equity_error(self, ticker: str, error: str):
        """Record an error for an equity"""
        self.session_state["errors"].append({
            "ticker": ticker,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save_session()

    def set_pending_equities(self, tickers: list):
        """Set the list of equities to process"""
        self.session_state["equities_pending"] = [
            t for t in tickers
            if t not in self.session_state["equities_completed"]
            and t not in self.session_state["equities_in_progress"]
        ]
        self.save_session()

    def get_remaining_equities(self) -> list:
        """Get list of equities not yet completed"""
        return (
            self.session_state["equities_pending"] +
            self.session_state["equities_in_progress"]
        )

    def is_completed(self, ticker: str) -> bool:
        """Check if an equity has been completed"""
        return ticker in self.session_state.get("equities_completed", [])

    def save_equity_context(self, ticker: str, context_data: Dict[str, Any]):
        """Save individual equity research context"""
        filename = self.context_dir / f"{ticker.replace(' ', '_')}_context.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False)

    def load_equity_context(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Load individual equity research context"""
        filename = self.context_dir / f"{ticker.replace(' ', '_')}_context.json"
        if filename.exists():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return None

    def update_summary(self, summary: str):
        """Update the overall session summary"""
        self.session_state["summary"] = summary
        self.save_session()

    def get_status_report(self) -> str:
        """Generate a status report"""
        completed = len(self.session_state["equities_completed"])
        in_progress = len(self.session_state["equities_in_progress"])
        pending = len(self.session_state["equities_pending"])
        errors = len(self.session_state["errors"])

        return f"""
Session Status Report
=====================
Created: {self.session_state["created_at"]}
Last Updated: {self.session_state["last_updated"]}

Progress:
- Completed: {completed} equities
- In Progress: {in_progress} equities
- Pending: {pending} equities
- Errors: {errors}

Completed Equities: {', '.join(self.session_state["equities_completed"]) or 'None'}
In Progress: {', '.join(self.session_state["equities_in_progress"]) or 'None'}
Pending: {', '.join(self.session_state["equities_pending"]) or 'None'}
"""

    def clear_session(self):
        """Clear the session state (start fresh)"""
        self.session_state = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "equities_completed": [],
            "equities_in_progress": [],
            "equities_pending": [],
            "current_phase": "initialization",
            "errors": [],
            "summary": ""
        }
        self.save_session()
