"""
Valuation Module - Multi-Method Valuation with Cross-Check

This module provides multiple valuation methods that all receive the SAME inputs,
then cross-checks results to ensure consistency and catch errors.

Methods:
- DCF (Discounted Cash Flow)
- Comps (Comparable Company Analysis)
- DDM (Dividend Discount Model)
- Reverse DCF (What growth does current price imply?)

All methods use Python math, not AI hallucination.

NEW: Multi-AI Assumption Extraction
- No more hardcoded defaults
- Extracts assumptions from broker research, public data, and AI debates
- Uses AI agents to reconcile multiple data sources
"""

from .assumption_extractor import (
    AssumptionExtractor,
    MultiAIAssumptionExtractor,  # NEW: Multi-AI extraction
    ValuationInputs,
    extract_assumptions_multi_ai  # NEW: Convenience function
)
from .assumption_agents import (  # NEW: AI-powered extraction agents
    BrokerDataExtractor,
    PublicDataCollector,
    DebateInsightsSynthesizer,
    AssumptionReconciler,
    extract_validated_assumptions,
    ExtractedAssumptions
)
from .engines import DCFEngine, CompsEngine, DDMEngine, ReverseDCFEngine
from .cross_checker import CrossChecker, CrossCheckResult
from .consensus_builder import ConsensusBuilder, ConsensusValuation
from .valuation_orchestrator import ValuationOrchestrator, run_valuation_node

__all__ = [
    # Assumption extraction
    'AssumptionExtractor',
    'MultiAIAssumptionExtractor',  # NEW
    'ValuationInputs',
    'extract_assumptions_multi_ai',  # NEW
    # AI agents for extraction
    'BrokerDataExtractor',  # NEW
    'PublicDataCollector',  # NEW
    'DebateInsightsSynthesizer',  # NEW
    'AssumptionReconciler',  # NEW
    'extract_validated_assumptions',  # NEW
    'ExtractedAssumptions',  # NEW
    # Valuation engines
    'DCFEngine',
    'CompsEngine',
    'DDMEngine',
    'ReverseDCFEngine',
    # Cross-check and consensus
    'CrossChecker',
    'CrossCheckResult',
    'ConsensusBuilder',
    'ConsensusValuation',
    # Main orchestrator
    'ValuationOrchestrator',
    'run_valuation_node'
]
