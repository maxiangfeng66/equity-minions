"""
Hierarchical Debate System - Full integration of spawnable agent architecture

This system orchestrates equity research using the new hierarchical agent structure:
- Tier 0: Architect agents (strategy and resource allocation)
- Tier 1: Supervisor agents (research and debate management)
- Tier 2: Worker agents (analysis execution)
- Tier 3: Goalkeeper agents (quality gates)

Key features:
- Dynamic agent spawning and termination
- Supervisor health monitoring
- Quality gates before publishing
- Full visualizer integration
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from .base_agent import ResearchContext, AgentMessage
from .ai_providers import AIProviderManager

# Import new hierarchical components
from .core.agent_registry import AgentRegistry
from .core.spawnable_agent import SpawnableAgent, set_global_visualizer
from .core.lifecycle import AgentLifecycleState

# Import architect agents
from .architects.chief_architect import ChiefArchitectAgent
from .architects.resource_allocator import ResourceAllocatorAgent
from .architects.priority_manager import PriorityManagerAgent

# Import supervisor agents
from .supervisors.research_supervisor import ResearchSupervisor
from .supervisors.debate_moderator import DebateModerator

# Import goalkeeper agents
from .goalkeepers.publish_gatekeeper import PublishGatekeeperAgent


class HierarchicalDebateSystem:
    """
    Full hierarchical equity research system.

    Architecture:
    - ChiefArchitect creates research pools with supervisors
    - ResearchSupervisor manages worker agents for each equity
    - DebateModerator orchestrates multi-agent debates
    - PublishGatekeeper ensures quality before publishing

    Usage:
        ai_manager = AIProviderManager(config)
        system = HierarchicalDebateSystem(ai_manager)

        # Run research on multiple equities
        results = await system.run_research_batch(equities)

        # Each result includes quality gate status
        for ticker, result in results.items():
            if result['approved']:
                # Safe to publish
                generate_report(result['context'])
    """

    def __init__(
        self,
        ai_manager: AIProviderManager,
        max_concurrent: int = 3,
        debate_rounds: int = 10,
        require_quality_gates: bool = True
    ):
        self.ai_manager = ai_manager
        self.max_concurrent = max_concurrent
        self.debate_rounds = debate_rounds
        self.require_quality_gates = require_quality_gates

        # Initialize global registry
        self.registry = AgentRegistry()
        SpawnableAgent._registry = self.registry

        # Get primary provider for architects
        providers = ai_manager.get_all_providers()
        self.primary_provider = providers[0] if providers else None

        # Initialize architect agents (Tier 0)
        self.chief_architect = None
        self.resource_allocator = None
        self.priority_manager = None

        # Progress callback
        self.progress_callback: Optional[Callable] = None

        # Visualizer bridge (optional)
        self._visualizer = None

    def set_visualizer(self, visualizer):
        """Set visualizer bridge for real-time updates"""
        self._visualizer = visualizer
        # Set global visualizer for all SpawnableAgent instances
        set_global_visualizer(visualizer)

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self.progress_callback = callback

    def _report_progress(self, message: str):
        """Report progress to callback if set"""
        if self.progress_callback:
            self.progress_callback(message)
        print(f"[HierarchicalDebate] {message}")

    async def initialize(self):
        """Initialize architect agents"""
        self._report_progress("Initializing hierarchical system...")

        # Create resource allocator (manages AI providers)
        self.resource_allocator = ResourceAllocatorAgent(
            ai_provider=self.primary_provider,
            ai_manager=self.ai_manager,
            config={'max_provider_errors': 5}
        )
        await self.resource_allocator.activate()

        # Create priority manager
        self.priority_manager = PriorityManagerAgent(
            ai_provider=self.primary_provider,
            config={'max_queue_size': 100}
        )
        await self.priority_manager.activate()

        # Create chief architect
        self.chief_architect = ChiefArchitectAgent(
            ai_provider=self.primary_provider,
            config={
                'default_quality_threshold': 0.7,
                'max_concurrent': self.max_concurrent
            }
        )
        await self.chief_architect.activate()

        self._report_progress("Architect agents initialized")

        # Sync with visualizer
        if self._visualizer:
            self._visualizer.sync_from_registry(self.registry)

    async def shutdown(self):
        """Gracefully shutdown all agents"""
        self._report_progress("Shutting down hierarchical system...")

        # Terminate in reverse order (workers -> supervisors -> architects)
        if self.chief_architect:
            await self.chief_architect.terminate(graceful=True)

        if self.priority_manager:
            await self.priority_manager.terminate(graceful=True)

        if self.resource_allocator:
            await self.resource_allocator.terminate(graceful=True)

        # Reset registry
        self.registry.reset()

        self._report_progress("System shutdown complete")

    async def run_research_batch(
        self,
        equities: Dict[str, Dict[str, str]],
        prioritize: bool = True
    ) -> Dict[str, Dict]:
        """
        Run research on a batch of equities.

        Args:
            equities: Dict of ticker -> {name, sector, industry}
            prioritize: Whether to use priority scoring

        Returns:
            Dict of ticker -> {
                'context': ResearchContext,
                'approved': bool,
                'gate_results': Dict,
                'error': Optional[str]
            }
        """
        if not self.chief_architect:
            await self.initialize()

        results = {}

        # Add equities to priority queue
        if prioritize:
            for ticker, info in equities.items():
                self.priority_manager.add_ticker(
                    ticker=ticker,
                    company=info.get('name', ticker),
                    metadata={
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown')
                    }
                )

        # Create research pool
        tickers = list(equities.keys())
        self._report_progress(f"Creating research pool for {len(tickers)} equities")

        supervisor = await self.chief_architect.create_research_pool(
            pool_name="main_pool",
            tickers=tickers,
            priority="normal"
        )

        # Assign equities to supervisor
        for ticker, info in equities.items():
            context = ResearchContext(
                ticker=ticker,
                company_name=info.get('name', ticker),
                sector=info.get('sector', 'Unknown'),
                industry=info.get('industry', 'Unknown')
            )
            await supervisor.assign_ticker(ticker, context)

        # Run all research
        self._report_progress("Starting research execution...")
        research_results = await supervisor.start_all_research()

        # Run quality gates for each result
        for ticker, context in research_results.items():
            if isinstance(context, Exception):
                results[ticker] = {
                    'context': None,
                    'approved': False,
                    'gate_results': None,
                    'error': str(context)
                }
                continue

            # Run quality gates
            if self.require_quality_gates:
                self._report_progress(f"Running quality gates for {ticker}")
                gate_results = await self._run_quality_gates(ticker, context)

                results[ticker] = {
                    'context': context,
                    'approved': gate_results.get('approved', False),
                    'gate_results': gate_results,
                    'error': None
                }

                if gate_results['approved']:
                    self._report_progress(f"✓ {ticker} approved for publishing")
                else:
                    blockers = gate_results.get('blockers', [])
                    self._report_progress(f"✗ {ticker} blocked: {len(blockers)} issues")
            else:
                results[ticker] = {
                    'context': context,
                    'approved': True,
                    'gate_results': None,
                    'error': None
                }

        # Sync with visualizer
        if self._visualizer:
            self._visualizer.sync_from_registry(self.registry)

        return results

    async def _run_quality_gates(self, ticker: str, context: ResearchContext) -> Dict:
        """Run quality gates for a completed research context"""

        # Get provider for gatekeeper
        provider = self.resource_allocator.get_provider_for_role('fact_checker')
        if not provider:
            provider = self.primary_provider

        # Create publish gatekeeper
        gatekeeper = PublishGatekeeperAgent(
            ai_provider=provider,
            config={'ticker': ticker}
        )
        await gatekeeper.activate()

        try:
            # Run all quality gates
            result = await gatekeeper.run_all_gates(context)
            return result
        finally:
            await gatekeeper.terminate()

    async def run_single_research(
        self,
        ticker: str,
        company_name: str,
        sector: str = "Unknown",
        industry: str = "Unknown"
    ) -> Dict:
        """
        Run research on a single equity.

        Convenience method for single-equity research.
        """
        return (await self.run_research_batch({
            ticker: {
                'name': company_name,
                'sector': sector,
                'industry': industry
            }
        }))[ticker]

    def get_registry_stats(self) -> Dict:
        """Get statistics about current agent registry"""
        return self.registry.get_stats()

    def get_agent_hierarchy(self) -> Dict:
        """Get full agent hierarchy tree"""
        return self.registry.get_hierarchy_tree()


class HierarchicalParallelRunner:
    """
    Parallel runner using hierarchical system.

    Manages multiple concurrent research tasks with proper
    resource allocation and quality gates.
    """

    def __init__(
        self,
        ai_manager: AIProviderManager,
        max_concurrent: int = 3,
        debate_rounds: int = 10
    ):
        self.system = HierarchicalDebateSystem(
            ai_manager=ai_manager,
            max_concurrent=max_concurrent,
            debate_rounds=debate_rounds
        )

    async def run_all(
        self,
        equities: Dict[str, Dict[str, str]],
        progress_callback: Callable = None,
        visualizer=None
    ) -> Dict[str, ResearchContext]:
        """
        Run research for all equities with hierarchical system.

        Args:
            equities: Dict of ticker -> {name, sector, industry}
            progress_callback: Optional callback for progress updates
            visualizer: Optional VisualizerBridge instance

        Returns:
            Dict of ticker -> ResearchContext (only approved results)
        """
        if progress_callback:
            self.system.set_progress_callback(progress_callback)

        if visualizer:
            self.system.set_visualizer(visualizer)

        try:
            await self.system.initialize()

            # Run batch research
            results = await self.system.run_research_batch(equities)

            # Filter to only approved results
            approved_results = {}
            for ticker, result in results.items():
                if result['approved'] and result['context']:
                    approved_results[ticker] = result['context']
                elif result['error']:
                    print(f"[{ticker}] Error: {result['error']}")
                elif not result['approved']:
                    blockers = result.get('gate_results', {}).get('blockers', [])
                    print(f"[{ticker}] Not approved: {blockers}")

            return approved_results

        finally:
            await self.system.shutdown()
