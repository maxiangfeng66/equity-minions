"""
Base Agent Class - Foundation for all research agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class AgentMessage:
    """Represents a message in agent communication"""
    role: str  # analyst, critic, bull, bear, synthesizer
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ResearchContext:
    """Context for equity research"""
    ticker: str
    company_name: str
    sector: str
    industry: str

    # Research data
    industry_analysis: str = ""
    company_analysis: str = ""
    governance_analysis: str = ""
    financial_data: Dict[str, Any] = field(default_factory=dict)

    # Valuation
    dcf_assumptions: Dict[str, Any] = field(default_factory=dict)
    scenario_analysis: Dict[str, Any] = field(default_factory=dict)
    intrinsic_values: Dict[str, float] = field(default_factory=dict)

    # Debate history
    debate_log: List[AgentMessage] = field(default_factory=list)

    # External research
    external_sources: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "industry": self.industry,
            "industry_analysis": self.industry_analysis,
            "company_analysis": self.company_analysis,
            "governance_analysis": self.governance_analysis,
            "financial_data": self.financial_data,
            "dcf_assumptions": self.dcf_assumptions,
            "scenario_analysis": self.scenario_analysis,
            "intrinsic_values": self.intrinsic_values,
            "debate_log": [m.to_dict() for m in self.debate_log],
            "external_sources": self.external_sources
        }

    def save(self, filepath: str):
        """Save context to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> 'ResearchContext':
        """Load context from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ctx = cls(
            ticker=data["ticker"],
            company_name=data["company_name"],
            sector=data["sector"],
            industry=data["industry"]
        )
        ctx.industry_analysis = data.get("industry_analysis", "")
        ctx.company_analysis = data.get("company_analysis", "")
        ctx.governance_analysis = data.get("governance_analysis", "")
        ctx.financial_data = data.get("financial_data", {})
        ctx.dcf_assumptions = data.get("dcf_assumptions", {})
        ctx.scenario_analysis = data.get("scenario_analysis", {})
        ctx.intrinsic_values = data.get("intrinsic_values", {})
        ctx.external_sources = data.get("external_sources", [])

        # Reconstruct debate log
        for msg_data in data.get("debate_log", []):
            msg = AgentMessage(
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata", {})
            )
            ctx.debate_log.append(msg)

        return ctx


class BaseAgent(ABC):
    """Base class for all research agents"""

    def __init__(self, ai_provider, role: str):
        self.ai_provider = ai_provider
        self.role = role
        self.system_prompt = self._get_system_prompt()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Define the agent's system prompt/personality"""
        pass

    @abstractmethod
    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Perform analysis on the given context"""
        pass

    async def respond(self, prompt: str) -> str:
        """Generate a response using the AI provider"""
        return await self.ai_provider.generate(prompt, self.system_prompt)

    def create_message(self, content: str, metadata: Dict[str, Any] = None) -> AgentMessage:
        """Create a message from this agent"""
        return AgentMessage(
            role=self.role,
            content=content,
            metadata=metadata or {}
        )
