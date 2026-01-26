"""
Worker Agents - Tier 2 task execution agents
"""

from .enhanced_workers import (
    EnhancedAnalystAgent,
    EnhancedBullAgent,
    EnhancedBearAgent,
    EnhancedCriticAgent,
    EnhancedSynthesizerAgent
)
from .devils_advocate import DevilsAdvocateAgent
from .specialist import SpecialistAgent

__all__ = [
    'EnhancedAnalystAgent',
    'EnhancedBullAgent',
    'EnhancedBearAgent',
    'EnhancedCriticAgent',
    'EnhancedSynthesizerAgent',
    'DevilsAdvocateAgent',
    'SpecialistAgent'
]
