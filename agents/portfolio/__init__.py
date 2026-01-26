"""
Portfolio-Level Agents for Multi-Equity Research

This module provides agents that operate at the portfolio level,
coordinating multiple equity research workflows and ensuring consistency.

Agents:
- PortfolioOrchestrator: Assigns tickers to workflow slots, identifies synergies
- CrossEquityAnalyst: Compares valuations across equities, finds relative value
- TemplateEnforcer: Pre/post validation of HTML template compliance
"""

from .portfolio_orchestrator import PortfolioOrchestrator
from .cross_equity_analyst import CrossEquityAnalyst
from .template_enforcer import TemplateEnforcer

__all__ = [
    'PortfolioOrchestrator',
    'CrossEquityAnalyst',
    'TemplateEnforcer'
]
