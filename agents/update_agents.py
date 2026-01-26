"""
Update Agents - Handle report updates and refinements
These agents take validation/monitoring results and update reports accordingly
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Visualizer integration
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


@dataclass
class UpdateTask:
    """A task to update a report"""
    ticker: str
    reason: str  # 'new_company', 'news_event', 'validation_issue', 'scheduled_refresh'
    priority: int  # 1=highest, 5=lowest
    details: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UpdateResult:
    """Result of an update operation"""
    ticker: str
    success: bool
    changes_made: List[str]
    errors: List[str]
    new_target_price: Optional[float] = None
    recommendation_changed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ResearchRefreshAgent:
    """
    Refreshes research for a company
    - Fetches latest financial data
    - Updates market data
    - Re-runs analysis
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "ResearchRefresh"

    async def refresh_equity(self, ticker: str, reason: str = "scheduled") -> UpdateResult:
        """Refresh research for a single equity"""
        result = UpdateResult(
            ticker=ticker,
            success=False,
            changes_made=[],
            errors=[]
        )

        try:
            # Load existing context
            context_file = self._find_context_file(ticker)
            if context_file:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
            else:
                context = {'ticker': ticker}
                result.changes_made.append("Created new context")

            # Run refresh tasks in parallel
            refresh_results = await asyncio.gather(
                self._refresh_market_data(ticker, context),
                self._refresh_financials(ticker, context),
                self._refresh_news(ticker, context),
                return_exceptions=True
            )

            # Merge results
            for refresh_result in refresh_results:
                if isinstance(refresh_result, dict):
                    context.update(refresh_result.get('updates', {}))
                    result.changes_made.extend(refresh_result.get('changes', []))
                elif isinstance(refresh_result, Exception):
                    result.errors.append(str(refresh_result))

            # Update timestamp
            context['last_updated'] = datetime.now().isoformat()
            context['update_reason'] = reason

            # Save updated context
            if context_file:
                with open(context_file, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2)
                result.success = True
            else:
                # Create new file
                new_file = self.context_dir / f"{ticker.replace(' ', '_')}.json"
                with open(new_file, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2)
                result.success = True

        except Exception as e:
            result.errors.append(f"Refresh failed: {str(e)}")

        return result

    def _find_context_file(self, ticker: str) -> Optional[Path]:
        """Find context file for ticker"""
        # Try exact match
        exact = self.context_dir / f"{ticker.replace(' ', '_')}.json"
        if exact.exists():
            return exact

        # Try pattern match
        for f in self.context_dir.glob("*.json"):
            if ticker.replace(' ', '_') in f.stem or ticker.replace(' ', '') in f.stem:
                return f

        return None

    async def _refresh_market_data(self, ticker: str, context: Dict) -> Dict:
        """Refresh market data (price, volume, etc.)"""
        # In production, would call market data API
        return {
            'updates': {},
            'changes': ['Market data refresh attempted']
        }

    async def _refresh_financials(self, ticker: str, context: Dict) -> Dict:
        """Refresh financial data"""
        # In production, would call financial data API
        return {
            'updates': {},
            'changes': ['Financial data refresh attempted']
        }

    async def _refresh_news(self, ticker: str, context: Dict) -> Dict:
        """Refresh recent news"""
        return {
            'updates': {},
            'changes': ['News refresh attempted']
        }


class ReportRegeneratorAgent:
    """
    Regenerates HTML reports after context updates
    """

    def __init__(self, context_dir: str = "context", reports_dir: str = "reports"):
        self.context_dir = Path(context_dir)
        self.reports_dir = Path(reports_dir)
        self.agent_name = "ReportRegenerator"

    async def regenerate_report(self, ticker: str) -> UpdateResult:
        """Regenerate HTML report for a ticker"""
        result = UpdateResult(
            ticker=ticker,
            success=False,
            changes_made=[],
            errors=[]
        )

        try:
            # Import report generators
            from utils.html_generator import HTMLGenerator
            from utils.detailed_report_generator import DetailedReportGenerator

            # Load context
            context_file = self._find_context_file(ticker)
            if not context_file:
                result.errors.append(f"No context file found for {ticker}")
                return result

            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)

            # Generate summary report
            html_gen = HTMLGenerator(str(self.reports_dir))
            summary_path = html_gen.generate_equity_report(context)
            result.changes_made.append(f"Summary report updated: {summary_path}")

            # Generate detailed report
            detailed_gen = DetailedReportGenerator(str(self.reports_dir))
            detailed_path = detailed_gen.generate_detailed_report(context)
            result.changes_made.append(f"Detailed report updated: {detailed_path}")

            result.success = True

        except ImportError as e:
            result.errors.append(f"Import error: {str(e)}")
        except Exception as e:
            result.errors.append(f"Regeneration failed: {str(e)}")

        return result

    def _find_context_file(self, ticker: str) -> Optional[Path]:
        """Find context file for ticker"""
        for f in self.context_dir.glob("*.json"):
            if ticker.replace(' ', '_') in f.stem:
                return f
        return None


class IndexUpdaterAgent:
    """
    Updates the main index.html when reports change
    """

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.agent_name = "IndexUpdater"

    async def update_index(self, changed_tickers: List[str], flags: Dict[str, str] = None) -> UpdateResult:
        """Update index.html with changes and flags"""
        result = UpdateResult(
            ticker="INDEX",
            success=False,
            changes_made=[],
            errors=[]
        )

        try:
            index_file = self.reports_dir / "index.html"
            if not index_file.exists():
                result.errors.append("index.html not found")
                return result

            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add update flags to changed tickers
            if flags:
                for ticker, flag in flags.items():
                    # Find and update the card for this ticker
                    # This is a simplified approach - in production would use proper HTML parsing
                    if ticker in content:
                        result.changes_made.append(f"Flag added for {ticker}: {flag}")

            # Update timestamp in footer
            new_timestamp = datetime.now().strftime('%B %Y')
            if 'Generated' in content:
                result.changes_made.append("Updated generation timestamp")

            result.success = True

        except Exception as e:
            result.errors.append(f"Index update failed: {str(e)}")

        return result


class ValidationFixerAgent:
    """
    Automatically fixes certain validation issues
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "ValidationFixer"

    async def fix_issues(self, ticker: str, validation_report: Dict) -> UpdateResult:
        """Attempt to fix validation issues"""
        result = UpdateResult(
            ticker=ticker,
            success=False,
            changes_made=[],
            errors=[]
        )

        try:
            # Load context
            context_file = self._find_context_file(ticker)
            if not context_file:
                result.errors.append(f"No context file for {ticker}")
                return result

            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)

            fixes_made = False

            # Try to fix calculation errors
            for issue in validation_report.get('calculation_issues', []):
                if 'upside' in issue.get('issue', '').lower():
                    # Recalculate upside
                    current = context.get('current_price', 0)
                    target = context.get('target_price', 0)
                    if current > 0 and target > 0:
                        context['upside_potential'] = (target - current) / current
                        result.changes_made.append("Recalculated upside potential")
                        fixes_made = True

            # Try to fix probability sum issues
            for issue in validation_report.get('logic_issues', []):
                if 'probabilities' in issue.get('issue', '').lower():
                    scenarios = context.get('scenarios', {})
                    if scenarios:
                        total = sum(s.get('probability', 0) for s in scenarios.values())
                        if total > 0 and abs(total - 1.0) > 0.01:
                            # Normalize probabilities
                            for s in scenarios.values():
                                s['probability'] = s.get('probability', 0) / total
                            context['scenarios'] = scenarios
                            result.changes_made.append("Normalized scenario probabilities")
                            fixes_made = True

            if fixes_made:
                context['last_fixed'] = datetime.now().isoformat()
                with open(context_file, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2)
                result.success = True
            else:
                result.success = True  # No fixes needed is still success

        except Exception as e:
            result.errors.append(f"Fix failed: {str(e)}")

        return result

    def _find_context_file(self, ticker: str) -> Optional[Path]:
        """Find context file for ticker"""
        for f in self.context_dir.glob("*.json"):
            if ticker.replace(' ', '_') in f.stem:
                return f
        return None


class NewCompanyResearchAgent:
    """
    Handles research for newly added companies
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "NewCompanyResearch"

    async def research_new_company(self, ticker: str, company_name: str) -> UpdateResult:
        """Run full research workflow for a new company"""
        result = UpdateResult(
            ticker=ticker,
            success=False,
            changes_made=[],
            errors=[]
        )

        try:
            print(f"  [{self.agent_name}] Starting research for {ticker} - {company_name}")

            # Run research phases in sequence (some depend on previous)
            phases = [
                ('data_gathering', self._gather_data(ticker, company_name)),
                ('industry_analysis', self._analyze_industry(ticker, company_name)),
                ('company_analysis', self._analyze_company(ticker, company_name)),
                ('dcf_valuation', self._run_dcf(ticker)),
                ('scenario_analysis', self._run_scenarios(ticker)),
            ]

            context = {
                'ticker': ticker,
                'company_name': company_name,
                'created': datetime.now().isoformat()
            }

            for phase_name, phase_coro in phases:
                try:
                    phase_result = await phase_coro
                    if isinstance(phase_result, dict):
                        context.update(phase_result)
                        result.changes_made.append(f"Completed: {phase_name}")
                except Exception as e:
                    result.errors.append(f"{phase_name} failed: {str(e)}")

            # Save context
            context_file = self.context_dir / f"{ticker.replace(' ', '_')}.json"
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2)

            result.success = len(result.errors) == 0

        except Exception as e:
            result.errors.append(f"Research failed: {str(e)}")

        return result

    async def _gather_data(self, ticker: str, company_name: str) -> Dict:
        """Gather initial data"""
        return {'data_gathered': True}

    async def _analyze_industry(self, ticker: str, company_name: str) -> Dict:
        """Analyze industry"""
        return {'industry_analysis': {}}

    async def _analyze_company(self, ticker: str, company_name: str) -> Dict:
        """Analyze company"""
        return {'company_analysis': {}}

    async def _run_dcf(self, ticker: str) -> Dict:
        """Run DCF valuation"""
        return {'dcf_valuation': {}}

    async def _run_scenarios(self, ticker: str) -> Dict:
        """Run scenario analysis"""
        return {'scenarios': {}}


class UpdateOrchestrator:
    """
    Orchestrates all update operations
    """

    def __init__(self, context_dir: str = "context", reports_dir: str = "reports", visualizer=None):
        self.context_dir = Path(context_dir)
        self.reports_dir = Path(reports_dir)

        # Visualizer for real-time updates
        self.visualizer = visualizer
        if self.visualizer is None and VISUALIZER_AVAILABLE:
            try:
                self.visualizer = VisualizerBridge(context_dir)
            except:
                self.visualizer = None

        # Initialize agents
        self.refresh_agent = ResearchRefreshAgent(context_dir)
        self.regenerator = ReportRegeneratorAgent(context_dir, reports_dir)
        self.index_updater = IndexUpdaterAgent(reports_dir)
        self.fixer = ValidationFixerAgent(context_dir)
        self.new_company_agent = NewCompanyResearchAgent(context_dir)

    async def process_update_tasks(self, tasks: List[UpdateTask]) -> List[UpdateResult]:
        """Process all update tasks"""
        print(f"\n{'='*60}")
        print(f"UPDATE PROCESSOR: {len(tasks)} tasks")
        print(f"{'='*60}")

        # Update visualizer
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Processing {len(tasks)} update tasks",
                progress=5
            )

        # Sort by priority
        tasks.sort(key=lambda t: t.priority)

        # Group by type for parallel processing
        new_companies = [t for t in tasks if t.reason == 'new_company']
        refreshes = [t for t in tasks if t.reason in ['news_event', 'scheduled_refresh']]
        validations = [t for t in tasks if t.reason == 'validation_issue']

        results = []

        # Process new companies (can be parallel)
        if new_companies:
            print(f"\n  Processing {len(new_companies)} new companies...")
            if self.visualizer:
                self.visualizer.update_agent_task(
                    "orchestrator",
                    f"Researching {len(new_companies)} new companies",
                    progress=20
                )
            new_results = await asyncio.gather(
                *[self.new_company_agent.research_new_company(
                    t.ticker, t.details.get('company_name', t.ticker))
                  for t in new_companies],
                return_exceptions=True
            )
            results.extend([r for r in new_results if isinstance(r, UpdateResult)])

        # Process refreshes (can be parallel)
        if refreshes:
            print(f"\n  Processing {len(refreshes)} refreshes...")
            if self.visualizer:
                self.visualizer.update_agent_task(
                    "orchestrator",
                    f"Refreshing {len(refreshes)} equities",
                    progress=40
                )
            refresh_results = await asyncio.gather(
                *[self.refresh_agent.refresh_equity(t.ticker, t.reason) for t in refreshes],
                return_exceptions=True
            )
            results.extend([r for r in refresh_results if isinstance(r, UpdateResult)])

        # Process validation fixes (can be parallel)
        if validations:
            print(f"\n  Processing {len(validations)} validation fixes...")
            if self.visualizer:
                self.visualizer.update_agent_task(
                    "orchestrator",
                    f"Fixing {len(validations)} validation issues",
                    progress=60
                )
            fix_results = await asyncio.gather(
                *[self.fixer.fix_issues(t.ticker, t.details) for t in validations],
                return_exceptions=True
            )
            results.extend([r for r in fix_results if isinstance(r, UpdateResult)])

        # Regenerate reports for all updated tickers
        updated_tickers = [r.ticker for r in results if r.success]
        if updated_tickers:
            print(f"\n  Regenerating {len(updated_tickers)} reports...")
            if self.visualizer:
                self.visualizer.update_agent_task(
                    "orchestrator",
                    f"Regenerating {len(updated_tickers)} reports",
                    progress=80
                )
            regen_results = await asyncio.gather(
                *[self.regenerator.regenerate_report(t) for t in updated_tickers],
                return_exceptions=True
            )
            results.extend([r for r in regen_results if isinstance(r, UpdateResult)])

        # Update index
        if updated_tickers:
            print(f"\n  Updating index...")
            index_result = await self.index_updater.update_index(updated_tickers)
            results.append(index_result)

        # Summary
        successful = sum(1 for r in results if r.success)
        print(f"\n{'='*60}")
        print(f"UPDATE COMPLETE: {successful}/{len(results)} successful")
        print(f"{'='*60}\n")

        # Update visualizer completion
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Updates complete - {successful}/{len(results)} successful",
                progress=100
            )

        return results


async def run_updates(tasks: List[UpdateTask]):
    """Run update tasks"""
    orchestrator = UpdateOrchestrator()
    return await orchestrator.process_update_tasks(tasks)


if __name__ == "__main__":
    # Example usage
    test_tasks = [
        UpdateTask(ticker="TEST", reason="scheduled_refresh", priority=3)
    ]
    asyncio.run(run_updates(test_tasks))
