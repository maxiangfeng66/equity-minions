"""
Tools module - Provides real computation and API tools for agents.

This module contains tools that give agents actual computational capabilities
rather than relying on AI to generate/hallucinate numbers.
"""

from .financial_calculator import FinancialCalculator, DCFCalculator
from .market_data_api import MarketDataAPI
from .validation_tools import ValidationTools

__all__ = [
    'FinancialCalculator',
    'DCFCalculator',
    'MarketDataAPI',
    'ValidationTools'
]
