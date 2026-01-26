"""
Research Supervisor Agent - Owns the full research cycle for assigned equities

Responsibilities:
- Own research lifecycle for assigned tickers
- Spawn and manage worker agents
- Monitor worker health and handle failures
- Coordinate with goalkeepers for publishing
- Implement retry logic with backoff
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext, AgentMessage


class ResearchSupervisor(SpawnableAgent):
    """
    Supervises the full research cycle for assigned equities (Tier 1).

    The ResearchSupervisor owns the complete research process for its
    assigned tickers, spawning workers as needed and ensuring quality.

    Usage:
        supervisor = await architect.spawn_child(
            ResearchSupervisor, "supervisor_tech",
            config={
                'tickers': ['9660 HK', 'LEGN US'],
                'concurrent_limit': 2
            }
        )
        await supervisor.start_all_research()
    """

    def __init__(
        self,
        ai_provider,
        role: str = "research_supervisor",
        parent_id: str = None,
        tier: int = 1,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role=role,
            parent_id=parent_id,
            tier=tier,
            config=config
        )

        # Configuration
        self.pool_name = config.get('pool_name', 'default') if config else 'default'
        self.assigned_tickers = config.get('tickers', []) if config else []
        self.quality_thresholds = config.get('quality_thresholds', {}) if config else {}
        self.concurrent_limit = config.get('concurrent_limit', 3) if config else 3

        # Worker tracking: ticker -> worker_id
        self.worker_assignments: Dict[str, str] = {}

        # Research state: ticker -> status
        self.research_status: Dict[str, Dict] = {}

        # Results: ticker -> ResearchContext
        self.research_results: Dict[str, ResearchContext] = {}

        # Retry tracking: ticker -> retry_count
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = config.get('max_retries', 3) if config else 3

        # Ticker info storage for assign_ticker
        self.ticker_info: Dict[str, Dict] = {}

    async def assign_ticker(self, ticker: str, context: ResearchContext):
        """
        Assign a ticker with its context info to this supervisor.

        Args:
            ticker: Stock ticker symbol
            context: ResearchContext with company info
        """
        if ticker not in self.assigned_tickers:
            self.assigned_tickers.append(ticker)

        self.ticker_info[ticker] = {
            'company': context.company_name,
            'sector': context.sector,
            'industry': context.industry
        }

    def _get_system_prompt(self) -> str:
        return """You are a Research Supervisor managing equity research tasks.

Your responsibilities:
1. Assign work to analyst and debate agents
2. Monitor progress and health of workers
3. Handle failures and reassign work when needed
4. Ensure quality standards before passing to goalkeepers
5. Report progress to the Chief Architect

Maintain awareness of all assigned tickers and their status.
Make decisions about retries, escalation, and resource allocation."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Main analysis dispatch"""
        action = kwargs.get('action', 'status')

        if action == 'start':
            ticker = kwargs.get('ticker')
            return await self._start_single_research(ticker, context)
        elif action == 'check_health':
            return await self._get_health_report()
        elif action == 'evaluate':
            return await self._evaluate_research(context)
        else:
            return await self._get_status_report()

    # ==========================================
    # Research Lifecycle
    # ==========================================

    async def start_all_research(self) -> Dict[str, ResearchContext]:
        """
        Start research for all assigned tickers with concurrency control.

        Returns:
            Dict mapping tickers to their completed ResearchContext
        """
        self.set_task(f"Starting research for {len(self.assigned_tickers)} tickers")

        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def research_with_semaphore(ticker: str):
            async with semaphore:
                return await self._research_ticker(ticker)

        # Create tasks for all tickers
        tasks = [research_with_semaphore(ticker) for ticker in self.assigned_tickers]

        # Run all with gather
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results
        for ticker, result in zip(self.assigned_tickers, results):
            if isinstance(result, Exception):
                self.research_status[ticker] = {
                    'status': 'error',
                    'error': str(result)
                }
            elif isinstance(result, ResearchContext):
                self.research_results[ticker] = result
                self.research_status[ticker] = {'status': 'completed'}

        self.set_task(f"Completed research for pool: {self.pool_name}")
        return self.research_results

    async def _research_ticker(self, ticker: str) -> ResearchContext:
        """
        Run full research cycle for a single ticker.

        Includes:
        1. Create research context
        2. Spawn analyst for initial research
        3. Spawn debate moderator for debate
        4. Run quality gates
        5. Handle retries on failure
        """
        self.research_status[ticker] = {'status': 'starting', 'started_at': datetime.now().isoformat()}
        self.retry_counts[ticker] = 0

        # Get ticker info (would come from config or lookup)
        ticker_info = self._get_ticker_info(ticker)

        # Create research context
        context = ResearchContext(
            ticker=ticker,
            company_name=ticker_info.get('company', ticker),
            sector=ticker_info.get('sector', 'Unknown'),
            industry=ticker_info.get('industry', 'Unknown')
        )

        try:
            # Phase 1: Initial Research
            self.research_status[ticker]['status'] = 'initial_research'
            await self._run_initial_research(ticker, context)

            # Phase 2: Debate
            self.research_status[ticker]['status'] = 'debate'
            await self._run_debate(ticker, context)

            # Phase 3: Quality Gates
            self.research_status[ticker]['status'] = 'quality_check'
            passed = await self._run_quality_gates(ticker, context)

            if not passed:
                raise Exception("Failed quality gates")

            # Success
            self.research_status[ticker] = {
                'status': 'completed',
                'completed_at': datetime.now().isoformat()
            }

            # Report to parent
            if self._registry:
                parent = self._registry.get_parent(self.agent_id)
                if parent and hasattr(parent, 'report_completion'):
                    parent.report_completion(self.pool_name, ticker, True)

            return context

        except Exception as e:
            return await self._handle_research_failure(ticker, context, str(e))

    async def _run_initial_research(self, ticker: str, context: ResearchContext):
        """Run initial research phase with spawned analyst"""
        from agents.workers import EnhancedAnalystAgent

        # Spawn analyst
        analyst = await self.spawn_child(
            EnhancedAnalystAgent,
            f"analyst_{ticker.replace(' ', '_').replace('.', '_')}",
            config={'ticker': ticker}
        )

        self.worker_assignments[ticker] = analyst.agent_id

        try:
            # Run analyses in parallel where possible
            # Industry and governance can run in parallel
            industry_task = analyst.analyze(context, analysis_type="industry")
            governance_task = analyst.analyze(context, analysis_type="governance")

            context.industry_analysis, context.governance_analysis = await asyncio.gather(
                industry_task, governance_task
            )

            # Company analysis depends on industry
            context.company_analysis = await analyst.analyze(context, analysis_type="company")

            # DCF depends on company
            dcf_result = await analyst.analyze(context, analysis_type="dcf")
            # Parse DCF result into assumptions/values
            self._parse_dcf_result(context, dcf_result)

        finally:
            # Terminate analyst
            await self.terminate_child(analyst.agent_id)
            del self.worker_assignments[ticker]

    async def _run_debate(self, ticker: str, context: ResearchContext):
        """Run debate phase with debate moderator"""
        from agents.supervisors.debate_moderator import DebateModerator

        # Get debate rounds from config
        debate_rounds = self.quality_thresholds.get('debate_rounds_min', 10)

        # Spawn debate moderator
        moderator = await self.spawn_child(
            DebateModerator,
            f"moderator_{ticker.replace(' ', '_').replace('.', '_')}",
            config={
                'ticker': ticker,
                'rounds': debate_rounds
            }
        )

        try:
            # Run full debate
            synthesis = await moderator.run_full_debate(context)

            # Add final synthesis to debate log
            context.debate_log.append(AgentMessage(
                role="synthesizer",
                content=synthesis,
                metadata={"phase": "final_synthesis"}
            ))

        finally:
            # Moderator terminates its own children, then we terminate it
            await self.terminate_child(moderator.agent_id)

    async def _run_quality_gates(self, ticker: str, context: ResearchContext) -> bool:
        """Run quality gates and return pass/fail"""
        from agents.goalkeepers import PublishGatekeeperAgent

        # Spawn gatekeeper
        gatekeeper = await self.spawn_child(
            PublishGatekeeperAgent,
            f"gatekeeper_{ticker.replace(' ', '_').replace('.', '_')}",
            config={'ticker': ticker}
        )

        try:
            # Run all gates
            result = await gatekeeper.run_all_gates(context)

            # Store gate results in research status
            self.research_status[ticker]['gate_results'] = result

            return result.get('approved', False)

        finally:
            await self.terminate_child(gatekeeper.agent_id)

    # ==========================================
    # Error Handling
    # ==========================================

    async def _handle_research_failure(
        self,
        ticker: str,
        context: ResearchContext,
        error: str
    ) -> ResearchContext:
        """Handle research failure with retry logic"""
        self.retry_counts[ticker] = self.retry_counts.get(ticker, 0) + 1

        if self.retry_counts[ticker] <= self.max_retries:
            # Retry
            self.research_status[ticker] = {
                'status': 'retrying',
                'retry_count': self.retry_counts[ticker],
                'last_error': error
            }

            # Wait before retry (exponential backoff)
            await asyncio.sleep(5 * self.retry_counts[ticker])

            return await self._research_ticker(ticker)
        else:
            # Max retries exceeded
            self.research_status[ticker] = {
                'status': 'failed',
                'error': error,
                'retry_count': self.retry_counts[ticker]
            }

            # Report failure to parent
            if self._registry:
                parent = self._registry.get_parent(self.agent_id)
                if parent and hasattr(parent, 'report_completion'):
                    parent.report_completion(self.pool_name, ticker, False)

            return context

    async def check_worker_health(self) -> Dict[str, bool]:
        """Check health of all active workers"""
        health_report = {}

        for ticker, worker_id in self.worker_assignments.items():
            worker = self.get_child(worker_id)
            if worker:
                health_report[ticker] = worker.is_healthy()
                if not health_report[ticker]:
                    await self._handle_unhealthy_worker(ticker, worker_id)
            else:
                health_report[ticker] = False

        return health_report

    async def _handle_unhealthy_worker(self, ticker: str, worker_id: str):
        """Handle an unhealthy worker"""
        worker = self.get_child(worker_id)

        if worker and worker.error_count >= worker.max_errors:
            # Worker has too many errors, terminate and mark for retry
            await self.terminate_child(worker_id)
            del self.worker_assignments[ticker]
            self.research_status[ticker] = {
                'status': 'needs_restart',
                'reason': 'worker_unhealthy'
            }

    # ==========================================
    # Helper Methods
    # ==========================================

    def _get_ticker_info(self, ticker: str) -> Dict:
        """Get ticker info from assigned info or defaults"""
        if ticker in self.ticker_info:
            return self.ticker_info[ticker]
        return {
            'company': ticker,
            'sector': 'Unknown',
            'industry': 'Unknown'
        }

    def _parse_dcf_result(self, context: ResearchContext, dcf_result: str):
        """Parse DCF analysis result into context"""
        # Simple parsing - in reality would be more sophisticated
        context.dcf_assumptions = {
            'raw_analysis': dcf_result[:2000],
            'parsed': False
        }

    # ==========================================
    # Status and Reporting
    # ==========================================

    async def _get_status_report(self) -> str:
        """Generate status report"""
        stats = {
            'pool': self.pool_name,
            'total_tickers': len(self.assigned_tickers),
            'completed': len([s for s in self.research_status.values() if s.get('status') == 'completed']),
            'in_progress': len([s for s in self.research_status.values() if s.get('status') in ('starting', 'initial_research', 'debate', 'quality_check')]),
            'failed': len([s for s in self.research_status.values() if s.get('status') == 'failed']),
            'active_workers': len(self.worker_assignments)
        }

        prompt = f"""Generate a research supervisor status report.

Statistics:
{json.dumps(stats, indent=2)}

Detailed Status:
{json.dumps(self.research_status, indent=2)}

Provide:
1. Progress summary
2. Current bottlenecks
3. Recommendations"""

        return await self.respond(prompt)

    async def _get_health_report(self) -> str:
        """Generate worker health report"""
        health = await self.check_worker_health()

        prompt = f"""Generate a worker health report.

Worker Health:
{json.dumps(health, indent=2)}

Research Status:
{json.dumps(self.research_status, indent=2)}

Assess:
1. Overall health of workers
2. Any concerning patterns
3. Recommended actions"""

        return await self.respond(prompt)

    async def _evaluate_research(self, context: ResearchContext) -> str:
        """Evaluate completed research quality"""
        prompt = f"""Evaluate the research quality for {context.ticker}.

Analysis Lengths:
- Industry: {len(context.industry_analysis)} chars
- Company: {len(context.company_analysis)} chars
- Governance: {len(context.governance_analysis)} chars

Debate Log: {len(context.debate_log)} entries

Quality Thresholds:
{json.dumps(self.quality_thresholds, indent=2)}

Evaluate:
1. Completeness
2. Quality vs. thresholds
3. Areas needing improvement"""

        return await self.respond(prompt)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Initialize on activation"""
        self.set_task(f"Supervising pool: {self.pool_name}")

    async def _graceful_shutdown(self):
        """Graceful shutdown - terminate all workers"""
        for worker_id in list(self.worker_assignments.values()):
            await self.terminate_child(worker_id, graceful=True)
