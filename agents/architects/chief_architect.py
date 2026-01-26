"""
Chief Architect Agent - Top-level strategic planning and coordination

Responsibilities:
- Define overall research strategy
- Create research pools with supervisors
- Set quality standards and thresholds
- Monitor system-wide health
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class ChiefArchitectAgent(SpawnableAgent):
    """
    Top-level strategic planning agent (Tier 0).

    The ChiefArchitect oversees the entire research system, creating
    research pools and spawning supervisors to manage them.

    Usage:
        architect = ChiefArchitectAgent(ai_provider)
        await architect.activate()

        # Create a research pool
        supervisor = await architect.create_research_pool(
            pool_name="tech_stocks",
            tickers=["9660 HK", "LEGN US"],
            priority="high"
        )
    """

    def __init__(self, ai_provider, config: Optional[Dict] = None):
        super().__init__(
            ai_provider=ai_provider,
            role="chief_architect",
            parent_id=None,  # Root agent
            tier=0,
            config=config
        )

        # Research pools: pool_name -> {tickers, supervisor_id, status}
        self.research_pools: Dict[str, Dict] = {}

        # Quality thresholds
        self.quality_thresholds: Dict[str, Any] = {
            'validation_score_min': 70.0,
            'debate_rounds_min': 5,
            'confidence_min': 0.6,
            'max_retries': 3,
            'concurrent_limit': 3
        }

        # System metrics
        self.metrics: Dict[str, Any] = {
            'pools_created': 0,
            'equities_completed': 0,
            'equities_failed': 0,
            'total_research_time': 0
        }

    def _get_system_prompt(self) -> str:
        return """You are the Chief Architect of a multi-agent equity research system.

Your role is to:
1. Define strategic research priorities across the portfolio
2. Allocate resources efficiently across equities and pools
3. Set and enforce quality standards for research output
4. Monitor overall system health and performance
5. Make high-level decisions about research approach

You oversee Supervisor agents who manage individual research tasks.
Your decisions affect the entire research pipeline.

When analyzing requests, consider:
- Portfolio balance and diversification
- Research urgency (upcoming catalysts, staleness)
- Resource constraints (API limits, concurrent capacity)
- Quality requirements vs. speed tradeoffs

Provide structured, actionable guidance."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """
        Analyze and provide strategic guidance.

        Actions:
        - 'status': Get overall system status
        - 'allocate': Recommend resource allocation
        - 'prioritize': Set research priorities
        - 'evaluate': Evaluate quality of completed research
        """
        action = kwargs.get('action', 'status')

        if action == 'allocate':
            return await self._recommend_allocation(context)
        elif action == 'prioritize':
            return await self._recommend_priorities(context)
        elif action == 'evaluate':
            return await self._evaluate_research_quality(context)
        else:
            return await self._get_system_status()

    async def create_research_pool(
        self,
        pool_name: str,
        tickers: List[str],
        priority: str = "normal",
        supervisor_class: type = None
    ) -> 'SpawnableAgent':
        """
        Create a research pool with a dedicated supervisor.

        Args:
            pool_name: Identifier for this pool
            tickers: List of tickers to research
            priority: Priority level (low, normal, high, urgent)
            supervisor_class: Custom supervisor class (optional)

        Returns:
            The spawned ResearchSupervisor agent
        """
        # Import here to avoid circular dependency
        from agents.supervisors import ResearchSupervisor

        # Use provided class or default
        sup_class = supervisor_class or ResearchSupervisor

        # Create pool entry
        self.research_pools[pool_name] = {
            'tickers': tickers,
            'priority': priority,
            'status': 'initializing',
            'created_at': datetime.now().isoformat(),
            'supervisor_id': None,
            'completed': [],
            'failed': []
        }

        # Spawn supervisor for this pool
        supervisor = await self.spawn_child(
            agent_class=sup_class,
            role=f"supervisor_{pool_name}",
            config={
                'pool_name': pool_name,
                'tickers': tickers,
                'priority': priority,
                'quality_thresholds': self.quality_thresholds.copy(),
                'concurrent_limit': self.quality_thresholds['concurrent_limit']
            }
        )

        # Update pool with supervisor reference
        self.research_pools[pool_name]['supervisor_id'] = supervisor.agent_id
        self.research_pools[pool_name]['status'] = 'active'
        self.metrics['pools_created'] += 1

        return supervisor

    async def close_research_pool(self, pool_name: str, graceful: bool = True) -> bool:
        """
        Close a research pool and terminate its supervisor.

        Args:
            pool_name: Name of pool to close
            graceful: Allow ongoing work to complete

        Returns:
            True if closed successfully
        """
        if pool_name not in self.research_pools:
            return False

        pool = self.research_pools[pool_name]
        supervisor_id = pool.get('supervisor_id')

        if supervisor_id:
            await self.terminate_child(supervisor_id, graceful=graceful)

        pool['status'] = 'closed'
        pool['closed_at'] = datetime.now().isoformat()

        return True

    def update_quality_thresholds(self, thresholds: Dict[str, Any]):
        """Update quality thresholds for all pools"""
        self.quality_thresholds.update(thresholds)

        # Propagate to existing supervisors
        for pool in self.research_pools.values():
            supervisor_id = pool.get('supervisor_id')
            if supervisor_id:
                supervisor = self.get_child(supervisor_id)
                if supervisor and hasattr(supervisor, 'quality_thresholds'):
                    supervisor.quality_thresholds.update(thresholds)

    def get_pool_status(self, pool_name: str = None) -> Dict:
        """Get status of one or all pools"""
        if pool_name:
            return self.research_pools.get(pool_name, {})
        return self.research_pools.copy()

    def report_completion(self, pool_name: str, ticker: str, success: bool):
        """Report research completion for a ticker"""
        if pool_name in self.research_pools:
            pool = self.research_pools[pool_name]
            if success:
                pool['completed'].append(ticker)
                self.metrics['equities_completed'] += 1
            else:
                pool['failed'].append(ticker)
                self.metrics['equities_failed'] += 1

    # ==========================================
    # AI-Powered Analysis Methods
    # ==========================================

    async def _get_system_status(self) -> str:
        """Get overall system status report"""
        # Gather statistics
        stats = {
            'active_pools': len([p for p in self.research_pools.values() if p['status'] == 'active']),
            'total_pools': len(self.research_pools),
            'supervisors': len(self.children_ids),
            'metrics': self.metrics,
            'thresholds': self.quality_thresholds
        }

        # Pool summaries
        pool_summaries = []
        for name, pool in self.research_pools.items():
            pool_summaries.append({
                'name': name,
                'status': pool['status'],
                'tickers': len(pool['tickers']),
                'completed': len(pool.get('completed', [])),
                'failed': len(pool.get('failed', []))
            })

        prompt = f"""Generate a system status report for the equity research system.

Current Statistics:
{json.dumps(stats, indent=2)}

Research Pools:
{json.dumps(pool_summaries, indent=2)}

Provide:
1. Overall health assessment
2. Progress summary
3. Any concerns or bottlenecks
4. Recommended actions"""

        return await self.respond(prompt)

    async def _recommend_allocation(self, context: ResearchContext) -> str:
        """Recommend resource allocation strategy"""
        prompt = f"""As Chief Architect, recommend resource allocation for the equity research system.

Current Research Portfolio:
- Active pools: {len([p for p in self.research_pools.values() if p['status'] == 'active'])}
- Quality thresholds: {json.dumps(self.quality_thresholds, indent=2)}
- Concurrent limit: {self.quality_thresholds['concurrent_limit']}

Context ticker (if relevant): {context.ticker if context else 'N/A'}

Consider:
1. How to distribute research across concurrent workers
2. AI provider allocation (diversify perspectives)
3. Priority handling
4. Quality vs. speed tradeoffs

Provide specific allocation recommendations."""

        return await self.respond(prompt)

    async def _recommend_priorities(self, context: ResearchContext) -> str:
        """Recommend research priorities"""
        # Gather pool states
        pools_info = []
        for name, pool in self.research_pools.items():
            pending = len(pool['tickers']) - len(pool.get('completed', [])) - len(pool.get('failed', []))
            pools_info.append({
                'pool': name,
                'priority': pool['priority'],
                'pending': pending,
                'completed': len(pool.get('completed', []))
            })

        prompt = f"""As Chief Architect, recommend research priorities.

Current Pools:
{json.dumps(pools_info, indent=2)}

Recommend:
1. Which pools should be prioritized
2. Specific tickers that need urgent attention
3. Any rebalancing needed
4. Factors driving your recommendations"""

        return await self.respond(prompt)

    async def _evaluate_research_quality(self, context: ResearchContext) -> str:
        """Evaluate quality of completed research"""
        if not context:
            return "No research context provided for evaluation."

        prompt = f"""Evaluate the quality of this equity research:

Ticker: {context.ticker}
Company: {context.company_name}

Industry Analysis Length: {len(context.industry_analysis)} chars
Company Analysis Length: {len(context.company_analysis)} chars
Debate Rounds: {len(context.debate_log)}
DCF Assumptions: {bool(context.dcf_assumptions)}
Scenario Analysis: {bool(context.scenario_analysis)}

Quality Thresholds:
{json.dumps(self.quality_thresholds, indent=2)}

Evaluate:
1. Does it meet minimum quality standards?
2. Strengths of the analysis
3. Weaknesses or gaps
4. Recommended improvements
5. Overall score (0-100)"""

        return await self.respond(prompt)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Initialize on activation"""
        self.set_task("Coordinating research system")

    async def _graceful_shutdown(self):
        """Gracefully close all pools before terminating"""
        for pool_name in list(self.research_pools.keys()):
            await self.close_research_pool(pool_name, graceful=True)
